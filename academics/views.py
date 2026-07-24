from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from .models import Enrollment, CourseUnit, Student, StudyYear, semester, Marks, Intake, Course
from admissions.models import Student as AdmissionStudent
from finance.models import Ledger, Payment

def course_list(request):
    courses = CourseUnit.objects.all()
    return render(request, 'academics/course_list.html', {'courses': courses})


def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    enrollments = Enrollment.objects.filter(student=student).select_related('study_year', 'semester').order_by('-created_at')
    enrollment_data = []
    for enrollment in enrollments:
        course_units = CourseUnit.objects.filter(
            courses=student.course,
            year=enrollment.study_year,
            semester=enrollment.semester,
        ).order_by('code')
        # Fetch marks for each course unit in this enrollment
        unit_marks = {}
        total_marks = 0
        marks_count = 0
        for cu in course_units:
            mark = Marks.objects.filter(enrollment=enrollment, course_unit=cu).first()
            if mark:
                unit_marks[cu.id] = {
                    'test_marks': mark.test_marks,
                    'final_marks': mark.final_marks,
                    'total_marks': mark.total_marks(),
                }
                total_marks += mark.total_marks()
                marks_count += 1
        # Calculate average
        average_score = round(total_marks / marks_count, 1) if marks_count > 0 else None
        enrollment_data.append({
            'enrollment': enrollment,
            'course_units': course_units,
            'course_unit_count': course_units.count(),
            'unit_marks': unit_marks,
            'average_score': average_score,
            'marks_count': marks_count,
        })
    
    # Fetch finance data
    ledgers = Ledger.objects.filter(student=student).select_related('study_year', 'semester').prefetch_related('payment_type_breakdowns__payment_type').order_by('-generated_on')
    ledger_data = []
    for ledger in ledgers:
        payments = Payment.objects.filter(enrollment__student=student, enrollment__study_year=ledger.study_year, enrollment__semester=ledger.semester)
        # Calculate paid amount per payment type
        payment_type_paid = {}
        for payment in payments:
            pt_id = payment.payment_type.id
            payment_type_paid[pt_id] = payment_type_paid.get(pt_id, 0) + payment.amount
        
        # Add paid amounts to breakdowns
        breakdowns_with_paid = []
        for breakdown in ledger.payment_type_breakdowns.all():
            paid_amount = payment_type_paid.get(breakdown.payment_type.id, 0)
            balance = breakdown.amount - paid_amount
            breakdowns_with_paid.append({
                'payment_type': breakdown.payment_type,
                'amount': breakdown.amount,
                'paid': paid_amount,
                'balance': balance,
            })
        
        ledger_data.append({
            'ledger': ledger,
            'payments': payments,
            'payment_count': payments.count(),
            'breakdowns': breakdowns_with_paid,
        })

    # Determine whether the student can be enrolled for a new academic year/semester.
    # Allowed if there is no enrollment yet, or the most recent enrollment has
    # course units and all of them have marks recorded.
    latest = enrollment_data[0] if enrollment_data else None
    if latest is None:
        can_enroll_next = True
    else:
        can_enroll_next = latest['course_unit_count'] > 0 and latest['marks_count'] == latest['course_unit_count']

    return render(request, 'academics/student_detail.html', {
        'student': student,
        'enrollments': enrollment_data,
        'ledgers': ledger_data,
        'can_enroll_next': can_enroll_next,
        'study_years': StudyYear.objects.all(),
        'semesters': semester.objects.all(),
    })


@require_POST
def enroll_student(request, student_id):
    """Enroll a single student for a new academic year/semester, only if the
    student's most recent enrollment (if any) has full marks recorded for all
    of its course units."""
    student = get_object_or_404(Student, id=student_id)
    study_year_id = request.POST.get('study_year') or request.POST.get('academic_year')
    semester_id = request.POST.get('semester')

    if not study_year_id or not semester_id:
        messages.error(request, "Please select both a study year and a semester.")
        return redirect('student_detail', student_id=student.id)

    study_year = get_object_or_404(StudyYear, id=study_year_id)
    semester_obj = get_object_or_404(semester, id=semester_id)

    if Enrollment.objects.filter(student=student, study_year=study_year, semester=semester_obj).exists():
        messages.error(request, "This student is already enrolled for that study year and semester.")
        return redirect('student_detail', student_id=student.id)

    latest_enrollment = Enrollment.objects.filter(student=student).order_by('-created_at').first()
    if latest_enrollment:
        course_units = CourseUnit.objects.filter(
            courses=student.course,
            year=latest_enrollment.study_year,
            semester=latest_enrollment.semester,
        )
        total_units = course_units.count()
        marked_units = Marks.objects.filter(
            enrollment=latest_enrollment,
            course_unit__in=course_units,
            test_marks__isnull=False,
            final_marks__isnull=False,
        ).count()
        if total_units == 0 or marked_units < total_units:
            messages.error(
                request,
                "Cannot enroll for a new period until all course units for the current "
                "enrollment have full marks recorded."
            )
            return redirect('student_detail', student_id=student.id)

    Enrollment.objects.create(student=student, study_year=study_year, semester=semester_obj)
    messages.success(request, f"Student enrolled for {study_year.year} - {semester_obj.semester}.")
    return redirect('student_detail', student_id=student.id)


@require_GET
def get_academic_data(request):
    """Return study years and semesters as JSON"""
    study_years = [{'id': sy.id, 'year': sy.year} for sy in StudyYear.objects.all()]
    semesters = [{'id': sem.id, 'semester': sem.semester} for sem in semester.objects.all()]
    return JsonResponse({
        'study_years': study_years,
        'semesters': semesters
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def bulk_enroll_students(request):
    """Bulk enroll selected admissions for a study year and semester.
    GET without params: return intakes, courses, study years, semesters.
    GET with intake/course: return filtered student preview (all admissions).
    POST: create academic records + enroll selected admission_ids."""
    try:
        # GET without params: return all filter options
        if request.method == 'GET' and not request.GET.get('intake') and not request.GET.get('course'):
            intakes = [{'id': i.id, 'name': i.name, 'status': i.status} for i in Intake.objects.all().order_by('-start_date')]
            courses = [{'id': c.id, 'name': c.name, 'short_name': c.short_name} for c in Course.objects.all().order_by('name')]
            study_years = [{'id': sy.id, 'year': sy.year} for sy in StudyYear.objects.all()]
            semesters = [{'id': sem.id, 'semester': sem.semester} for sem in semester.objects.all()]
            return JsonResponse({
                'intakes': intakes,
                'courses': courses,
                'study_years': study_years,
                'semesters': semesters,
            })

        if request.method == 'GET':
            # GET with params: return filtered student preview from admissions
            from django.db.models import Q
            intake_id = request.GET.get('intake')
            course_id = request.GET.get('course')
            study_year_id = request.GET.get('study_year')
            semester_id = request.GET.get('semester')

            qs = AdmissionStudent.objects.select_related('course', 'application__intake').all()
            if intake_id:
                qs = qs.filter(
                    Q(application__intake_id=intake_id) |
                    Q(academic_student__intake_id=intake_id)
                ).distinct()
            if course_id:
                qs = qs.filter(course_id=course_id)

            study_year = StudyYear.objects.filter(id=study_year_id).first() if study_year_id else None
            semester_obj = semester.objects.filter(id=semester_id).first() if semester_id else None

            students_data = []
            for adm in qs:
                # Check if an academic Student record exists
                ac_student = None
                try:
                    ac_student = adm.academic_student
                except Student.DoesNotExist:
                    pass

                already_enrolled = False
                has_academic = ac_student is not None

                if has_academic and study_year and semester_obj:
                    already_enrolled = Enrollment.objects.filter(
                        student=ac_student,
                        study_year=study_year,
                        semester=semester_obj
                    ).exists()

                # Determine intake display
                intake_name = 'N/A'
                if has_academic and ac_student.intake:
                    intake_name = ac_student.intake.name
                elif adm.application and adm.application.intake:
                    intake_name = adm.application.intake.name

                students_data.append({
                    'admission_id': adm.id,
                    'student_name': f"{adm.first_name} {adm.last_name}",
                    'student_id': adm.NSIN if adm.NSIN and adm.NSIN != '0000' else adm.admission_number,
                    'course': adm.course.name if adm.course else 'N/A',
                    'intake': intake_name,
                    'has_academic': has_academic,
                    'already_enrolled': already_enrolled,
                })
            return JsonResponse({
                'students_data': students_data,
            })

        # POST: enroll selected admissions
        study_year_id = request.POST.get('study_year')
        semester_id = request.POST.get('semester')
        admission_ids = request.POST.getlist('admission_ids')

        if not study_year_id or not semester_id:
            return JsonResponse({'success': False, 'error': 'Study year and semester are required'})
        if not admission_ids:
            return JsonResponse({'success': False, 'error': 'No students selected'})

        study_year = get_object_or_404(StudyYear, id=study_year_id)
        semester_obj = get_object_or_404(semester, id=semester_id)

        enrolled_count = 0
        skipped_count = 0
        created_count = 0
        errors = []

        for aid in admission_ids:
            try:
                adm = AdmissionStudent.objects.get(id=aid)
            except AdmissionStudent.DoesNotExist:
                errors.append(f"Admission id {aid} not found")
                continue

            # Get or create the academic Student record
            ac_student, created = Student.objects.get_or_create(admission=adm)
            if created:
                created_count += 1
                # Try to set intake from the application if available
                if adm.application and adm.application.intake:
                    ac_student.intake = adm.application.intake
                    ac_student.save()

            # Check if already enrolled
            existing = Enrollment.objects.filter(
                student=ac_student,
                study_year=study_year,
                semester=semester_obj
            ).exists()
            if existing:
                skipped_count += 1
                continue

            try:
                Enrollment.objects.create(
                    student=ac_student,
                    study_year=study_year,
                    semester=semester_obj
                )
                enrolled_count += 1
            except Exception as e:
                errors.append(f"Failed to enroll {ac_student.display_id}: {str(e)}")

        return JsonResponse({
            'success': True,
            'enrolled_count': enrolled_count,
            'skipped_count': skipped_count,
            'created_count': created_count,
            'errors': errors,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
