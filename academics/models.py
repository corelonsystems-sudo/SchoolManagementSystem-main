from django.db import models
from django.utils import timezone
from admissions.models import Student
from staff.models import Employee, Department
from django.apps import apps


class AcademicYear(models.Model):
    name = models.CharField(max_length=50, help_text="e.g., 2024-2025", null=True, blank=True)
    start_date = models.DateField(help_text="Start date of the academic year", null=True, blank=True)
    end_date = models.DateField(help_text="End date of the academic year", null=True, blank=True)
    is_current = models.BooleanField(default=False, help_text="Mark as current academic year")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'Academic Year'
        verbose_name_plural = 'Academic Years'
        ordering = ['-start_date']

    def __str__(self):
        return self.name or f"Academic Year {self.id}"

    def save(self, *args, **kwargs):
        # If this is set as current, unset all others
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class StudyYear(models.Model):
    year = models.CharField(unique=True, max_length=4, help_text="e.g., 2026")

    class Meta:
        verbose_name = 'Study Year'
        verbose_name_plural = 'Study Years'
        ordering = ['-year']

    def __str__(self):
        return str(self.year)


class Intake(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('UPCOMING', 'Upcoming'),
    ]
    name = models.CharField(max_length=100, help_text="Intake name, e.g., January 2026 Intake")
    academic_year = models.ForeignKey('AcademicYear', on_delete=models.CASCADE, related_name='intakes')
    start_date = models.DateField(help_text="Start date for this intake")
    end_date = models.DateField(help_text="Application deadline for this intake")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='UPCOMING')
    description = models.TextField(blank=True, help_text="Description of the intake")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Intake'
        verbose_name_plural = 'Intakes'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.academic_year.name})"


class Course(models.Model):
    LEVEL_CHOICES = [
        ('CERTIFICATE', 'Certificate'),
        ('DIPLOMA', 'Diploma'),
        ('BACHELORS', "Bachelor's"),
        ('MASTERS', "Master's"),
    ]
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=10, unique=True)  # e.g., CS for Computer Science
    duration = models.IntegerField(help_text="Duration in months")  # Course duration in months
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='CERTIFICATE',
        help_text="Academic level of the course"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        help_text="Department this course belongs to"
    )

    def __str__(self):
        return f"{self.name} ({self.short_name})"


class semester(models.Model):
    semester = models.CharField(unique=True, max_length=4)

    def __str__(self):
        return str(self.semester)


class CourseUnit(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    year = models.ForeignKey(StudyYear, on_delete=models.SET_NULL, null=True, blank=True)
    semester = models.ForeignKey(semester, on_delete=models.SET_NULL, null=True, blank=True)
    tutor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    departments = models.ManyToManyField(Department, blank=True, related_name='course_units')
    courses = models.ManyToManyField('Course', blank=True, related_name='course_units')

    def __str__(self):
        return f"{self.name} ({self.code})"


class Student(models.Model):
    admission = models.OneToOneField(
        'admissions.Student',
        on_delete=models.CASCADE,
        related_name='academic_student',
        help_text="The admission record this enrolled student was created from"
    )
    intake = models.ForeignKey(
        'Intake',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text="The intake this student belongs to"
    )
    reg_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Auto-generated registration number shown when NSIN is not available"
    )

    def __str__(self):
        return f"{self.admission.first_name} {self.admission.last_name} ({self.display_id})"

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def generate_reg_number(self):
        last = Student.objects.order_by('-id').values_list('id', flat=True).first()
        next_id = (last or 0) + 1
        return f"REG-{next_id:04d}"

    def save(self, *args, **kwargs):
        if not self.reg_number:
            self.reg_number = self.generate_reg_number()
        super().save(*args, **kwargs)

    @property
    def display_id(self):
        nsin = self.NSIN
        if nsin and str(nsin).strip():
            return nsin
        return self.reg_number

    @property
    def first_name(self):
        return self.admission.first_name

    @property
    def last_name(self):
        return self.admission.last_name

    @property
    def phone(self):
        return self.admission.phone

    @property
    def email(self):
        return self.admission.email

    @property
    def passport_photo(self):
        return self.admission.passport_photo

    @property
    def course(self):
        return self.admission.course

    @property
    def NSIN(self):
        return self.admission.NSIN


class Enrollment(models.Model):
    student = models.ForeignKey('academics.Student', on_delete=models.CASCADE)
    study_year = models.ForeignKey(StudyYear, on_delete=models.CASCADE, null=True, blank=True)
    semester = models.ForeignKey(semester, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        year = self.study_year.year if self.study_year else "No Year"
        return f"{self.student} - {year}"


from decimal import Decimal

class Marks(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    course_unit = models.ForeignKey(CourseUnit, on_delete=models.CASCADE)
    test_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def total_marks(self):
        """Calculate total marks (test + final)"""
        if self.test_marks is not None and self.final_marks is not None:
            # Convert the float to Decimal to avoid the TypeError
            test_weight = Decimal('0.30')
            final_weight = Decimal('0.70')

            total = (self.test_marks * test_weight) + (self.final_marks * final_weight)
            return total.quantize(Decimal('0.01'))  # Rounding to two decimal places
        return None

    def __str__(self):
        return f"{self.enrollment.student} - {self.course_unit.name} Marks"