from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Employee(models.Model):
    CATEGORY_CHOICES = [
        ('TEACHING', 'Teaching Staff'),
        ('NON_TEACHING', 'Non-Teaching Staff'),
        ('ADMINISTRATIVE', 'Administrative Staff'),
        ('SUPPORT', 'Support Staff'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='TEACHING')
    role = models.CharField(max_length=100, help_text="Job title or position")
    start_date = models.DateField(help_text="Employment start date")
    end_date = models.DateField(null=True, blank=True, help_text="Employment end/exit date")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=100, help_text="Document name/description")
    file = models.FileField(upload_to='employee_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.employee}"
