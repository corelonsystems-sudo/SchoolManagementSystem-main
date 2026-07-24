from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Count
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
import json
from .models import Student, Document, Application, ApplicationDocument
from finance.models import AdmissionFee
from academics.models import StudyYear, semester


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 1
    fields = ['name', 'file']
    max_num = 10


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'course', 'intake', 'status', 'application_date', 'admit_action']
    list_filter = ['status', 'course', 'intake']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    date_hierarchy = 'application_date'
    readonly_fields = ['application_date']

    fieldsets = [
        ('Application Status', {
            'fields': ['status', 'review_notes']
        }),
        ('Student Bio Data', {
            'fields': [
                'passport_photo', 'first_name', 'middle_name',
                'last_name', 'date_of_birth', 'gender',
                'religion', 'nationality'
            ]
        }),
        ('Contact and Address Details', {
            'fields': [
                'birth_district', 'subcounty', 'parish',
                'village', 'phone', 'email'
            ]
        }),
        ('Parents Information', {
            'fields': [
                'father_name', 'father_phone',
                'mother_name', 'mother_phone'
            ]
        }),
        ('Sponsor Information', {
            'fields': ['sponsor_name']
        }),
        ('Previous School Information', {
            'fields': ['former_school', 'former_school_district']
        }),
        ('Academic Information', {
            'fields': ['course', 'intake', 'year_of_admission', 'NSIN']
        }),
    ]
    inlines = [ApplicationDocumentInline]

    def admit_action(self, obj):
        buttons = []
        try:
            has_student = obj.admitted_student.exists()
        except:
            has_student = False
        
        if obj.status == 'PENDING' or obj.status == 'UNDER_REVIEW':
            buttons.append(format_html(
                '<a href="{}" class="button" style="background-color:#28a745;margin-right:5px;">Admit</a>',
                reverse('admin:admit_application', args=[obj.id])
            ))
            buttons.append(format_html(
                '<a href="{}" class="button" style="background-color:#dc3545;">Reject</a>',
                reverse('admin:reject_application', args=[obj.id])
            ))
        elif obj.status == 'ACCEPTED' and not has_student:
            buttons.append(format_html(
                '<a href="{}" class="button" style="background-color:#28a745;">Admit</a>',
                reverse('admin:admit_application', args=[obj.id])
            ))
        elif obj.status == 'ADMITTED' or has_student:
            return format_html('<span style="color:green;font-weight:bold;">Admitted</span>')
        elif obj.status == 'REJECTED':
            return format_html('<span style="color:red;font-weight:bold;">Rejected</span>')
        return format_html(' '.join(buttons)) if buttons else '-'
    admit_action.short_description = 'Actions'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:application_id>/admit/', self.admin_site.admin_view(self.admit_application_view), name='admit_application'),
            path('<int:application_id>/reject/', self.admin_site.admin_view(self.reject_application_view), name='reject_application'),
        ]
        return custom_urls + urls

    def admit_application_view(self, request, application_id):
        from django.shortcuts import get_object_or_404
        application = get_object_or_404(Application, id=application_id)

        if application.status == 'REJECTED':
            messages.error(request, 'Rejected applications cannot be admitted.')
            return redirect('admin:admissions_application_changelist')

        try:
            has_student = application.admitted_student.exists()
        except:
            has_student = False

        if has_student:
            messages.warning(request, 'This application has already been admitted.')
            return redirect('admin:admissions_application_changelist')

        # Create a Student from the application
        student = Student.objects.create(
            application=application,
            first_name=application.first_name,
            middle_name=application.middle_name,
            last_name=application.last_name,
            date_of_birth=application.date_of_birth,
            gender=application.gender,
            religion=application.religion,
            nationality=application.nationality,
            passport_photo=application.passport_photo,
            birth_district=application.birth_district,
            subcounty=application.subcounty,
            parish=application.parish,
            village=application.village,
            phone=application.phone,
            email=application.email,
            father_name=application.father_name,
            father_phone=application.father_phone,
            mother_name=application.mother_name,
            mother_phone=application.mother_phone,
            sponsor_name=application.sponsor_name,
            former_school=application.former_school,
            former_school_district=application.former_school_district,
            course=application.course,
            year_of_admission=application.year_of_admission,
            NSIN=application.NSIN,
            enrollment_status='ENROLLED'
        )

        # Update application status
        application.status = 'ADMITTED'
        application.save()

        # Copy application documents to student documents
        for app_doc in application.documents.all():
            Document.objects.create(
                student=student,
                name=app_doc.name,
                file=app_doc.file
            )

        messages.success(request, f'Student {student.first_name} {student.last_name} has been admitted successfully.')
        return redirect('admin:admissions_student_change', student.id)

    def reject_application_view(self, request, application_id):
        from django.shortcuts import get_object_or_404
        application = get_object_or_404(Application, id=application_id)

        try:
            has_student = application.admitted_student.exists()
        except:
            has_student = False

        if application.status == 'ADMITTED' or has_student:
            messages.error(request, 'Admitted applications cannot be rejected.')
            return redirect('admin:admissions_application_changelist')

        if application.status == 'REJECTED':
            messages.warning(request, 'This application has already been rejected.')
            return redirect('admin:admissions_application_changelist')

        # Update application status
        application.status = 'REJECTED'
        application.save()

        messages.success(request, f'Application from {application.first_name} {application.last_name} has been rejected.')
        return redirect('admin:admissions_application_changelist')


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ['name', 'file']
    max_num = 10

class AdmissionFeeInline(admin.TabularInline):
    model = AdmissionFee
    extra = 0
    fields = ['payment_type_display', 'frequency_display', 'default_amount_display', 'custom_amount', 'is_active']
    readonly_fields = ['payment_type_display', 'frequency_display', 'default_amount_display']
    autocomplete_fields = []

    def payment_type_display(self, obj):
        return obj.payment_type.name
    payment_type_display.short_description = 'Payment Type'

    def frequency_display(self, obj):
        return obj.payment_type.get_frequency_display()
    frequency_display.short_description = 'Frequency'

    def default_amount_display(self, obj):
        return obj.payment_type.default_amount
    default_amount_display.short_description = 'Default Amount'

from django.utils.html import format_html

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    actions = []
    change_list_template = 'admin/admissions/student/change_list.html'
    list_display = ['first_name', 'last_name', 'admission_number', 'course', 'get_intake', 'year_of_admission', 'student_actions']
    search_fields = ['first_name', 'last_name', 'admission_number']
    list_filter = ['course', 'year_of_admission', 'enrollment_status']
    readonly_fields = ['admission_number', 'preview_passport_photo']
    fieldsets = [
        ('Student Bio Data', {
            'fields': [
                'preview_passport_photo', 'passport_photo', 'first_name', 'middle_name',
                'last_name', 'date_of_birth', 'gender',
                'religion', 'nationality'
            ]
        }),
        ('Contact and Address Details', {
            'fields': [
                'birth_district', 'subcounty', 'parish',
                'village', 'phone', 'email'
            ]
        }),
        ('Parents Information', {
            'fields': [
                'father_name', 'father_phone',
                'mother_name', 'mother_phone'
            ]
        }),
        ('Sponsor Information', {
            'fields': ['sponsor_name']
        }),
        ('Previous School Information', {
            'fields': ['former_school', 'former_school_district']
        }),
        ('Academic Information', {
            'fields': ['course', 'application', 'admission_number', 'year_of_admission', 'reporting', 'NSIN', 'enrollment_status']
        }),
    ]
    
    inlines = [DocumentInline, AdmissionFeeInline]
    search_fields = ['first_name', 'last_name', 'admission_number']
    list_filter = ['course', 'year_of_admission', 'enrollment_status']
    readonly_fields = ['admission_number', 'preview_passport_photo']

    def student_actions(self, obj):
        buttons = []
        # Enroll button - opens popup
        buttons.append(format_html(
            '<a href="#" onclick="openEnrollModal(event, \'{}\')" class="button" style="background-color:#007bff;margin-right:5px;">Enroll</a>',
            reverse('admin:enroll_student', args=[obj.id])
        ))
        # Print button
        buttons.append(format_html(
            '<a href="{}" target="_blank" class="button" style="background-color:#28a745;margin-right:5px;">Print</a>',
            reverse('student_admission_form', args=[obj.id])
        ))
        # Download button
        buttons.append(format_html(
            '<a href="{}" target="_blank" class="button" style="background-color:#17a2b8;margin-right:5px;">Download</a>',
            reverse('admission_letter', args=[obj.id])
        ))
        # View button
        buttons.append(format_html(
            '<a href="{}" class="button" style="background-color:#6c757d;">View</a>',
            reverse('admin:admissions_student_change', args=[obj.id])
        ))
        return format_html(' '.join(buttons))
    student_actions.short_description = 'Actions'

    def get_intake(self, obj):
        if obj.application and obj.application.intake:
            return obj.application.intake
        return '-'
    get_intake.short_description = 'Intake'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:student_id>/enroll/', self.admin_site.admin_view(self.enroll_student_view), name='enroll_student'),
            path('<int:student_id>/enroll/submit/', self.admin_site.admin_view(self.enroll_student_submit), name='enroll_student_submit'),
        ]
        return custom_urls + urls

    def enroll_student_view(self, request, student_id):
        from django.shortcuts import get_object_or_404
        student = get_object_or_404(Student, id=student_id)
        
        context = {
            **self.admin_site.each_context(request),
            'student': student,
            'opts': self.model._meta,
            'title': f'Enroll {student.first_name} {student.last_name}',
            'study_years': StudyYear.objects.all(),
            'semesters': semester.objects.all(),
        }
        return render(request, 'admin/admissions/student/enroll.html', context)

    def enroll_student_submit(self, request, student_id):
        from django.shortcuts import get_object_or_404
        from academics.models import Enrollment, Student as AcademicsStudent
        admissions_student = get_object_or_404(Student, id=student_id)
        
        study_year_id = request.POST.get('study_year')
        semester_id = request.POST.get('semester')
        
        if not study_year_id or not semester_id:
            messages.error(request, 'Please select both study year and semester.')
            return redirect('admin:enroll_student', student_id)
        
        try:
            study_year = StudyYear.objects.get(id=study_year_id)
            sem = semester.objects.get(id=semester_id)
        except (StudyYear.DoesNotExist, semester.DoesNotExist):
            messages.error(request, 'Invalid study year or semester selected.')
            return redirect('admin:enroll_student', student_id)
        
        # Check if academics student already exists
        try:
            academics_student = AcademicsStudent.objects.get(admission=admissions_student)
            # Update intake if not set
            if not academics_student.intake and admissions_student.application and admissions_student.application.intake:
                academics_student.intake = admissions_student.application.intake
                academics_student.save()
        except AcademicsStudent.DoesNotExist:
            # Create academics student record
            academics_student = AcademicsStudent.objects.create(
                admission=admissions_student,
                reg_number=admissions_student.admission_number,
                intake=admissions_student.application.intake if admissions_student.application and admissions_student.application.intake else None
            )
        
        # Create enrollment record
        Enrollment.objects.create(
            student=academics_student,
            study_year=study_year,
            semester=sem
        )
        
        # Update student enrollment status
        admissions_student.enrollment_status = 'ENROLLED'
        admissions_student.save()
        
        context = {
            'success': True,
            'message': f'{admissions_student.first_name} {admissions_student.last_name} has been enrolled successfully.'
        }
        return render(request, 'admin/admissions/student/enroll_success.html', context)

    def preview_passport_photo(self, obj):
        if obj.passport_photo:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.passport_photo.url)
        return "No photo uploaded"

    preview_passport_photo.short_description = "Passport Photo Preview"

    def print_admission_letter(self, obj):
        url = reverse('admission_letter', args=[obj.id])
        return format_html('<a href="{}" target="_blank">Download Admission Letter</a>', url)

    print_admission_letter.short_description = 'Download Admission Letter'

    def enrollment_status_badge(self, obj):
        colors = {
            'ENROLLED': '#28a745',
            'PENDING': '#ffc107',
            'DEFERRED': '#6c757d',
            'COMPLETED': '#007bff',
            'WITHDRAWN': '#dc3545',
        }
        color = colors.get(obj.enrollment_status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:#fff; padding:2px 8px; border-radius:3px; font-size:0.8em;">{}</span>',
            color, obj.get_enrollment_status_display()
        )

    enrollment_status_badge.short_description = 'Enrollment Status'
    enrollment_status_badge.admin_order_field = 'enrollment_status'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        study_years = StudyYear.objects.all()
        semesters = semester.objects.all()
        extra_context['study_years'] = study_years
        extra_context['semesters'] = semesters
        response = super().changelist_view(request, extra_context=extra_context)
        return response

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'student', 'uploaded_at']
    search_fields = ['name', 'student__first_name', 'student__last_name']
