from django.core.management.base import BaseCommand
from academics.models import AcademicYear, semester, CourseUnit, Course


class Command(BaseCommand):
    help = "Seed Course Units for the Nursing (Certificate in Enrolled Nursing) curriculum"

    def handle(self, *args, **options):
        try:
            course = Course.objects.get(short_name='Nur')
        except Course.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "Course with short_name 'Nur' (Nursing) not found. "
                "Please create the Nursing course first."
            ))
            return

        year_one, _ = AcademicYear.objects.get_or_create(year='ONE')
        year_two, _ = AcademicYear.objects.get_or_create(year='TWO')
        year_three, _ = AcademicYear.objects.get_or_create(year='THREE')

        sem1, _ = semester.objects.get_or_create(semester='SEM1')
        sem2, _ = semester.objects.get_or_create(semester='SEM2')

        # (code, name, year, semester)
        course_units = [
            # Year ONE - Semester 1
            ('CN-1101', 'Foundations of Nursing (I)', year_one, sem1),
            ('CN-1102', 'Anatomy and Physiology (I)', year_one, sem1),
            ('CN-1103', 'First Aid and Emergencies', year_one, sem1),
            ('CN-1104', 'Microbiology', year_one, sem1),
            ('CN-1105', 'Personal and Communal Health (PCH)', year_one, sem1),

            # Year ONE - Semester 2
            ('CN-1201', 'Foundation of Nursing (II)', year_one, sem2),
            ('CN-1202', 'Anatomy and Physiology (II)', year_one, sem2),
            ('CN-1203', 'Sociology and Psychology', year_one, sem2),
            ('CN-1204', 'Introduction to Computer', year_one, sem2),
            ('CN-1205', 'Primary Health Care (PHC)', year_one, sem2),

            # Year TWO - Semester 1
            ('CN-2101', 'Pharmacology (I)', year_two, sem1),
            ('CN-2102', 'Medical Nursing (I)', year_two, sem1),
            ('CN-2103', 'Surgical Nursing (I)', year_two, sem1),
            ('CN-2104', 'Paediatric Nursing (I)', year_two, sem1),
            ('CN-2105', 'Gynecological Nursing', year_two, sem1),
            ('CN-21', 'Field Placement (Hospital/Community)', year_two, sem1),

            # Year TWO - Semester 2
            ('CN-2201', 'Pharmacology (II)', year_two, sem2),
            ('CN-2202', 'Medical Nursing (II)', year_two, sem2),
            ('CN-2203', 'Surgical Nursing (II)', year_two, sem2),
            ('CN-2204', 'Mental Health Nursing', year_two, sem2),
            ('CN-2205', 'Occupational Health', year_two, sem2),
            ('CN-2206', 'Paediatric Nursing (II)', year_two, sem2),
            ('CN-22', 'Field Placement (Hospital/Community)', year_two, sem2),

            # Year THREE - Semester 1
            ('CN-3101', 'Tropical Medicine', year_three, sem1),
            ('CN-3102', 'Guidance and Counseling', year_three, sem1),
            ('CN-3103', 'Surgical Nursing (III)', year_three, sem1),
            ('CN-3104', 'Reproductive Health', year_three, sem1),
            ('CN-3105', 'Health Service Management', year_three, sem1),
            ('CN-3106', 'Entrepreneurship', year_three, sem1),
        ]

        created_count = 0
        updated_count = 0
        for code, name, year, sem in course_units:
            unit, created = CourseUnit.objects.get_or_create(
                code=code,
                defaults={'name': name, 'year': year, 'semester': sem},
            )
            if not created:
                unit.name = name
                unit.year = year
                unit.semester = sem
                unit.save()
                updated_count += 1
            else:
                created_count += 1

            unit.courses.add(course)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created_count} course units, updated {updated_count} existing ones, "
            f"all linked to '{course}'."
        ))
