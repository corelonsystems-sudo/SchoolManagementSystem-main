import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolManagementSystem.settings')
django.setup()

from academics.models import Student
from admissions.models import Student as AdmissionsStudent

print('Academics Students (enrolled):')
academics_students = Student.objects.all()
if academics_students:
    for s in academics_students:
        print(f'  - {s.admission.first_name} {s.admission.last_name} - Course: {s.admission.course.name if s.admission.course else "None"}')
else:
    print('  No academics students found')

print('\nAdmissions Students with course:')
admissions_students = AdmissionsStudent.objects.all()[:20]
if admissions_students:
    for s in admissions_students:
        print(f'  - {s.first_name} {s.last_name} - Course: {s.course.name if s.course else "None"} - Status: {s.enrollment_status}')
else:
    print('  No admissions students found')

print('\nNursing course ID:')
from academics.models import Course
nursing = Course.objects.get(short_name='CN')
print(f'  Nursing ID: {nursing.id}')
