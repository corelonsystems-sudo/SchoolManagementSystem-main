from django.db import models
from academics.models import Student, Enrollment
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.db.models import Max
from decimal import Decimal


class PaymentType(models.Model):
    FREQUENCY_CHOICES = [
        ('ONCE', 'Once'),
        ('YEARLY', 'Per Year'),
        ('SEMESTERLY', 'Per Semester'),
    ]

    name = models.CharField(max_length=100, unique=True)  # Name of the payment type, e.g., "School Fees"
    frequency = models.CharField(
        max_length=15,
        choices=FREQUENCY_CHOICES,
        default='SEMESTERLY',
        help_text="How often this fee is charged: once, every academic year, or every semester."
    )
    default_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Standard fee amount charged for this payment type. Used to auto-generate ledgers on enrollment. Ignored if 'Is tuition' is checked (tuition uses CourseFee instead)."
    )
    is_tuition = models.BooleanField(
        default=False,
        help_text="Mark this payment type as the one representing course tuition fees. Its amount will be pulled from CourseFee (matched by student's course, academic year and semester) instead of default_amount."
    )
    courses = models.ManyToManyField(
        'academics.Course',
        blank=True,
        related_name='payment_types',
        help_text="Courses this payment type applies to. Leave empty to apply to all courses."
    )

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class PaymentTypeBreakdown(models.Model):
    ledger = models.ForeignKey('Ledger', on_delete=models.CASCADE, related_name='payment_type_breakdowns')  # Link to the specific Ledger
    payment_type = models.ForeignKey(PaymentType, on_delete=models.CASCADE)  # Payment type for this breakdown
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0,
        help_text="Amount charged to this student for this fee. Edit to grant a discount or waiver."
    )
    standard_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, editable=False,
        help_text="The amount originally generated on enrollment, kept so discounts can be reported."
    )
    note = models.CharField(
        max_length=255, blank=True,
        help_text="Reason for adjusting this amount, e.g. 'Bursary award' or 'Staff child discount'."
    )

    @property
    def is_adjusted(self):
        """True when the charged amount differs from what was generated on enrollment."""
        return (
            self.standard_amount is not None
            and self.amount != self.standard_amount
        )

    @property
    def adjustment(self):
        """Negative for a discount, positive for a surcharge, None if never adjusted."""
        if self.standard_amount is None:
            return None
        return self.amount - self.standard_amount

    def save(self, *args, **kwargs):
        # Capture the generated amount the first time the row is created so any
        # later edit can be reported as a discount or surcharge against it.
        if self.standard_amount is None:
            self.standard_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payment_type.name} - {self.amount}"


from decimal import Decimal

class Ledger(models.Model):
    def generate_ledger_number(self):
        last_ledger = Ledger.objects.aggregate(Max('id'))  # Get the last ledger ID
        next_ledger_id = last_ledger['id__max'] + 1 if last_ledger['id__max'] else 1
        ledger_number = f"LEDG-{next_ledger_id:04d}"  # Format as 'LEDG-0001', 'LEDG-0002', etc.
        return ledger_number

    ledger_number = models.CharField(max_length=10, unique=True, editable=False)  # Removed default

    student = models.ForeignKey('academics.Student', on_delete=models.CASCADE, related_name="ledgers")
    study_year = models.ForeignKey('academics.StudyYear', on_delete=models.CASCADE, null=True, blank=True)
    semester = models.ForeignKey('academics.semester', on_delete=models.CASCADE)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    required_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    generated_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        year = self.study_year.year if self.study_year else "No Year"
        return f"{self.student.first_name} {self.student.last_name} - {year} - {self.semester.semester} - Ledger No: {self.ledger_number}"

    def update_required_amount(self):
        total_breakdown = self.payment_type_breakdowns.aggregate(total=Sum('amount'))['total']
        self.required_amount = total_breakdown or Decimal('0.00')  # Ensure this is a Decimal value

    def save(self, *args, **kwargs):
        if not self.pk:
            # First insert to get the primary key. ledger_number is generated
            # afterwards so we can use the assigned id.
            super().save(*args, **kwargs)
            if not self.ledger_number:
                self.ledger_number = self.generate_ledger_number()
            self.update_required_amount()
            self.balance = self.required_amount - Decimal(self.total_paid)
            # get_or_create passes force_insert; the second save must be an
            # update, so drop force_insert.
            kwargs.pop('force_insert', None)
            super().save(*args, **kwargs)
        else:
            if not self.ledger_number:
                self.ledger_number = self.generate_ledger_number()
            self.update_required_amount()
            self.balance = self.required_amount - Decimal(self.total_paid)
            # get_or_create passes force_insert; if the pk already exists that
            # would cause an attempted duplicate insert, so drop it.
            kwargs.pop('force_insert', None)
            super().save(*args, **kwargs)
            


class Payment(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    payment_type = models.ForeignKey(PaymentType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    ledger = models.ForeignKey(Ledger, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)

    def __str__(self):
        return f"{self.payment_type.name} - {self.amount} - {self.date.strftime('%Y-%m-%d')}"


class CourseFee(models.Model):
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE, related_name='fees')
    study_year = models.ForeignKey('academics.StudyYear', on_delete=models.CASCADE, null=True, blank=True)
    semester = models.ForeignKey('academics.semester', on_delete=models.CASCADE)
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('course', 'study_year', 'semester')

    def __str__(self):
        year = self.study_year.year if self.study_year else "No Year"
        return f"{self.course.name} - {year} - {self.semester.semester}: {self.tuition_fee}"


class AdmissionFee(models.Model):
    admission = models.ForeignKey('admissions.Student', on_delete=models.CASCADE, related_name='selected_fees')
    payment_type = models.ForeignKey(PaymentType, on_delete=models.CASCADE)
    custom_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional override for the student's fee amount. Leave blank to use the payment type's default or course fee."
    )
    is_active = models.BooleanField(default=True, help_text="Uncheck to skip this fee during enrollment.")

    class Meta:
        unique_together = ('admission', 'payment_type')

    def __str__(self):
        amount = self.custom_amount if self.custom_amount is not None else self.payment_type.default_amount
        return f"{self.admission} - {self.payment_type.name}: {amount}"
