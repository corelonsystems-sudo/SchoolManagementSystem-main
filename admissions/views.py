from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Student, Application, ApplicationDocument
from academics.models import Course, Intake
from django.core.serializers.json import DjangoJSONEncoder
import json
from io import BytesIO
from xhtml2pdf import pisa
from datetime import datetime


def portal_landing(request):
    """Public landing page for the application portal"""
    open_intakes = Intake.objects.filter(status='OPEN').select_related('academic_year')
    courses = Course.objects.all().order_by('name')
    return render(request, 'admissions/portal/landing.html', {
        'open_intakes': open_intakes,
        'courses': courses,
    })


def apply_view(request):
    """Public application form for prospective students"""
    open_intakes = Intake.objects.filter(status__in=['OPEN', 'UPCOMING']).select_related('academic_year')
    courses = Course.objects.all().order_by('name')

    if request.method == 'POST':
        try:
            application = Application.objects.create(
                first_name=request.POST.get('first_name'),
                middle_name=request.POST.get('middle_name', ''),
                last_name=request.POST.get('last_name'),
                date_of_birth=request.POST.get('date_of_birth'),
                gender=request.POST.get('gender'),
                religion=request.POST.get('religion'),
                nationality=request.POST.get('nationality'),
                birth_district=request.POST.get('birth_district'),
                subcounty=request.POST.get('subcounty'),
                parish=request.POST.get('parish'),
                village=request.POST.get('village'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email'),
                father_name=request.POST.get('father_name'),
                father_phone=request.POST.get('father_phone'),
                mother_name=request.POST.get('mother_name'),
                mother_phone=request.POST.get('mother_phone'),
                sponsor_name=request.POST.get('sponsor_name'),
                former_school=request.POST.get('former_school', ''),
                former_school_district=request.POST.get('former_school_district', ''),
                course_id=request.POST.get('course'),
                intake_id=request.POST.get('intake'),
                year_of_admission=request.POST.get('year_of_admission'),
                NSIN=request.POST.get('NSIN', ''),
                status='PENDING'
            )

            if 'passport_photo' in request.FILES:
                application.passport_photo = request.FILES['passport_photo']
                application.save()

            for key in request.FILES:
                if key.startswith('doc_file_'):
                    name_key = key.replace('doc_file_', 'doc_name_')
                    doc_name = request.POST.get(name_key, '').strip()
                    if not doc_name:
                        doc_name = 'Untitled Document'
                    ApplicationDocument.objects.create(
                        application=application,
                        name=doc_name,
                        file=request.FILES[key]
                    )

            messages.success(request, 'Your application has been submitted successfully.')
            return redirect('apply_success')

        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')

    return render(request, 'admissions/portal/apply.html', {
        'open_intakes': open_intakes,
        'courses': courses,
    })


def apply_success(request):
    """Success page after application submission"""
    return render(request, 'admissions/portal/success.html')


def lookup_application(request):
    """Look up an existing application by email or phone or NSIN"""
    if request.method == 'POST':
        lookup_value = request.POST.get('lookup_value', '').strip()
        lookup_type = request.POST.get('lookup_type', 'email')

        applications = None
        if lookup_type == 'email':
            applications = Application.objects.filter(email__iexact=lookup_value)
        elif lookup_type == 'phone':
            applications = Application.objects.filter(phone__iexact=lookup_value)
        elif lookup_type == 'nsin':
            applications = Application.objects.filter(NSIN__iexact=lookup_value)

        if applications and applications.exists():
            if applications.count() == 1:
                return redirect('update_application', application_id=applications.first().id)
            else:
                return render(request, 'admissions/portal/lookup.html', {
                    'applications': applications,
                    'lookup_value': lookup_value,
                    'lookup_type': lookup_type,
                    'multiple': True,
                })
        else:
            # Also check Student model
            students = None
            if lookup_type == 'email':
                students = Student.objects.filter(email__iexact=lookup_value)
            elif lookup_type == 'phone':
                students = Student.objects.filter(phone__iexact=lookup_value)
            elif lookup_type == 'nsin':
                students = Student.objects.filter(NSIN__iexact=lookup_value)

            if students and students.exists():
                if students.count() == 1:
                    return redirect('update_student', student_id=students.first().id)
                else:
                    return render(request, 'admissions/portal/lookup.html', {
                        'students': students,
                        'lookup_value': lookup_value,
                        'lookup_type': lookup_type,
                        'multiple_students': True,
                    })

            messages.error(request, f'No application or student record found with that {lookup_type}. Please check and try again, or submit a new application.')

    return render(request, 'admissions/portal/lookup.html')


def update_application(request, application_id):
    """Update an existing application's details"""
    application = get_object_or_404(Application, id=application_id)
    courses = Course.objects.all().order_by('name')
    intakes = Intake.objects.filter(status__in=['OPEN', 'UPCOMING', 'CLOSED']).select_related('academic_year')

    if request.method == 'POST':
        try:
            application.first_name = request.POST.get('first_name', application.first_name)
            application.middle_name = request.POST.get('middle_name', '')
            application.last_name = request.POST.get('last_name', application.last_name)
            application.date_of_birth = request.POST.get('date_of_birth', application.date_of_birth)
            application.gender = request.POST.get('gender', application.gender)
            application.religion = request.POST.get('religion', application.religion)
            application.nationality = request.POST.get('nationality', application.nationality)
            application.birth_district = request.POST.get('birth_district', application.birth_district)
            application.subcounty = request.POST.get('subcounty', application.subcounty)
            application.parish = request.POST.get('parish', application.parish)
            application.village = request.POST.get('village', application.village)
            application.phone = request.POST.get('phone', application.phone)
            application.email = request.POST.get('email', application.email)
            application.father_name = request.POST.get('father_name', application.father_name)
            application.father_phone = request.POST.get('father_phone', application.father_phone)
            application.mother_name = request.POST.get('mother_name', application.mother_name)
            application.mother_phone = request.POST.get('mother_phone', application.mother_phone)
            application.sponsor_name = request.POST.get('sponsor_name', application.sponsor_name)
            application.former_school = request.POST.get('former_school', '')
            application.former_school_district = request.POST.get('former_school_district', '')
            application.year_of_admission = request.POST.get('year_of_admission', application.year_of_admission)
            application.NSIN = request.POST.get('NSIN', '')

            course_id = request.POST.get('course')
            if course_id:
                application.course_id = course_id
            intake_id = request.POST.get('intake')
            if intake_id:
                application.intake_id = intake_id

            if 'passport_photo' in request.FILES:
                application.passport_photo = request.FILES['passport_photo']

            application.save()

            for key in request.FILES:
                if key.startswith('doc_file_'):
                    name_key = key.replace('doc_file_', 'doc_name_')
                    doc_name = request.POST.get(name_key, '').strip()
                    if not doc_name:
                        doc_name = 'Untitled Document'
                    ApplicationDocument.objects.create(
                        application=application,
                        name=doc_name,
                        file=request.FILES[key]
                    )

            messages.success(request, 'Your application details have been updated successfully.')
            return redirect('update_success')

        except Exception as e:
            messages.error(request, f'Error updating application: {str(e)}')

    return render(request, 'admissions/portal/update_form.html', {
        'application': application,
        'courses': courses,
        'intakes': intakes,
        'existing_docs': application.documents.all(),
    })


def update_student(request, student_id):
    """Update an existing student's details (for already enrolled students)"""
    student = get_object_or_404(Student, id=student_id)
    courses = Course.objects.all().order_by('name')

    if request.method == 'POST':
        try:
            student.first_name = request.POST.get('first_name', student.first_name)
            student.middle_name = request.POST.get('middle_name', '')
            student.last_name = request.POST.get('last_name', student.last_name)
            student.date_of_birth = request.POST.get('date_of_birth', student.date_of_birth)
            student.gender = request.POST.get('gender', student.gender)
            student.religion = request.POST.get('religion', student.religion)
            student.nationality = request.POST.get('nationality', student.nationality)
            student.birth_district = request.POST.get('birth_district', student.birth_district)
            student.subcounty = request.POST.get('subcounty', student.subcounty)
            student.parish = request.POST.get('parish', student.parish)
            student.village = request.POST.get('village', student.village)
            student.phone = request.POST.get('phone', student.phone)
            student.email = request.POST.get('email', student.email)
            student.father_name = request.POST.get('father_name', student.father_name)
            student.father_phone = request.POST.get('father_phone', student.father_phone)
            student.mother_name = request.POST.get('mother_name', student.mother_name)
            student.mother_phone = request.POST.get('mother_phone', student.mother_phone)
            student.sponsor_name = request.POST.get('sponsor_name', student.sponsor_name)
            student.former_school = request.POST.get('former_school', '')
            student.former_school_district = request.POST.get('former_school_district', '')
            student.NSIN = request.POST.get('NSIN', '')

            if 'passport_photo' in request.FILES:
                student.passport_photo = request.FILES['passport_photo']

            student.save()

            messages.success(request, 'Your details have been updated successfully.')
            return redirect('update_success')

        except Exception as e:
            messages.error(request, f'Error updating details: {str(e)}')

    return render(request, 'admissions/portal/update_student.html', {
        'student': student,
        'courses': courses,
    })


def update_success(request):
    """Success page after updating details"""
    return render(request, 'admissions/portal/update_success.html')


def add_old_application(request):
    """Public form for registering an old/historical application"""
    all_intakes = Intake.objects.all().select_related('academic_year').order_by('-start_date')
    courses = Course.objects.all().order_by('name')

    if request.method == 'POST':
        try:
            dob_str = request.POST.get('date_of_birth', '').strip()
            dob = None
            if dob_str:
                date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']
                for fmt in date_formats:
                    try:
                        dob = datetime.strptime(dob_str, fmt).date()
                        break
                    except ValueError:
                        continue

            gender = request.POST.get('gender', '').strip().upper()
            if gender and gender not in ('M', 'F'):
                if gender.startswith('M'):
                    gender = 'M'
                elif gender.startswith('F'):
                    gender = 'F'

            Application.objects.create(
                first_name=request.POST.get('first_name', '').strip(),
                middle_name=request.POST.get('middle_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                date_of_birth=dob,
                gender=gender or 'M',
                religion=request.POST.get('religion', '').strip(),
                nationality=request.POST.get('nationality', '').strip(),
                birth_district=request.POST.get('birth_district', '').strip(),
                subcounty=request.POST.get('subcounty', '').strip(),
                parish=request.POST.get('parish', '').strip(),
                village=request.POST.get('village', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
                father_name=request.POST.get('father_name', '').strip(),
                father_phone=request.POST.get('father_phone', '').strip(),
                mother_name=request.POST.get('mother_name', '').strip(),
                mother_phone=request.POST.get('mother_phone', '').strip(),
                sponsor_name=request.POST.get('sponsor_name', '').strip(),
                former_school=request.POST.get('former_school', '').strip(),
                former_school_district=request.POST.get('former_school_district', '').strip(),
                course_id=request.POST.get('course'),
                intake_id=request.POST.get('intake'),
                year_of_admission=request.POST.get('year_of_admission', '').strip(),
                NSIN=request.POST.get('NSIN', '').strip(),
                status='PENDING',
            )

            messages.success(request, 'Your old application record has been submitted successfully.')
            return redirect('old_application_success')

        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')

    return render(request, 'admissions/portal/add_old_application.html', {
        'all_intakes': all_intakes,
        'courses': courses,
    })


def old_application_success(request):
    """Success page after old application submission"""
    return render(request, 'admissions/portal/old_application_success.html')


def student_login(request):
    """Login for enrolled students using email + admission number"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        admission_number = request.POST.get('admission_number', '').strip()

        if not email or not admission_number:
            messages.error(request, 'Please enter both your email and admission number.')
        else:
            student = Student.objects.filter(
                email__iexact=email,
                admission_number__iexact=admission_number
            ).first()

            if student:
                request.session['student_portal_id'] = student.id
                return redirect('student_dashboard')
            else:
                messages.error(request, 'No student found with those credentials. Please check and try again.')

    return render(request, 'admissions/portal/student_login.html')


def student_logout(request):
    """Logout student from portal"""
    if 'student_portal_id' in request.session:
        del request.session['student_portal_id']
    return redirect('portal_landing')


def student_dashboard(request):
    """Student dashboard showing enrollment history, performance, and payments"""
    student_id = request.session.get('student_portal_id')
    if not student_id:
        return redirect('student_login')

    from academics.models import Student as AcademicsStudent, Enrollment, CourseUnit, Marks, StudyYear
    from finance.models import Ledger, Payment

    adm_student = get_object_or_404(Student, id=student_id)

    # Try to get the academics.Student record
    acad_student = AcademicsStudent.objects.filter(admission=adm_student).first()

    enrollment_data = []
    ledger_data = []

    if acad_student:
        # Enrollment history with marks
        enrollments = Enrollment.objects.filter(
            student=acad_student
        ).select_related('study_year', 'semester').order_by('-created_at')

        for enrollment in enrollments:
            course_units = CourseUnit.objects.filter(
                courses=acad_student.course,
                year=enrollment.study_year,
                semester=enrollment.semester,
            ).order_by('code')

            unit_marks = {}
            total_score = 0
            marks_count = 0
            for cu in course_units:
                mark = Marks.objects.filter(enrollment=enrollment, course_unit=cu).first()
                if mark and mark.total_marks() is not None:
                    unit_marks[cu.id] = {
                        'test_marks': mark.test_marks,
                        'final_marks': mark.final_marks,
                        'total_marks': mark.total_marks(),
                    }
                    total_score += float(mark.total_marks())
                    marks_count += 1

            avg_score = round(total_score / marks_count, 1) if marks_count > 0 else None

            enrollment_data.append({
                'enrollment': enrollment,
                'course_units': course_units,
                'unit_marks': unit_marks,
                'average_score': avg_score,
                'marks_count': marks_count,
                'unit_count': course_units.count(),
            })

        # Finance data
        ledgers = Ledger.objects.filter(
            student=acad_student
        ).select_related('study_year', 'semester').prefetch_related(
            'payment_type_breakdowns__payment_type'
        ).order_by('-generated_on')

        for ledger in ledgers:
            payments = Payment.objects.filter(
                enrollment__student=acad_student,
                enrollment__study_year=ledger.study_year,
                enrollment__semester=ledger.semester
            ).order_by('-date')

            payment_type_paid = {}
            for payment in payments:
                pt_id = payment.payment_type.id
                payment_type_paid[pt_id] = payment_type_paid.get(pt_id, 0) + float(payment.amount)

            breakdowns_with_paid = []
            for breakdown in ledger.payment_type_breakdowns.all():
                paid_amount = payment_type_paid.get(breakdown.payment_type.id, 0)
                balance = float(breakdown.amount) - paid_amount
                breakdowns_with_paid.append({
                    'payment_type': breakdown.payment_type,
                    'amount': breakdown.amount,
                    'paid': paid_amount,
                    'balance': balance,
                })

            total_required = float(ledger.required_amount)
            total_paid = sum(p['paid'] for p in breakdowns_with_paid)
            total_balance = total_required - total_paid

            ledger_data.append({
                'ledger': ledger,
                'payments': payments,
                'breakdowns': breakdowns_with_paid,
                'total_required': total_required,
                'total_paid': total_paid,
                'total_balance': total_balance,
                'payment_count': payments.count(),
            })

    return render(request, 'admissions/portal/student_dashboard.html', {
        'adm_student': adm_student,
        'acad_student': acad_student,
        'enrollment_data': enrollment_data,
        'ledger_data': ledger_data,
        'grand_total_paid': sum(ld['total_paid'] for ld in ledger_data),
        'grand_total_balance': sum(ld['total_balance'] for ld in ledger_data if ld['total_balance'] > 0),
    })


def student_list(request):
    name = request.GET.get('name', '')
    admission_number = request.GET.get('admission_number', '')
    year_of_admission = request.GET.get('year_of_admission', '')

    students = Student.objects.select_related('course').all()

    if name:
        students = students.filter(first_name__icontains=name) | students.filter(last_name__icontains=name)
    if admission_number:
        students = students.filter(admission_number__icontains=admission_number)
    if year_of_admission:
        students = students.filter(year_of_admission=year_of_admission)

    # Serialize student data
    student_data = [
        {
            "first_name": student.first_name,
            "last_name": student.last_name,
            "admission_number": student.admission_number,
            "course": student.course.name,
            "year_of_admission": student.year_of_admission,
            "email": student.email,
            "phone": student.phone,
            "enrollment_status": student.get_enrollment_status_display(),
        }
        for student in students
    ]

    return render(request, 'admissions/student_list.html', {
        'students': students,
        'student_json': json.dumps(student_data, cls=DjangoJSONEncoder),
    })


def student_admission_form(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    return render(request, 'admissions/admission_form.html', {'student': student})


from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from .models import Student

def admission_letter(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    context = {
        'student': student,
    }

    html_content = render_to_string('admissions/admission_form.html', context)

    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

    if pisa_status.err:
        return HttpResponse('Failed to generate admission letter PDF.', status=500)

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="admission_letter_{student.admission_number}.pdf"'
    return response
