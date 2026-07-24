from django.contrib import admin
from .models import CourseUnit, AcademicYear, StudyYear, Student, Enrollment, semester, Marks, Course, Intake
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.urls import path
from django.db.models import Count
from django.shortcuts import render, redirect
from finance.models import PaymentType, CourseFee


@admin.register(Intake)
class IntakeAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_year', 'start_date', 'end_date', 'status', 'student_count', 'view_students_link']
    list_filter = ['status', 'academic_year']
    search_fields = ['name', 'description']
    change_form_template = 'admin/academics/intake_change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:intake_id>/students/', self.admin_site.admin_view(self.view_intake_students), name='academics_intake_students'),
        ]
        return custom_urls + urls

    def student_count(self, obj):
        count = obj.students.count()
        return format_html('<span style="font-weight:bold;">{}</span>', count)
    student_count.short_description = 'Students'

    def view_students_link(self, obj):
        url = reverse('admin:academics_intake_students', args=[obj.id])
        return format_html('<a href="#" onclick="openIntakeStudentsModal(event, \'{}\')" class="button">View Students</a>', url)
    view_students_link.short_description = 'Actions'

    def view_intake_students(self, request, intake_id):
        intake = self.get_object(request, intake_id)
        if intake is None:
            self.message_user(request, 'Intake not found.', level='error')
            return redirect('admin:academics_intake_changelist')
        
        students = intake.students.select_related('admission').prefetch_related('enrollment_set__study_year', 'enrollment_set__semester').all()
        
        context = {
            **self.admin_site.each_context(request),
            'intake': intake,
            'students': students,
            'opts': self.model._meta,
            'title': f'Students for {intake.name}',
            'has_change_permission': self.has_change_permission(request, intake),
        }
        return render(request, 'admin/academics/intake_students.html', context)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current']
    search_fields = ['name']
    date_hierarchy = 'start_date'


@admin.register(StudyYear)
class StudyYearAdmin(admin.ModelAdmin):
    list_display = ['year']
    search_fields = ['year']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'level', 'department', 'duration', 'view_details']
    search_fields = ['name', 'short_name']
    list_filter = ['level', 'department']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/detail/', self.admin_site.admin_view(self.course_detail_view), name='course_detail'),
        ]
        return custom_urls + urls

    def view_details(self, obj):
        url = reverse('admin:course_detail', args=[obj.id])
        return format_html(
            '<a href="{}" class="button course-detail-link" data-title="Course Details - {}">View Details</a>',
            url,
            obj
        )
    view_details.short_description = 'Details'

    def course_detail_view(self, request, object_id):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(self.model, pk=object_id)

        is_popup = request.GET.get('_popup') == '1'

        # Get related data
        student_count = Student.objects.filter(admission__course=obj).count()

        # Get course units grouped by semester
        course_units = CourseUnit.objects.filter(courses=obj).select_related('tutor', 'year', 'semester').order_by('semester__semester', 'code')
        units_by_semester = {}
        for unit in course_units:
            sem_name = unit.semester.semester if unit.semester else 'Unassigned'
            if sem_name not in units_by_semester:
                units_by_semester[sem_name] = []
            units_by_semester[sem_name].append(unit)

        # Get enrolled students with their enrollment details
        enrollments = Enrollment.objects.filter(
            student__admission__course=obj
        ).select_related('student', 'study_year', 'semester').order_by('student__admission__admission_number')

        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            students_data.append({
                'nsin': student.admission.NSIN,
                'reg_number': student.reg_number,
                'name': f"{student.admission.first_name} {student.admission.last_name}",
                'year_of_study': enrollment.study_year.year if enrollment.study_year else 'N/A',
                'semester': enrollment.semester.semester if enrollment.semester else 'N/A',
                'status': student.admission.get_enrollment_status_display()
            })

        # Get payment types attached to this course
        payment_types = PaymentType.objects.filter(courses=obj).order_by('name')

        context = {
            **self.admin_site.each_context(request),
            'original': obj,
            'title': f'Course Details - {obj}',
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request, obj),
            'is_popup': is_popup,
            'student_count': student_count,
            'units_by_semester': units_by_semester,
            'total_units': course_units.count(),
            'students_data': students_data,
            'payment_types': payment_types,
        }
        return render(request, 'admin/admissions/course/course_detail.html', context)

    class Media:
        js = ('admissions/js/course_popup.js',)

@admin.register(CourseUnit)
class CourseUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'tutor', 'year', 'semester')
    search_fields = ('name', 'code', 'courses__name', 'departments__name', 'tutor__first_name', 'tutor__last_name')
    list_filter = ('year', 'semester', 'tutor', 'departments', 'courses')
    filter_horizontal = ('departments', 'courses')

# Admin for Semester
@admin.register(semester)  # Ensure class name is correctly capitalized (Semester instead of semester)
class semesterAdmin(admin.ModelAdmin):  # Corrected the class name for consistency
    list_display = ('semester',)
    search_fields = ('semester',)
    list_filter = ('semester',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('display_id', 'first_name', 'last_name', 'gender', 'course', 'intake', 'study_year', 'semester', 'phone', 'email')
    list_display_links = None
    search_fields = ('admission__first_name', 'admission__last_name', 'admission__admission_number', 'reg_number', 'admission__NSIN')
    list_filter = ('admission__course', 'intake', 'admission__gender')
    change_list_template = 'admin/academics/student/change_list.html'
    fields = ('admission', 'intake', 'reg_number')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('admission').prefetch_related('enrollment_set__study_year', 'enrollment_set__semester')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['study_years'] = StudyYear.objects.all()
        extra_context['semesters'] = semester.objects.all()
        return super().changelist_view(request, extra_context=extra_context)

    def display_id(self, obj):
        url = reverse('student_detail', args=[obj.id]) + '?_modal=1'
        return format_html(
            '<a href="{}" class="student-detail-link" data-student-id="{}" target="_blank">{}</a>',
            url, obj.id, obj.display_id
        )

    def first_name(self, obj):
        return obj.admission.first_name

    def last_name(self, obj):
        return obj.admission.last_name

    def phone(self, obj):
        return obj.admission.phone

    def email(self, obj):
        return obj.admission.email

    def study_year(self, obj):
        enrollment = obj.enrollment_set.last()
        if enrollment and enrollment.study_year:
            return enrollment.study_year.year
        return 'N/A'
    study_year.short_description = 'Study Year'

    def semester(self, obj):
        enrollment = obj.enrollment_set.last()
        if enrollment and enrollment.semester:
            return enrollment.semester.semester
        return 'N/A'
    semester.short_description = 'Semester'

    def gender(self, obj):
        return obj.admission.gender

    def course(self, obj):
        return obj.admission.course

    display_id.short_description = 'NSIN / Reg. Number'
    first_name.short_description = 'First Name'
    last_name.short_description = 'Last Name'
    gender.short_description = 'Gender'
    phone.short_description = 'Phone'
    email.short_description = 'Email'
    course.short_description = 'Course'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('preview_passport_photo', 'student', 'study_year', 'semester', 'student_phone', 'student_email')
    search_fields = ('student__admission__first_name', 'student__admission__last_name', 'student__admission__admission_number', 'study_year__year')
    list_filter = ('study_year', 'semester')

    def preview_passport_photo(self, obj):
        if obj.student.passport_photo:  # Accessing passport photo from the related Student model
            return format_html('<img src="{}" style="width: 50px; height: auto;" />', obj.student.passport_photo.url)
        return "No photo uploaded"

    preview_passport_photo.short_description = "Passport Photo Preview"

    def student_phone(self, obj):
        return obj.student.phone  # Accessing phone from the related Student model

    student_phone.short_description = "Phone"  # Custom column name for the phone field

    def student_email(self, obj):
        return obj.student.email  # Accessing email from the related Student model

    student_email.short_description = "email"  # Custom column name for the email field

@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'course_unit', 'test_marks', 'final_marks', 'total_marks')
    search_fields = ('enrollment__student__first_name', 'enrollment__student__last_name', 'course_unit__name')
    change_list_template = 'admin/academics/marks/change_list.html'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('bulk-marks/', self.admin_site.admin_view(self.bulk_marks_view), name='bulk_marks'),
        ]
        return custom_urls + urls

    def bulk_marks_view(self, request):
        from django.shortcuts import get_object_or_404
        from django.http import JsonResponse
        from .models import StudyYear, semester, CourseUnit, Enrollment, Marks

        if request.method == 'POST':
            study_year_id = request.POST.get('study_year')
            semester_id = request.POST.get('semester')
            course_unit_id = request.POST.get('course_unit')

            if not study_year_id or not semester_id or not course_unit_id:
                return JsonResponse({'success': False, 'error': 'Study year, semester, and course unit are required'})

            study_year = get_object_or_404(StudyYear, id=study_year_id)
            semester_obj = get_object_or_404(semester, id=semester_id)
            course_unit = get_object_or_404(CourseUnit, id=course_unit_id)

            enrollments = Enrollment.objects.filter(
                study_year=study_year,
                semester=semester_obj
            ).select_related('student')

            saved_count = 0
            updated_count = 0

            for enrollment in enrollments:
                test_key = f'test_{enrollment.id}_{course_unit.id}'
                final_key = f'final_{enrollment.id}_{course_unit.id}'
                test_marks = request.POST.get(test_key)
                final_marks = request.POST.get(final_key)

                if test_marks or final_marks:
                    existing_mark = Marks.objects.filter(
                        enrollment=enrollment,
                        course_unit=course_unit
                    ).first()

                    if existing_mark:
                        existing_mark.test_marks = float(test_marks) if test_marks else None
                        existing_mark.final_marks = float(final_marks) if final_marks else None
                        existing_mark.save()
                        updated_count += 1
                    else:
                        Marks.objects.create(
                            enrollment=enrollment,
                            course_unit=course_unit,
                            test_marks=float(test_marks) if test_marks else None,
                            final_marks=float(final_marks) if final_marks else None
                        )
                        saved_count += 1

            return JsonResponse({
                'success': True,
                'saved_count': saved_count,
                'updated_count': updated_count,
            })

        # GET: return JSON data for AJAX modal
        study_years = [{'id': sy.id, 'year': sy.year} for sy in StudyYear.objects.all()]
        semesters = [{'id': sem.id, 'semester': sem.semester} for sem in semester.objects.all()]
        course_units = [{'id': cu.id, 'code': cu.code, 'name': cu.name} for cu in CourseUnit.objects.all().order_by('code')]

        students_data = []
        selected_year = request.GET.get('study_year')
        selected_semester = request.GET.get('semester')
        selected_course_unit = request.GET.get('course_unit')

        if selected_year and selected_semester and selected_course_unit:
            study_year = StudyYear.objects.filter(id=selected_year).first()
            semester_obj = semester.objects.filter(id=selected_semester).first()
            course_unit = CourseUnit.objects.filter(id=selected_course_unit).first()

            if study_year and semester_obj and course_unit:
                enrollments = Enrollment.objects.filter(
                    study_year=study_year,
                    semester=semester_obj
                ).select_related('student', 'student__admission')

                for enrollment in enrollments:
                    student = enrollment.student
                    existing_mark = Marks.objects.filter(
                        enrollment=enrollment,
                        course_unit=course_unit
                    ).first()

                    students_data.append({
                        'enrollment_id': enrollment.id,
                        'course_unit_id': course_unit.id,
                        'student_name': f"{student.admission.first_name} {student.admission.last_name}",
                        'student_id': student.display_id,
                        'test_marks': existing_mark.test_marks if existing_mark else None,
                        'final_marks': existing_mark.final_marks if existing_mark else None,
                        'total_marks': existing_mark.total_marks() if existing_mark else None,
                    })

        return JsonResponse({
            'study_years': study_years,
            'semesters': semesters,
            'course_units': course_units,
            'students_data': students_data,
        })