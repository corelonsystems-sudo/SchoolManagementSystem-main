from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random

from admissions.models import Student
from academics.models import StudyYear, semester, CourseUnit, Student as AcademicStudent, Enrollment, Course
from finance.models import PaymentType, CourseFee, AdmissionFee
from staff.models import Department, Employee


class Command(BaseCommand):
    help = 'Seed the database with sample courses, admissions, and course fees'

    def handle(self, *args, **options):
        self.stdout.write('Starting data seeding...')

        # Create or get Study Years
        ay_2024, _ = StudyYear.objects.get_or_create(year='2024')
        ay_2025, _ = StudyYear.objects.get_or_create(year='2025')

        # Create or get Semesters
        sem1, _ = semester.objects.get_or_create(semester='SEM1')
        sem2, _ = semester.objects.get_or_create(semester='SEM2')

        # Create Departments
        dept_cs, _ = Department.objects.get_or_create(name='Computer Science')
        dept_bus, _ = Department.objects.get_or_create(name='Business')
        dept_eng, _ = Department.objects.get_or_create(name='Engineering')

        # Create Courses
        courses_data = [
            {'name': 'Computer Science', 'short_name': 'CS', 'duration': 48},
            {'name': 'Information Technology', 'short_name': 'IT', 'duration': 48},
            {'name': 'Software Engineering', 'short_name': 'SE', 'duration': 48},
            {'name': 'Business Administration', 'short_name': 'BA', 'duration': 36},
            {'name': 'Accounting and Finance', 'short_name': 'AF', 'duration': 36},
            {'name': 'Civil Engineering', 'short_name': 'CE', 'duration': 60},
        ]

        courses = []
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                short_name=course_data['short_name'],
                defaults=course_data
            )
            courses.append(course)
            if created:
                self.stdout.write(f'Created course: {course.name}')

        # Create Payment Types
        payment_types_data = [
            {'name': 'Tuition Fees', 'frequency': 'SEMESTERLY', 'default_amount': 1500000, 'is_tuition': True},
            {'name': 'Library Fees', 'frequency': 'YEARLY', 'default_amount': 50000, 'is_tuition': False},
            {'name': 'Laboratory Fees', 'frequency': 'SEMESTERLY', 'default_amount': 200000, 'is_tuition': False},
            {'name': 'Sports Fees', 'frequency': 'YEARLY', 'default_amount': 100000, 'is_tuition': False},
            {'name': 'Medical Fees', 'frequency': 'YEARLY', 'default_amount': 150000, 'is_tuition': False},
            {'name': 'Student Union Fees', 'frequency': 'YEARLY', 'default_amount': 50000, 'is_tuition': False},
            {'name': 'Examination Fees', 'frequency': 'SEMESTERLY', 'default_amount': 100000, 'is_tuition': False},
            {'name': 'Registration Fees', 'frequency': 'ONCE', 'default_amount': 300000, 'is_tuition': False},
        ]

        payment_types = []
        for pt_data in payment_types_data:
            pt, created = PaymentType.objects.get_or_create(
                name=pt_data['name'],
                defaults=pt_data
            )
            payment_types.append(pt)
            if created:
                self.stdout.write(f'Created payment type: {pt.name}')

        # Create Course Fees
        course_fees_data = [
            # Computer Science
            {'course': courses[0], 'study_year': ay_2024, 'semester': sem1, 'tuition_fee': 1800000},
            {'course': courses[0], 'study_year': ay_2024, 'semester': sem2, 'tuition_fee': 1800000},
            {'course': courses[0], 'study_year': ay_2025, 'semester': sem1, 'tuition_fee': 1900000},
            {'course': courses[0], 'study_year': ay_2025, 'semester': sem2, 'tuition_fee': 1900000},
            # Information Technology
            {'course': courses[1], 'study_year': ay_2024, 'semester': sem1, 'tuition_fee': 1600000},
            {'course': courses[1], 'study_year': ay_2024, 'semester': sem2, 'tuition_fee': 1600000},
            {'course': courses[1], 'study_year': ay_2025, 'semester': sem1, 'tuition_fee': 1700000},
            {'course': courses[1], 'study_year': ay_2025, 'semester': sem2, 'tuition_fee': 1700000},
            # Software Engineering
            {'course': courses[2], 'study_year': ay_2024, 'semester': sem1, 'tuition_fee': 2000000},
            {'course': courses[2], 'study_year': ay_2024, 'semester': sem2, 'tuition_fee': 2000000},
            {'course': courses[2], 'study_year': ay_2025, 'semester': sem1, 'tuition_fee': 2100000},
            {'course': courses[2], 'study_year': ay_2025, 'semester': sem2, 'tuition_fee': 2100000},
            # Business Administration
            {'course': courses[3], 'study_year': ay_2024, 'semester': sem1, 'tuition_fee': 1200000},
            {'course': courses[3], 'study_year': ay_2024, 'semester': sem2, 'tuition_fee': 1200000},
            {'course': courses[3], 'study_year': ay_2025, 'semester': sem1, 'tuition_fee': 1300000},
            {'course': courses[3], 'study_year': ay_2025, 'semester': sem2, 'tuition_fee': 1300000},
            # Accounting and Finance
            {'course': courses[4], 'study_year': ay_2024, 'semester': sem1, 'tuition_fee': 1300000},
            {'course': courses[4], 'study_year': ay_2024, 'semester': sem2, 'tuition_fee': 1300000},
            {'course': courses[4], 'study_year': ay_2025, 'semester': sem1, 'tuition_fee': 1400000},
            {'course': courses[4], 'study_year': ay_2025, 'semester': sem2, 'tuition_fee': 1400000},
            # Civil Engineering
            {'course': courses[5], 'study_year': ay_2024, 'semester': sem1, 'tuition_fee': 2200000},
            {'course': courses[5], 'study_year': ay_2024, 'semester': sem2, 'tuition_fee': 2200000},
            {'course': courses[5], 'study_year': ay_2025, 'semester': sem1, 'tuition_fee': 2300000},
            {'course': courses[5], 'study_year': ay_2025, 'semester': sem2, 'tuition_fee': 2300000},
        ]

        for cf_data in course_fees_data:
            cf, created = CourseFee.objects.get_or_create(
                course=cf_data['course'],
                study_year=cf_data['study_year'],
                semester=cf_data['semester'],
                defaults={'tuition_fee': cf_data['tuition_fee']}
            )
            if created:
                self.stdout.write(f'Created course fee: {cf}')

        # Sample student data
        first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin']
        districts = ['Kampala', 'Wakiso', 'Mukono', 'Jinja', 'Mbale', 'Gulu', 'Lira', 'Arua', 'Mbarara', 'Kabale']
        religions = ['Christian', 'Muslim', 'Catholic', 'Protestant']
        nationalities = ['Ugandan', 'Kenyan', 'Tanzanian', 'Rwandan', 'South Sudanese']

        # Create 20 students
        for i in range(20):
            first_name = first_names[i % len(first_names)]
            last_name = last_names[i % len(last_names)]
            course = courses[i % len(courses)]
            
            # Generate unique email
            email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
            
            # Generate random dates
            dob = date.today() - timedelta(days=random.randint(6570, 10950))  # 18-30 years old
            reporting_date = date.today() - timedelta(days=random.randint(30, 365))
            
            student = Student.objects.create(
                first_name=first_name,
                middle_name=random.choice(['', 'A.', 'B.', 'C.']) if random.random() > 0.5 else '',
                last_name=last_name,
                date_of_birth=dob,
                gender=random.choice(['M', 'F']),
                religion=random.choice(religions),
                nationality=random.choice(nationalities),
                birth_district=random.choice(districts),
                subcounty=f"Subcounty {i+1}",
                parish=f"Parish {i+1}",
                village=f"Village {i+1}",
                phone=f"+2567{random.randint(00000000, 99999999)}",
                email=email,
                father_name=f"Father {last_name}",
                father_phone=f"+2567{random.randint(00000000, 99999999)}",
                mother_name=f"Mother {last_name}",
                mother_phone=f"+2567{random.randint(00000000, 99999999)}",
                sponsor_name=random.choice(['Self', 'Parents', 'Government', 'Scholarship']),
                former_school=random.choice(['St. Marys College', 'King College Budo', 'Ntare School', 'Makerere College', 'Gayaza High School']),
                former_school_district=random.choice(districts),
                course=course,
                reporting=reporting_date,
                year_of_admission='2024',
                NSIN=f"CM{random.randint(1000000000, 9999999999)}",
                enrollment_status=random.choice(['ENROLLED', 'PENDING', 'ENROLLED', 'ENROLLED'])  # Weight towards enrolled
            )
            
            self.stdout.write(f'Created student: {student.first_name} {student.last_name} ({student.admission_number})')

            # Create AdmissionFee records for this student
            for pt in payment_types:
                AdmissionFee.objects.get_or_create(
                    admission=student,
                    payment_type=pt,
                    defaults={'is_active': True, 'custom_amount': None}
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded 20 students, courses, and course fees!'))
