from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Student, Application, ApplicationDocument
from academics.models import Course, Intake
from django.core.serializers.json import DjangoJSONEncoder
import json
from io import BytesIO
from xhtml2pdf import pisa


def apply_view(request):
    """Public application form for prospective students"""
    # Only show open intakes
    open_intakes = Intake.objects.filter(status='OPEN').select_related('academic_year')
    courses = Course.objects.all()

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

            # Handle passport photo upload
            if 'passport_photo' in request.FILES:
                application.passport_photo = request.FILES['passport_photo']
                application.save()

            # Handle supporting document uploads
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

            messages.success(request, 'Your application has been submitted successfully. We will review it and get back to you.')
            return redirect('apply_success')

        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')

    return render(request, 'admissions/apply.html', {
        'open_intakes': open_intakes,
        'courses': courses,
    })


def apply_success(request):
    """Success page after application submission"""
    return render(request, 'admissions/apply_success.html')


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
