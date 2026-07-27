from django.db import models, transaction
from staff.models import Department


class Application(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('ADMITTED', 'Admitted'),
    ]
    # Bio Data
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Male'), ('F', 'Female')],
        help_text="Select gender"
    )
    religion = models.CharField(max_length=50)
    nationality = models.CharField(max_length=100)
    passport_photo = models.ImageField(upload_to='application_photos/', blank=True, null=True)

    # Contact and Address Details
    birth_district = models.CharField(max_length=100)
    subcounty = models.CharField(max_length=100)
    parish = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()

    # Parents Information
    father_name = models.CharField(max_length=100)
    father_phone = models.CharField(max_length=15)
    mother_name = models.CharField(max_length=100)
    mother_phone = models.CharField(max_length=15)

    # Sponsor Information
    sponsor_name = models.CharField(max_length=100)

    # Previous School Information
    former_school = models.CharField(max_length=200, blank=True)
    former_school_district = models.CharField(max_length=100, blank=True)

    # Academic Information
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE)
    intake = models.ForeignKey('academics.Intake', on_delete=models.CASCADE, related_name='applications')
    year_of_admission = models.CharField(max_length=15)

    NSIN = models.CharField(max_length=20, blank=True, default='', help_text="National Student Identification Number. Leave blank if not yet assigned.")

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Application status"
    )
    application_date = models.DateTimeField(auto_now_add=True)
    review_notes = models.TextField(blank=True, help_text="Notes from the review process")

    class Meta:
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        ordering = ['-application_date']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.course.short_name} ({self.status})"


class Student(models.Model):
    # Link to the application that led to this admission
    application = models.OneToOneField(
        'Application',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admitted_student',
        help_text="The application this student was admitted from"
    )

    # Bio Data
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)  # Optional middle name
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Male'), ('F', 'Female')],
        help_text="Select gender"
    )  # Gender choices
    religion = models.CharField(max_length=50)
    nationality = models.CharField(max_length=100)
    passport_photo = models.ImageField(upload_to='passport_photos/', blank=True, null=True)

    # Contact and Address Details
    birth_district = models.CharField(max_length=100)
    subcounty = models.CharField(max_length=100)
    parish = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)

    # Parents Information
    father_name = models.CharField(max_length=100)
    father_phone = models.CharField(max_length=15)
    mother_name = models.CharField(max_length=100)
    mother_phone = models.CharField(max_length=15)

    # Sponsor Information
    sponsor_name = models.CharField(max_length=100)

    # Previous School Information
    former_school = models.CharField(max_length=200, blank=True)
    former_school_district = models.CharField(max_length=100, blank=True)

    # Academic Information
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=20, unique=True, blank=True)
    reporting = models.DateField( blank=True, null=True)
    year_of_admission = models.CharField(max_length=15)

    NSIN = models.CharField(max_length=20, unique=False, blank=True, default='', help_text="National Student Identification Number. Leave blank if not yet assigned.")

    ENROLLMENT_STATUS_CHOICES = [
        ('ENROLLED', 'Enrolled'),
        ('PENDING', 'Pending'),
        ('DEFERRED', 'Deferred'),
        ('COMPLETED', 'Completed'),
        ('WITHDRAWN', 'Withdrawn'),
    ]
    enrollment_status = models.CharField(
        max_length=15,
        choices=ENROLLMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Current enrollment status of the student"
    )

    def save(self, *args, **kwargs):
        if not self.admission_number:
            with transaction.atomic():
                count = Student.objects.filter(course=self.course).count() + 1
                proposed_admission_number = f"{str(count).zfill(3)}-{self.course.short_name}"

                # Ensure the admission number is unique
                while Student.objects.filter(admission_number=proposed_admission_number).exists():
                    count += 1
                    proposed_admission_number = f"{str(count).zfill(3)}-{self.course.short_name}"

                self.admission_number = proposed_admission_number
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Admission'
        verbose_name_plural = 'Admissions'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.admission_number})"


class Document(models.Model):
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    name = models.CharField(max_length=200)  # Name or description of the document
    file = models.FileField(upload_to='student_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.student.first_name} {self.student.last_name}"


class ApplicationDocument(models.Model):
    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    name = models.CharField(max_length=200, help_text="Document name or description")
    file = models.FileField(upload_to='application_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Application Document'
        verbose_name_plural = 'Application Documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.name} - {self.application.first_name} {self.application.last_name}"
