import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolManagementSystem.settings')
django.setup()

from admissions.models import Application
from academics.models import Course, Intake
from datetime import date
import random

# Get courses
nursing = Course.objects.get(short_name='CN')
midwifery = Course.objects.get(short_name='CMID')

# Get latest intake
intake = Intake.objects.filter(name__contains='JULY 2026').first()
if not intake:
    intake = Intake.objects.last()

# Sample data
first_names = ['John', 'Mary', 'James', 'Grace', 'Peter', 'Sarah', 'David', 'Esther', 'Michael', 'Anna']
last_names = ['Owino', 'Achieng', 'Omondi', 'Akinyi', 'Otieno', 'Njeri', 'Kamau', 'Wanjiku', 'Mwangi', 'Nyambura']
districts = ['Kampala', 'Wakiso', 'Mukono', 'Jinja', 'Mbale', 'Gulu', 'Lira', 'Arua', 'Mbarara', 'Kabale']
religions = ['Christian', 'Muslim', 'Catholic', 'Pentecostal']
genders = ['M', 'F']

# Create 10 applications for Nursing
print("Creating 10 applications for Nursing...")
for i in range(10):
    app = Application.objects.create(
        first_name=random.choice(first_names),
        middle_name='',
        last_name=random.choice(last_names),
        date_of_birth=date(2000 + random.randint(0, 5), random.randint(1, 12), random.randint(1, 28)),
        gender=random.choice(genders),
        religion=random.choice(religions),
        nationality='Ugandan',
        birth_district=random.choice(districts),
        subcounty=random.choice(districts),
        parish=random.choice(districts),
        village=random.choice(districts),
        phone=f'+2567{random.randint(0,9)}{random.randint(10000000, 99999999)}',
        email=f'student_nursing_{i+1}@example.com',
        father_name=f'Father {random.choice(last_names)}',
        father_phone=f'+2567{random.randint(0,9)}{random.randint(10000000, 99999999)}',
        mother_name=f'Mother {random.choice(last_names)}',
        mother_phone=f'+2567{random.randint(0,9)}{random.randint(10000000, 99999999)}',
        course=nursing,
        intake=intake,
        status='PENDING'
    )
    print(f"  Created: {app.first_name} {app.last_name}")

# Create 10 applications for Midwifery
print("\nCreating 10 applications for Midwifery...")
for i in range(10):
    app = Application.objects.create(
        first_name=random.choice(first_names),
        middle_name='',
        last_name=random.choice(last_names),
        date_of_birth=date(2000 + random.randint(0, 5), random.randint(1, 12), random.randint(1, 28)),
        gender=random.choice(genders),
        religion=random.choice(religions),
        nationality='Ugandan',
        birth_district=random.choice(districts),
        subcounty=random.choice(districts),
        parish=random.choice(districts),
        village=random.choice(districts),
        phone=f'+2567{random.randint(0,9)}{random.randint(10000000, 99999999)}',
        email=f'student_midwifery_{i+1}@example.com',
        father_name=f'Father {random.choice(last_names)}',
        father_phone=f'+2567{random.randint(0,9)}{random.randint(10000000, 99999999)}',
        mother_name=f'Mother {random.choice(last_names)}',
        mother_phone=f'+2567{random.randint(0,9)}{random.randint(10000000, 99999999)}',
        course=midwifery,
        intake=intake,
        status='PENDING'
    )
    print(f"  Created: {app.first_name} {app.last_name}")

print("\nDone! Created 20 test applications (10 for Nursing, 10 for Midwifery).")
