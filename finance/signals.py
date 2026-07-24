from decimal import Decimal

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from academics.models import Enrollment, StudyYear, semester
from admissions.models import Student as AdmissionStudent
from .models import Ledger, PaymentType, PaymentTypeBreakdown, CourseFee, AdmissionFee


@receiver(post_save, sender=AdmissionStudent)
def create_admission_fee_records(sender, instance, created, **kwargs):
    """
    Ensure every payment type is represented as an AdmissionFee row for a new
    admission. This lets the admission form show all payment types and staff
    simply tick the ones the student should pay.
    """
    if not created:
        return
    for payment_type in PaymentType.objects.all():
        AdmissionFee.objects.get_or_create(
            admission=instance,
            payment_type=payment_type,
            defaults={'is_active': False, 'custom_amount': None},
        )


@receiver(post_save, sender=Enrollment)
def create_ledger_for_enrollment(sender, instance, created, **kwargs):
    """
    When a student is enrolled for an academic year & semester, automatically
    create their fee Ledger with a PaymentTypeBreakdown line for every fee
    selected on the student's admission. Tuition-flagged payment types pull
    their amount from CourseFee; all other payment types use their configured
    default_amount or the custom amount set on the admission fee.
    Frequency controls whether a fee is charged once, yearly, or every semester.
    
    Also includes payment types that are attached to the student's course.
    """
    if not created:
        return

    student = instance.student
    study_year = instance.study_year
    semester = instance.semester

    if not semester:
        return

    ledger, ledger_created = Ledger.objects.get_or_create(
        student=student,
        study_year=study_year,
        semester=semester,
    )

    if not ledger_created:
        return

    admission = student.admission
    
    # Get manually selected fees from admission
    selected_fees = AdmissionFee.objects.filter(
        admission=admission,
        is_active=True,
    ).select_related('payment_type')
    
    # Get payment types attached to the student's course
    course_payment_types = PaymentType.objects.filter(
        courses=admission.course
    )
    
    # Combine both sets of payment types, avoiding duplicates
    payment_types_to_include = set()
    
    # Add manually selected payment types
    for admission_fee in selected_fees:
        payment_types_to_include.add(admission_fee.payment_type)
    
    # Add course-attached payment types
    for payment_type in course_payment_types:
        payment_types_to_include.add(payment_type)

    for payment_type in payment_types_to_include:
        # Check if this payment type has a custom amount from admission fees
        admission_fee = selected_fees.filter(payment_type=payment_type).first()
        custom_amount = admission_fee.custom_amount if admission_fee else None

        # Frequency check
        if payment_type.frequency == 'ONCE':
            if Ledger.objects.filter(student=student).exclude(pk=ledger.pk).exists():
                continue
        elif payment_type.frequency == 'YEARLY':
            if Ledger.objects.filter(student=student, study_year=study_year).exclude(pk=ledger.pk).exists():
                continue
        # SEMESTERLY is always included

        amount = _get_fee_amount(
            payment_type, student, study_year, semester, custom_amount
        )
        if amount and amount > 0:
            PaymentTypeBreakdown.objects.create(
                ledger=ledger,
                payment_type=payment_type,
                amount=amount,
            )

    ledger.save()


def _get_fee_amount(payment_type, student, study_year, semester, custom_amount):
    if custom_amount is not None:
        return custom_amount
    if payment_type.is_tuition:
        course_fee = CourseFee.objects.filter(
            course=student.course,
            study_year=study_year,
            semester=semester,
        ).first()
        return course_fee.tuition_fee if course_fee else Decimal('0.00')
    return payment_type.default_amount


@receiver(m2m_changed, sender=PaymentType.courses.through)
def create_course_fees_for_payment_type(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    When a payment type is attached to courses, automatically create CourseFee records
    for each course-academic year-semester combination using the payment type's default amount.
    """
    if action != 'post_add':
        return
    
    if reverse:
        # Course is being added to payment types (not the typical use case)
        return
    
    # Get the courses that were added
    courses = model.objects.filter(pk__in=pk_set)
    
    # Get all study years and semesters
    study_years = StudyYear.objects.all()
    semesters = semester.objects.all()
    
    # Create CourseFee records for each combination
    for course in courses:
        for study_year in study_years:
            for sem in semesters:
                CourseFee.objects.get_or_create(
                    course=course,
                    study_year=study_year,
                    semester=sem,
                    defaults={'tuition_fee': instance.default_amount}
                )
