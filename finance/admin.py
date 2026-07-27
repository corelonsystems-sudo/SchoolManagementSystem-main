from django.contrib import admin
from django.shortcuts import render
from .models import Payment, Ledger, CourseFee
from academics.models import Enrollment, Student
from datetime import datetime
from django.utils.html import format_html
from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa
from import_export.admin import ExportMixin, ImportMixin
from decimal import Decimal, InvalidOperation
from django.conf import settings
from urllib.parse import urlparse, unquote
import os
from django import forms


def _pdf_link_callback(uri, rel):
    parsed = urlparse(uri)
    path = unquote(parsed.path or '')

    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    static_url = getattr(settings, 'STATIC_URL', '/static/')

    if media_url and path.startswith(media_url):
        return os.path.join(str(settings.MEDIA_ROOT), path[len(media_url):].lstrip('/'))
    if static_url and path.startswith(static_url):
        # Prefer STATIC_ROOT if collectstatic is used; fallback to BASE_DIR/static
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root:
            return os.path.join(str(static_root), path[len(static_url):].lstrip('/'))
        return os.path.join(str(settings.BASE_DIR), 'static', path[len(static_url):].lstrip('/'))

    return uri


def _render_pdf(template_name, context):
    template = get_template(template_name)
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.CreatePDF(
        src=html,
        dest=result,
        encoding='UTF-8',
        link_callback=_pdf_link_callback,
    )
    if pdf.err:
        return None
    return result.getvalue()


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('get_student_name', 'get_student_course', 'get_student_year_semester', 'payment_type', 'amount', 'date', 'receipt_pdf_button')
    search_fields = ('enrollment__student__admission__first_name', 'enrollment__student__admission__last_name', 'payment_type')
    list_filter = ('payment_type', 'date')
    readonly_fields = ('ledger_view', 'form_data_view', 'payment_history_view')

    fieldsets = [
        ('Form', {
            'classes': ('collapse',),
            'fields': ('enrollment', 'payment_type', 'amount',),
        }),
        ('Student General Ledger', {
            'classes': ('collapse',),
            'fields': ('ledger_view',),
        }),
        ('Student Form Data', {
            'classes': ('collapse',),
            'fields': ('form_data_view',),
        }),
        ('Payment History', {
            'classes': ('collapse',),
            'fields': ('payment_history_view',),
        }),
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('enrollment__student', 'enrollment__study_year', 'enrollment__semester')
        return queryset

    def get_student_name(self, obj):
        if obj.enrollment and obj.enrollment.student:
            return f"{obj.enrollment.student.first_name} {obj.enrollment.student.last_name}"
        return "No student assigned"

    get_student_name.short_description = 'Student Name'

    def get_student_course(self, obj):
        if obj.enrollment and obj.enrollment.student and obj.enrollment.student.course:
            return obj.enrollment.student.course.name
        return "No course assigned"

    get_student_course.short_description = 'Course'

    def get_student_year_semester(self, obj):
        if obj.enrollment and obj.enrollment.study_year and obj.enrollment.semester:
            return f"{obj.enrollment.study_year.year} - {obj.enrollment.semester.semester}"
        return "Year/Semester not assigned"

    get_student_year_semester.short_description = 'Year & Semester'

    def ledger_view(self, obj):
        if not obj or not obj.enrollment or not obj.enrollment.student:
            return "No ledger available."

        student = obj.enrollment.student
        full_name = f"{student.first_name} {student.last_name}"
        course = student.course.name if student.course else "No course assigned"
        image_url = student.passport_photo.url if student.passport_photo else None
        payments = Payment.objects.filter(enrollment__student=student).order_by('date')
        total_paid = Decimal(0)  # Initialize total_paid as Decimal
        ledger = Ledger.objects.filter(student=student).first()
        required_amount = ledger.required_amount if ledger else Decimal(1000000.0)  # Convert to Decimal

        grouped_payments = {}
        for payment in payments:
            year_val = payment.enrollment.study_year.year if payment.enrollment.study_year else 'N/A'
            sem_val = payment.enrollment.semester.semester if payment.enrollment.semester else 'N/A'
            year_semester = f"{year_val} - {sem_val}"
            if year_semester not in grouped_payments:
                grouped_payments[year_semester] = []
            grouped_payments[year_semester].append(payment)

        ledger = """
            <div style="font-family: Arial, sans-serif; border: 1px solid #ddd; padding: 20px; width: 1200px; position:relative;">
                <div style="text-align: center;">
                    <h2 style="color: #0056b3; margin-bottom: 5px; padding-left:30px; position:absolute; top:-22px; font-weight:3000; background:#ffffff;">Student Payment Ledger</h2>
                    <p style="margin: 0; font-size: 14px; color: #555;">Generated on: {}</p>
                </div>
                <div style="display: flex; margin-top: 20px;">
                    <div style="flex: 0 0 auto; margin-right: 20px;">
                        {}
                    </div>
                    <div style="flex: 1; display: flex; flex-direction: column; justify-content: center;">
                        <h4 style="margin: 0; font-size: 20px;">Student Details</h4>
                        <p style="margin: 0; font-size: 14px; color: #555;"><strong>Name:</strong> {}</p>
                        <p style="margin: 0; font-size: 14px; color: #555;"><strong>Course:</strong> {}</p>
                    </div>
                </div>
        """.format(
            datetime.now().strftime('%Y-%m-%d'),
            f'<img src="{image_url}" alt="{full_name}" style="max-height: 150px; max-width: 150px; margin-bottom: 10px; border-radius: 10px;">'
            if image_url else "",
            full_name,
            course,
        )

        for year_semester, payments_in_group in grouped_payments.items():
            ledger += f"""
                <h3 style="color: #333; margin-top: 20px;">{year_semester}</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Date of Payment</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Payment Type</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            group_total_paid = Decimal(0)
            for payment in payments_in_group:
                ledger += format_html(
                    """
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;">{}</td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{}</td>
                        </tr>
                    """,
                    payment.date.strftime('%Y-%m-%d'),
                    payment.payment_type,
                    f"{payment.amount:,.2f}",
                )
                group_total_paid += payment.amount
                total_paid += payment.amount

            # Now calculate the balance correctly
            balance = required_amount - total_paid

            ledger += format_html(
                """
                    </tbody>
                    <tfoot>
                        <tr>
                            <th colspan="2" style="border: 1px solid #ddd; padding: 8px; text-align: right;">Total Paid:</th>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{}</td>
                        </tr>
                        <tr>
                            <th colspan="2" style="border: 1px solid #ddd; padding: 8px; text-align: right;">Balance:</th>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: right; color: {}">{}</td>
                        </tr>
                    </tfoot>
                </table>
            """,
            f"{group_total_paid:,.2f}",
            "red" if balance > 0 else "green",
            f"{balance:,.2f}"
            )

        ledger += """
                <div style="text-align: center; margin-top: 20px;">
                    <p style="font-size: 14px; color: #888;">Thank you for your payment.</p>
                </div>
            </div>
        """

        return format_html(ledger)

    ledger_view.short_description = ""

    def form_data_view(self, obj):
        if not obj or not obj.enrollment or not obj.enrollment.student:
            return "No form data available."
        
        student = obj.enrollment.student
        return format_html(
            """
            <div style="margin-top: 10px;">
                <h4>Student Form Data:</h4>
                <p><strong>First Name:</strong> {}</p>
                <p><strong>Last Name:</strong> {}</p>
                <p><strong>Admission Number:</strong> {}</p>
            </div>
            """,
            student.first_name,
            student.last_name,
            student.admission_number
        )

    form_data_view.short_description = "Form Data"

    def payment_history_view(self, obj):
        if not obj or not obj.enrollment or not obj.enrollment.student:
            return "No payment history available."

        payments = Payment.objects.filter(enrollment__student=obj.enrollment.student).order_by('-date')
        history = """
            <table style="border: 1px solid #ddd; border-collapse: collapse; width: 100%; margin-top: 10px;">
                <thead>
                    <tr style="background-color: #f2f2f2; text-align: left;">
                        <th style="border: 1px solid #ddd; padding: 8px;">Date</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Amount</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Payment Type</th>
                    </tr>
                </thead>
                <tbody>
        """

        for payment in payments:
            history += format_html(
                """
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">{}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{}</td>
                    </tr>
                """,
                payment.date.strftime('%Y-%m-%d'),
                f"{payment.amount:,.2f}",
                payment.payment_type,
            )

        history += """
                </tbody>
            </table>
        """

        return format_html(history)

    def receipt_pdf_button(self, obj):
        return format_html(
            '<a href="{}" class="button" target="_blank">Receipt PDF</a>',
            reverse('admin:payment_receipt_pdf', args=[obj.id])
        )

    receipt_pdf_button.short_description = 'Receipt'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'receipt_pdf/<int:payment_id>/',
                self.admin_site.admin_view(self.receipt_pdf),
                name='payment_receipt_pdf',
            ),
        ]
        return custom_urls + urls

    def receipt_pdf(self, request, payment_id):
        payment = Payment.objects.select_related(
            'enrollment__student',
            'enrollment__study_year',
            'enrollment__semester',
            'payment_type',
            'ledger',
        ).get(id=payment_id)

        student = payment.enrollment.student
        context = {
            'receipt_number': f"RCT-{payment.id:06d}",
            'payment': payment,
            'student': student,
            'ledger': payment.ledger,
            'study_year': payment.enrollment.study_year,
            'semester': payment.enrollment.semester,
        }
        pdf = _render_pdf('admin/finance/payment/receipt_pdf.html', context)
        if not pdf:
            return HttpResponse('Failed to generate receipt PDF.', status=500)

        filename = f"receipt_{payment.id}.pdf"
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    payment_history_view.short_description = "Payment History"


from django.utils.html import format_html
from django import forms
from django.contrib import admin
from .models import PaymentType, PaymentTypeBreakdown, Ledger, Payment, CourseFee, AdmissionFee
from academics.models import Enrollment, Student
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.db.models import Sum

@admin.register(PaymentType)
class PaymentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'default_amount', 'is_tuition')
    search_fields = ('name',)
    ordering = ('name',)
    list_filter = ('frequency', 'is_tuition')
    list_editable = ('frequency', 'default_amount', 'is_tuition')


# @admin.register(AdmissionFee)
# class AdmissionFeeAdmin(admin.ModelAdmin):
#     list_display = ('admission', 'payment_type', 'custom_amount', 'is_active')
#     search_fields = ('admission__first_name', 'admission__last_name', 'admission__admission_number', 'payment_type__name')
#     list_filter = ('payment_type', 'is_active')


@admin.register(CourseFee)
class CourseFeeAdmin(admin.ModelAdmin):
    list_display = ('course', 'study_year', 'semester', 'tuition_fee', 'view_details')
    search_fields = ('course__name', 'study_year__year', 'semester__semester')
    list_filter = ('course', 'study_year', 'semester')

    class Media:
        js = ('finance/js/course_fee_popup.js',)

    def view_details(self, obj):
        url = reverse('admin:course_fee_detail', args=[obj.id])
        return format_html(
            '<a href="{}" class="button course-fee-detail-link" data-title="Course Fee Details - {}">View Details</a>',
            url,
            obj
        )
    view_details.short_description = 'Details'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'course_fee/<int:object_id>/detail/',
                self.admin_site.admin_view(self.course_fee_detail_view),
                name='course_fee_detail',
            ),
        ]
        return custom_urls + urls

    def course_fee_detail_view(self, request, object_id):
        from django.shortcuts import get_object_or_404
        obj = get_object_or_404(self.model, pk=object_id)
        
        is_popup = request.GET.get('_popup') == '1'
        
        # Get payment data
        from academics.models import Enrollment
        payments = Payment.objects.filter(
            enrollment__student__admission__course=obj.course,
            enrollment__study_year=obj.study_year,
            enrollment__semester=obj.semester
        ).select_related('enrollment__student', 'payment_type').order_by('-date')[:10]
        
        # Get enrolled students with payment status
        enrollments = Enrollment.objects.filter(
            student__admission__course=obj.course,
            study_year=obj.study_year,
            semester=obj.semester
        ).select_related('student')
        
        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            student_payments = Payment.objects.filter(
                enrollment=enrollment,
                payment_type__is_tuition=True
            )
            total_paid = sum(p.amount for p in student_payments)
            balance = obj.tuition_fee - total_paid
            students_data.append({
                'student': student,
                'admission_number': student.admission_number,
                'name': f"{student.first_name} {student.last_name}",
                'total_paid': total_paid,
                'balance': balance,
                'status': 'Fully Paid' if balance <= 0 else 'Partially Paid' if total_paid > 0 else 'Not Paid'
            })
        
        # Calculate statistics
        total_students = enrollments.count()
        total_collected = sum(p.amount for p in payments)
        collection_rate = (total_collected / (obj.tuition_fee * total_students) * 100) if total_students > 0 and obj.tuition_fee > 0 else 0
        
        context = {
            **self.admin_site.each_context(request),
            'original': obj,
            'title': f'Course Fee Details - {obj}',
            'fee_info_section': self.fee_info_section(obj),
            'fee_payments_section': self.fee_payments_section(obj),
            'fee_statistics_section': self.fee_statistics_section(obj),
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request, obj),
            'is_popup': is_popup,
            'payments': payments,
            'students_data': students_data,
            'total_students': total_students,
            'total_collected': total_collected,
            'collection_rate': collection_rate,
        }
        return render(request, 'admin/finance/course_fee/change_form.html', context)

    def fee_info_section(self, obj):
        if not obj.pk:
            return "Save this course fee first to view details."
        
        return format_html(
            '''
            <div class="fee-section">
                <h3>Fee Information</h3>
                <div class="fee-info-grid">
                    <div class="fee-info-item">
                        <label>Course:</label>
                        <span>{}</span>
                    </div>
                    <div class="fee-info-item">
                        <label>Academic Year:</label>
                        <span>{}</span>
                    </div>
                    <div class="fee-info-item">
                        <label>Semester:</label>
                        <span>{}</span>
                    </div>
                    <div class="fee-info-item">
                        <label>Tuition Fee:</label>
                        <span class="fee-amount">{}</span>
                    </div>
                </div>
            </div>
            ''',
            obj.course.name if obj.course else 'N/A',
            obj.study_year.year if obj.study_year else 'N/A',
            obj.semester.semester if obj.semester else 'N/A',
            f"{obj.tuition_fee:,.2f}"
        )
    fee_info_section.short_description = ''

    def fee_payments_section(self, obj):
        if not obj.pk:
            return ""
        
        from academics.models import Enrollment
        from .models import Payment
        
        enrollments = Enrollment.objects.filter(
            student__admission__course=obj.course,
            study_year=obj.study_year,
            semester=obj.semester
        )
        
        total_students = enrollments.count()
        total_paid = Decimal('0.00')
        payment_count = 0
        
        for enrollment in enrollments:
            payments = Payment.objects.filter(
                enrollment=enrollment,
                payment_type__is_tuition=True
            )
            payment_count += payments.count()
            total_paid += sum(p.amount for p in payments)
        
        return format_html(
            '''
            <div class="fee-section">
                <h3>Fee Payments</h3>
                <div class="fee-stats-grid">
                    <div class="fee-stat-card">
                        <div class="stat-label">Total Students</div>
                        <div class="stat-value">{}</div>
                    </div>
                    <div class="fee-stat-card">
                        <div class="stat-label">Total Payments</div>
                        <div class="stat-value">{}</div>
                    </div>
                    <div class="fee-stat-card">
                        <div class="stat-label">Total Collected</div>
                        <div class="stat-value">{}</div>
                    </div>
                    <div class="fee-stat-card">
                        <div class="stat-label">Expected Total</div>
                        <div class="stat-value">{}</div>
                    </div>
                </div>
            </div>
            ''',
            total_students,
            payment_count,
            f"{total_paid:,.2f}",
            f"{obj.tuition_fee * total_students:,.2f}"
        )
    fee_payments_section.short_description = ''

    def fee_statistics_section(self, obj):
        if not obj.pk:
            return ""
        
        from academics.models import Enrollment
        from .models import Payment
        
        enrollments = Enrollment.objects.filter(
            student__admission__course=obj.course,
            study_year=obj.study_year,
            semester=obj.semester
        )
        
        total_students = enrollments.count()
        if total_students == 0:
            collection_rate = 0
        else:
            total_paid = Decimal('0.00')
            for enrollment in enrollments:
                payments = Payment.objects.filter(
                    enrollment=enrollment,
                    payment_type__is_tuition=True
                )
                total_paid += sum(p.amount for p in payments)
            expected_total = obj.tuition_fee * total_students
            collection_rate = (total_paid / expected_total * 100) if expected_total > 0 else 0
        
        # Count fully paid students
        fully_paid = 0
        partially_paid = 0
        not_paid = 0
        
        for enrollment in enrollments:
            payments = Payment.objects.filter(
                enrollment=enrollment,
                payment_type__is_tuition=True
            )
            paid_amount = sum(p.amount for p in payments)
            if paid_amount >= obj.tuition_fee:
                fully_paid += 1
            elif paid_amount > 0:
                partially_paid += 1
            else:
                not_paid += 1
        
        return format_html(
            '''
            <div class="fee-section">
                <h3>Fee Statistics</h3>
                <div class="fee-stats-grid">
                    <div class="fee-stat-card">
                        <div class="stat-label">Collection Rate</div>
                        <div class="stat-value">{}%</div>
                    </div>
                    <div class="fee-stat-card">
                        <div class="stat-label">Fully Paid</div>
                        <div class="stat-value success">{}</div>
                    </div>
                    <div class="fee-stat-card">
                        <div class="stat-label">Partially Paid</div>
                        <div class="stat-value warning">{}</div>
                    </div>
                    <div class="fee-stat-card">
                        <div class="stat-label">Not Paid</div>
                        <div class="stat-value danger">{}</div>
                    </div>
                </div>
            </div>
            ''',
            f"{collection_rate:.1f}",
            fully_paid,
            partially_paid,
            not_paid
        )
    fee_statistics_section.short_description = ''

# class PaymentTypeBreakdownAdminForm(forms.ModelForm):
#     class Meta:
#         model = PaymentTypeBreakdown
#         fields = ['ledger', 'payment_type', 'amount']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if not self.instance.pk:
#             self.fields['ledger'].queryset = Ledger.objects.all()

# @admin.register(PaymentTypeBreakdown)
# class PaymentTypeBreakdownAdmin(admin.ModelAdmin):
#     form = PaymentTypeBreakdownAdminForm
#     list_display = ('ledger', 'payment_type', 'amount')
#     search_fields = ('ledger__student__admission__first_name', 'ledger__student__admission__last_name', 'payment_type__name')
#     list_filter = ('ledger', 'payment_type', 'ledger__academic_year', 'ledger__semester')

#     def save_model(self, request, obj, form, change):
#         # Ensure the PaymentTypeBreakdown is correctly linked to the Ledger
#         if not obj.ledger:
#             raise ValueError("Ledger must be associated with this payment breakdown.")

#         # Recalculate the required_amount for the Ledger based on all breakdowns
#         obj.ledger.required_amount = obj.ledger.payment_type_breakdowns.aggregate(
#             total=Sum('amount'))['total'] or Decimal('0.00')
#         obj.ledger.save()

#         # Save the breakdown record
#         super().save_model(request, obj, form, change)

#         # Recalculate the balance after saving the breakdown
#         self.update_balance(obj.ledger)

    def update_balance(self, ledger):
        # Calculate the total paid from payments
        total_paid = Payment.objects.filter(
            enrollment__student=ledger.student,
            enrollment__study_year=ledger.study_year,
            enrollment__semester=ledger.semester
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        # Update the balance
        balance = ledger.required_amount - total_paid
        ledger.balance = balance
        ledger.save()

    def get_queryset(self, request):
        return super().get_queryset(request)

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

from django import forms
from django.contrib import admin
from django.utils.html import format_html
from decimal import Decimal, InvalidOperation
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Ledger, Payment
from academics.models import Enrollment, Student
from datetime import datetime
from django.http import HttpResponse


class PaymentTypeBreakdownInline(admin.TabularInline):
    """
    Editable fee lines on a student's ledger. Staff adjust `amount` here to grant
    a bursary, waiver or any other individual favour; `standard_amount` shows what
    was originally generated on enrollment so the concession stays auditable.
    """
    model = PaymentTypeBreakdown
    extra = 0
    fields = ('payment_type', 'standard_amount_display', 'amount', 'adjustment_display', 'note')
    readonly_fields = ('standard_amount_display', 'adjustment_display')
    autocomplete_fields = ()
    verbose_name = 'Fee item'
    verbose_name_plural = 'Fee items (edit an amount to grant a discount or waiver)'

    def standard_amount_display(self, obj):
        if obj is None or obj.standard_amount is None:
            return '—'
        return "{:,.2f}".format(obj.standard_amount)

    standard_amount_display.short_description = 'Standard'

    def adjustment_display(self, obj):
        if obj is None or obj.pk is None:
            return '—'
        delta = obj.adjustment
        if not delta:
            return format_html('<span style="color:#64748b;">No change</span>')
        colour = '#15803d' if delta < 0 else '#b91c1c'
        label = 'Discount' if delta < 0 else 'Surcharge'
        return format_html(
            '<span style="color:{}; font-weight:600;">{} {:,.2f}</span>',
            colour, label, abs(delta),
        )

    adjustment_display.short_description = 'Adjustment'


class LedgerAdminForm(forms.ModelForm):
    class Meta:
        model = Ledger
        fields = ['student', 'study_year', 'semester']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        study_year = self.initial.get('study_year') or getattr(self.instance, 'study_year', None)
        semester = self.initial.get('semester') or getattr(self.instance, 'semester', None)

        if study_year and semester:
            self.fields['student'].queryset = Enrollment.objects.filter(
                study_year=study_year,
                semester=semester
            ).values_list('student', flat=True)
            self.fields['student'].queryset = Student.objects.filter(id__in=self.fields['student'].queryset)


@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    form = LedgerAdminForm
    inlines = [PaymentTypeBreakdownInline]
    list_display = ('student', 'ledger_number', 'study_year', 'semester', 'required_amount', 'total_paid_display', 'balance_display', 'generated_on', 'print_button')
    search_fields = ('student__admission__first_name', 'student__admission__last_name', 'ledger_number', 'study_year__year', 'semester__semester')
    list_filter = ('study_year', 'semester')
    # required_amount is the sum of the fee items below, so it is shown but not typed in.
    readonly_fields = ('ledger_details', 'total_paid', 'required_amount', 'balance', 'generated_on')

    fieldsets = [
        ('Ledger Details', {
            'classes': ('collapse', 'wide',),
            'fields': ('ledger_details',),
        }),
        ('Ledger Summary', {
            'classes': ('collapse',),
            'fields': ('student', 'study_year', 'semester', 'total_paid', 'required_amount', 'balance', 'generated_on'),
        }),
    ]

    def save_related(self, request, form, formsets, change):
        """
        Django saves the parent before its inlines, so recalculating totals in
        Ledger.save() alone would use the pre-edit fee lines. Re-save the ledger
        once the inline formsets have been committed.
        """
        super().save_related(request, form, formsets, change)
        form.instance.save()

    def total_paid_display(self, obj):
        payments = Payment.objects.filter(
            enrollment__student=obj.student,
            enrollment__study_year=obj.study_year,
            enrollment__semester=obj.semester
        )
        total_paid = sum(payment.amount for payment in payments)
        return format_html("{:,.2f}".format(total_paid))

    total_paid_display.short_description = 'Total Paid'

    def balance_display(self, obj):
        total_paid = Decimal(self.total_paid_display(obj).replace(",", ""))
        balance = obj.required_amount - total_paid
        return format_html(
            "<span style='color: {}; font-weight: bold;'>{}</span>".format(
                "green" if balance <= 0 else "red", "{:,.2f}".format(balance)
            )
        )

    balance_display.short_description = 'Balance'

    def ledger_details(self, obj):
        if not obj or not obj.student:
            return "No ledger details available."

        student = obj.student
        full_name = f"{student.first_name} {student.last_name}"
        course = student.course.name if student.course else "No course assigned"
        NSIN = student.NSIN if student.NSIN else "No NSIN assigned"
        image_url = student.passport_photo.url if student.passport_photo else None
        payments = Payment.objects.filter(
            enrollment__student=student,
            enrollment__study_year=obj.study_year,
            enrollment__semester=obj.semester
        ).order_by('date')

        total_paid = Decimal('0.00')

        # Aggregate payments per payment type
        payment_type_paid = {}
        for payment in payments:
            name = payment.payment_type.name
            payment_type_paid[name] = payment_type_paid.get(name, Decimal('0.00')) + payment.amount

        pay_url = reverse('admin:pay_ledger', args=[obj.id])
        pdf_url = reverse('admin:ledger_pdf', args=[obj.id])

        # Build the ledger HTML
        ledger_html = f"""
            <style>
                .ledger-page {{ font-family: Arial, sans-serif; color: #334155; }}
                .ledger-actions {{ display: flex; justify-content: flex-end; gap: 8px; margin: 0 0 16px; }}
                .ledger-actions button, .ledger-actions a {{ border: 0; border-radius: 3px; color: #fff; cursor: pointer; font-size: 12px; font-weight: 600; padding: 10px 16px; text-decoration: none; }}
                .ledger-action-print {{ background: #0b5cad; }}
                .ledger-action-pdf {{ background: #111827; }}
                .ledger-action-pay {{ background: #16a34a; }}
                #ledger-printable-content {{ background: #fff; border: 1px solid #dbe3ec; box-sizing: border-box; padding: 20px; width: 100%; }}
                .ledger-heading {{ align-items: center; border-bottom: 1px solid #dbe3ec; display: flex; justify-content: space-between; padding-bottom: 14px; }}
                .ledger-heading h2 {{ color: #1d4f82; font-size: 18px; letter-spacing: .3px; margin: 0; text-transform: uppercase; }}
                .ledger-generated {{ color: #64748b; font-size: 11px; margin: 0; }}
                .ledger-student-grid {{ display: grid; gap: 18px; grid-template-columns: 132px minmax(0, 1fr); margin: 20px 0; }}
                .ledger-photo {{ align-items: center; background: #f1f5f9; border: 1px solid #dbe3ec; display: flex; height: 132px; justify-content: center; overflow: hidden; width: 132px; }}
                .ledger-photo img {{ height: 100%; object-fit: cover; width: 100%; }}
                .ledger-student-info h4 {{ border-bottom: 2px solid #1d4f82; color: #1d4f82; font-size: 14px; margin: 0 0 12px; padding-bottom: 7px; }}
                .ledger-info-grid {{ display: grid; gap: 8px 24px; grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                .ledger-info-item {{ font-size: 12px; margin: 0; }}
                .ledger-info-item strong {{ color: #64748b; display: inline-block; min-width: 70px; }}
                .ledger-period {{ background: #f8fafc; border: 1px solid #e2e8f0; color: #475569; font-size: 12px; margin: 0 0 16px; padding: 10px 12px; }}
                #ledger-breakdown-table {{ border-collapse: collapse; font-size: 12px; margin-top: 0; width: 100%; }}
                #ledger-breakdown-table th {{ background: #1d4f82; color: #fff; font-weight: 600; padding: 10px 12px; text-align: left; }}
                #ledger-breakdown-table th:not(:first-child), #ledger-breakdown-table td:not(:first-child) {{ text-align: right; }}
                #ledger-breakdown-table td {{ border-bottom: 1px solid #e2e8f0; padding: 10px 12px; }}
                #ledger-breakdown-table tbody tr:nth-child(even) {{ background: #f8fafc; }}
                #ledger-breakdown-table tfoot td {{ background: #f1f5f9; border-bottom: 0; font-weight: 600; padding: 10px 12px; }}
                .ledger-thank-you {{ color: #64748b; font-size: 12px; margin: 18px 0 0; text-align: center; }}
                @media (max-width: 700px) {{
                    .ledger-actions {{ justify-content: flex-start; flex-wrap: wrap; }}
                    .ledger-student-grid, .ledger-info-grid {{ grid-template-columns: 1fr; }}
                    .ledger-photo {{ height: 96px; width: 96px; }}
                    #ledger-breakdown-table {{ display: block; overflow-x: auto; white-space: nowrap; }}
                }}
                @media print {{
                    .ledger-actions {{ display: none; }}
                    #ledger-printable-content {{ border: 0; }}
                }}
            </style>
            <div class="ledger-page">
                <div class="ledger-actions">
                    <button type="button" class="ledger-action-print" onclick="window.print();">Print Ledger</button>
                    <a class="ledger-action-pdf" href="{pdf_url}" target="_blank">Download PDF</a>
                    <button type="button" class="ledger-action-pay" onclick="document.getElementById('ledger-pay-modal').style.display='block';">Pay</button>
                </div>
                <div id="ledger-printable-content">
                    <div class="ledger-heading">
                        <h2>Student Ledger</h2>
                        <p class="ledger-generated">Generated on: {datetime.now().strftime('%Y-%m-%d')}</p>
                    </div>
                    <div class="ledger-student-grid">
                        <div class="ledger-photo">
                            {'<img src="{}" alt="{}">'.format(image_url, full_name) if image_url else '<span>No photo</span>'}
                        </div>
                        <div class="ledger-student-info">
                            <h4>STUDENT DETAILS</h4>
                            <div class="ledger-info-grid">
                                <p class="ledger-info-item"><strong>Name:</strong> {full_name}</p>
                                <p class="ledger-info-item"><strong>Course:</strong> {course}</p>
                                <p class="ledger-info-item"><strong>NSIN:</strong> {NSIN}</p>
                                <p class="ledger-info-item"><strong>Ledger:</strong> {obj.ledger_number}</p>
                            </div>
                        </div>
                    </div>
                    <p class="ledger-period"><strong>Academic period:</strong> Study Year {obj.study_year.year if obj.study_year else 'N/A'} &nbsp;·&nbsp; Semester {obj.semester.semester}</p>
                    <table id="ledger-breakdown-table">
                        <thead>
                            <tr>
                                <th>Payment Type</th>
                                <th>Amount</th>
                                <th>Paid</th>
                                <th>Balance</th>
                            </tr>
                        </thead>
                        <tbody>
        """

        for breakdown in obj.payment_type_breakdowns.all():
            payment_type_name = breakdown.payment_type.name
            amount = breakdown.amount
            paid = payment_type_paid.get(payment_type_name, Decimal('0.00'))
            balance_per_payment_type = amount - paid
            ledger_html += format_html(
                """
                <tr data-payment-type-id="{}" data-amount="{}">
                    <td>{}</td>
                    <td>{}</td>
                    <td class="ledger-paid">{}</td>
                    <td class="ledger-balance" style="color: {}">{}</td>
                </tr>
                """,
                breakdown.payment_type_id,
                str(amount),
                payment_type_name,
                f"{amount:,.2f}",
                f"{paid:,.2f}",
                "green" if balance_per_payment_type <= 0 else "red",
                f"{balance_per_payment_type:,.2f}",
            )
        total_paid = sum(payment_type_paid.values(), Decimal('0.00'))
        balance = obj.required_amount - total_paid

        ledger_html += format_html(
            """
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="3">Total Paid:</td>
                            <td><span id="ledger-total-paid">{}</span></td>
                        </tr>
                        <tr>
                            <td colspan="3">Balance:</td>
                            <td id="ledger-overall-balance-cell" style="color: {}"><span id="ledger-overall-balance">{}</span></td>
                        </tr>
                    </tfoot>
                </table>
                <p class="ledger-thank-you">Thank you for your payment.</p>
            </div>
            """,
        f"{total_paid:,.2f}",
        "green" if balance <= 0 else "red",
        f"{balance:,.2f}",
        )

        # Payment modal
        modal_rows = []
        for breakdown in obj.payment_type_breakdowns.all():
            payment_type_name = breakdown.payment_type.name
            amount = breakdown.amount
            paid = payment_type_paid.get(payment_type_name, Decimal('0.00'))
            remaining = amount - paid
            if remaining <= 0:
                continue
            modal_rows.append(
                f"""
                <tr data-payment-type-id="{breakdown.payment_type_id}" data-amount="{amount}">
                    <td style="border-bottom: 1px solid #e2e8f0; padding: 10px 12px;">{payment_type_name}</td>
                    <td style="border-bottom: 1px solid #e2e8f0; padding: 10px 12px; text-align: right;">{amount:,.2f}</td>
                    <td class="modal-paid" style="border-bottom: 1px solid #e2e8f0; padding: 10px 12px; text-align: right;">{paid:,.2f}</td>
                    <td class="modal-balance" style="border-bottom: 1px solid #e2e8f0; padding: 10px 12px; text-align: right; color: #b91c1c; font-weight: 600;">{remaining:,.2f}</td>
                    <td style="border-bottom: 1px solid #e2e8f0; padding: 10px 12px;">
                        <input type="number" name="pay_amount_{breakdown.payment_type_id}" step="0.01" min="0" max="{remaining}" placeholder="Amount" style="width: 120px; padding: 6px 8px; border: 1px solid #d9e1ea; border-radius: 4px; font-size: 12px;">
                    </td>
                </tr>
                """
            )

        if not modal_rows:
            modal_rows.append('<tr><td colspan="5" style="padding: 12px; text-align: center;">No outstanding balances.</td></tr>')

        modal_html = f"""
        <div id="ledger-pay-modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
            <div style="background-color: #fff; margin: 8% auto; padding: 24px; border: 1px solid #dbe3ec; width: 90%; max-width: 800px; border-radius: 8px; box-shadow: 0 8px 30px rgba(0,0,0,0.15);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">
                    <h3 style="margin: 0; color: #1d4f82; font-size: 16px;">Record Payment</h3>
                    <button type="button" onclick="document.getElementById('ledger-pay-modal').style.display='none';" style="background: none; border: 0; font-size: 22px; cursor: pointer; color: #64748b;">&times;</button>
                </div>
                <div id="ledger-pay-form" data-action="{pay_url}">
                    <input type="hidden" id="ledger-pay-csrf" name="csrfmiddlewaretoken" value="">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 12px;">
                        <thead>
                            <tr style="background: #1d4f82; color: #fff;">
                                <th style="padding: 10px 12px; text-align: left;">Payment Type</th>
                                <th style="padding: 10px 12px; text-align: right;">Amount</th>
                                <th style="padding: 10px 12px; text-align: right;">Paid</th>
                                <th style="padding: 10px 12px; text-align: right;">Balance</th>
                                <th style="padding: 10px 12px;">Pay Now</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(modal_rows)}
                        </tbody>
                    </table>
                    <div id="ledger-pay-message" style="margin-bottom: 12px; font-weight: 500; font-size: 12px;"></div>
                    <div style="text-align: right;">
                        <button type="button" onclick="document.getElementById('ledger-pay-modal').style.display='none';" style="padding: 8px 16px; margin-right: 8px; cursor: pointer; border: 1px solid #d9e1ea; border-radius: 4px; background: #fff; color: #475569; font-size: 12px;">Cancel</button>
                        <button type="button" id="ledger-pay-submit" onclick="ledgerPaySubmit(this, event); return false;" style="padding: 8px 16px; background: #16a34a; color: #fff; border: 0; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;">Save Payment</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="ledger-confirm-modal" style="display: none; position: fixed; z-index: 1100; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.35);">
            <div style="background-color: #fff; margin: 8% auto; padding: 24px; border: 1px solid #dbe3ec; width: 90%; max-width: 650px; border-radius: 8px; box-shadow: 0 8px 30px rgba(0,0,0,0.15);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">
                    <h3 style="margin: 0; color: #1d4f82; font-size: 16px;">Payment Confirmation</h3>
                    <button type="button" onclick="document.getElementById('ledger-confirm-modal').style.display='none';" style="background: none; border: 0; font-size: 22px; cursor: pointer; color: #64748b;">&times;</button>
                </div>
                <div id="ledger-confirm-body"></div>
                <div style="text-align: right; margin-top: 16px;">
                    <button type="button" onclick="document.getElementById('ledger-confirm-modal').style.display='none';" style="padding: 8px 16px; cursor: pointer; border: 1px solid #d9e1ea; border-radius: 4px; background: #fff; color: #475569; font-size: 12px;">Close</button>
                </div>
            </div>
        </div>
        <script>
            window.ledgerPaySubmit = function(button, event) {{
                if (event) {{
                    event.preventDefault();
                    event.stopPropagation();
                }}
                var container = document.getElementById('ledger-pay-form');
                var messageDiv = document.getElementById('ledger-pay-message');
                if (!container) {{
                    alert('Payment container not found.');
                    return false;
                }}
                if (button) button.disabled = true;
                var formData = new FormData();
                var inputs = container.querySelectorAll('input[name]');
                inputs.forEach(function(input) {{
                    if (input.name !== 'csrfmiddlewaretoken' && (input.value === '' || input.value === null || typeof input.value === 'undefined')) {{
                        return;
                    }}
                    formData.append(input.name, input.value);
                }});
                var action = container.getAttribute('data-action');
                fetch(action, {{
                    method: 'POST',
                    body: formData,
                    headers: {{'X-Requested-With': 'XMLHttpRequest'}},
                    credentials: 'same-origin'
                }})
                .then(function(response) {{
                    if (!response.ok) {{
                        throw new Error('Server returned ' + response.status);
                    }}
                    return response.json();
                }})
                .then(function(data) {{
                    messageDiv.textContent = data.message;
                    messageDiv.style.color = data.success ? '#16a34a' : '#dc2626';
                    if (data.success) {{
                        try {{
                            var modal = document.getElementById('ledger-pay-modal');
                            if (modal) {{
                                modal.style.display = 'none';
                            }}
                        }} catch (e) {{}}

                        try {{
                            window.onbeforeunload = null;
                            if (window.jQuery) {{
                                window.jQuery(window).off('beforeunload');
                            }}
                        }} catch (e) {{}}

                        try {{
                            var parseNum = function(s) {{
                                if (s === null || typeof s === 'undefined') return 0;
                                return parseFloat(String(s).replace(/,/g, '')) || 0;
                            }};
                            var fmt = function(n) {{
                                return (n || 0).toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
                            }};

                            if (data.ledger) {{
                                var perTypePaid = data.ledger.per_type_paid || {{}};

                                document.querySelectorAll('#ledger-breakdown-table tbody tr[data-payment-type-id]').forEach(function(row) {{
                                    var ptId = row.getAttribute('data-payment-type-id');
                                    var amount = parseFloat(row.getAttribute('data-amount')) || 0;
                                    var paidStr = perTypePaid[ptId] || '0.00';
                                    var paidVal = parseNum(paidStr);
                                    var balVal = amount - paidVal;

                                    var paidCell = row.querySelector('.ledger-paid');
                                    var balCell = row.querySelector('.ledger-balance');
                                    if (paidCell) paidCell.textContent = paidStr;
                                    if (balCell) {{
                                        balCell.textContent = fmt(balVal);
                                        balCell.style.color = balVal <= 0 ? 'green' : 'red';
                                    }}
                                }});

                                var totalPaidEl = document.getElementById('ledger-total-paid');
                                if (totalPaidEl && data.ledger.total_paid) totalPaidEl.textContent = data.ledger.total_paid;
                                var overallBalEl = document.getElementById('ledger-overall-balance');
                                if (overallBalEl && data.ledger.balance) overallBalEl.textContent = data.ledger.balance;
                                var overallBalCell = document.getElementById('ledger-overall-balance-cell');
                                if (overallBalCell && data.ledger.balance_color) overallBalCell.style.color = data.ledger.balance_color;

                                var modalTbody = document.querySelector('#ledger-pay-form tbody');
                                if (modalTbody) {{
                                    modalTbody.querySelectorAll('tr[data-payment-type-id]').forEach(function(row) {{
                                        var ptId = row.getAttribute('data-payment-type-id');
                                        var amount = parseFloat(row.getAttribute('data-amount')) || 0;
                                        var paidStr = perTypePaid[ptId] || '0.00';
                                        var paidVal = parseNum(paidStr);
                                        var balVal = amount - paidVal;

                                        var paidCell = row.querySelector('.modal-paid');
                                        var balCell = row.querySelector('.modal-balance');
                                        if (paidCell) paidCell.textContent = paidStr;
                                        if (balCell) {{
                                            balCell.textContent = fmt(balVal);
                                            balCell.style.color = 'red';
                                        }}

                                        var input = row.querySelector('input[name^="pay_amount_"]');
                                        if (input) {{
                                            input.value = '';
                                            input.max = balVal;
                                        }}
                                        if (balVal <= 0) {{
                                            row.remove();
                                        }}
                                    }});

                                    if (modalTbody.querySelectorAll('tr[data-payment-type-id]').length === 0) {{
                                        modalTbody.innerHTML = '<tr><td colspan="5" style="padding: 12px; text-align: center;">No outstanding balances.</td></tr>';
                                    }}
                                }}
                            }}
                        }} catch (e) {{}}

                        try {{
                            if (data.receipt && data.receipt.items) {{
                                var confirmBody = document.getElementById('ledger-confirm-body');
                                var html = '';
                                html += '<div style="margin-bottom: 10px; color: #16a34a; font-weight: 600;">Payment recorded successfully.</div>';
                                html += '<table style="width: 100%; border-collapse: collapse;">';
                                html += '<thead><tr style="background-color: #f2f2f2;">';
                                html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Paid For</th>';
                                html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Amount</th>';
                                html += '</tr></thead><tbody>';
                                data.receipt.items.forEach(function(item) {{
                                    html += '<tr>';
                                    html += '<td style="border: 1px solid #ddd; padding: 8px;">' + item.payment_type + '</td>';
                                    html += '<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">' + item.amount + '</td>';
                                    html += '</tr>';
                                }});
                                html += '</tbody>';
                                html += '<tfoot><tr style="background-color: #f9f9f9; font-weight: bold;">';
                                html += '<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">Total</td>';
                                html += '<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">' + (data.receipt.total || '') + '</td>';
                                html += '</tr></tfoot>';
                                html += '</table>';
                                if (confirmBody) confirmBody.innerHTML = html;
                                var confirmModal = document.getElementById('ledger-confirm-modal');
                                if (confirmModal) confirmModal.style.display = 'block';
                            }}
                        }} catch (e) {{}}

                        if (button) button.disabled = false;
                    }} else {{
                        if (button) button.disabled = false;
                    }}
                }})
                .catch(function(error) {{
                    messageDiv.textContent = 'Payment failed: ' + error.message;
                    messageDiv.style.color = '#dc2626';
                    if (button) button.disabled = false;
                }});
                return false;
            }};
            (function() {{
                var modal = document.getElementById('ledger-pay-modal');
                var confirmModal = document.getElementById('ledger-confirm-modal');
                var csrfInput = document.getElementById('ledger-pay-csrf');
                if (csrfInput) {{
                    var token = '';
                    var adminCsrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
                    if (adminCsrf) {{
                        token = adminCsrf.value;
                    }}
                    if (!token) {{
                        var cookie = document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)');
                        token = cookie ? cookie.pop() : '';
                    }}
                    csrfInput.value = token;
                }}
                window.onclick = function(event) {{
                    if (event.target == modal) {{
                        modal.style.display = 'none';
                    }}
                    if (event.target == confirmModal) {{
                        confirmModal.style.display = 'none';
                    }}
                }}
            }})();
        </script>
        """

        ledger_html += modal_html
        return mark_safe(ledger_html)

    # Add print action
    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path('print_ledger/<int:ledger_id>/', self.admin_site.admin_view(self.print_ledger), name='print_ledger'),
            path('ledger_pdf/<int:ledger_id>/', self.admin_site.admin_view(self.ledger_pdf), name='ledger_pdf'),
            path('pay_ledger/<int:ledger_id>/', self.admin_site.admin_view(self.pay_ledger), name='pay_ledger'),
        ]
        return custom_urls + urls

    def print_ledger(self, request, ledger_id):
        ledger = Ledger.objects.get(id=ledger_id)
        ledger_html = self.ledger_details(ledger)
        return HttpResponse(ledger_html, content_type="text/html")

    def ledger_pdf(self, request, ledger_id):
        ledger = Ledger.objects.select_related('student', 'study_year', 'semester').get(id=ledger_id)
        student = ledger.student

        totals = ledger.payments.values('payment_type_id').annotate(total=Sum('amount'))
        per_type_paid = {row['payment_type_id']: (row['total'] or Decimal('0.00')) for row in totals}
        total_paid = sum(per_type_paid.values(), Decimal('0.00'))
        balance = ledger.required_amount - total_paid
        total_paid_display = f"{total_paid:,.2f}"
        balance_display = f"{balance:,.2f}"

        breakdowns = []
        for b in ledger.payment_type_breakdowns.select_related('payment_type').all():
            paid = per_type_paid.get(b.payment_type_id, Decimal('0.00'))
            row_balance = b.amount - paid
            breakdowns.append({
                'payment_type': b.payment_type.name,
                'amount_display': f"{b.amount:,.2f}",
                'paid_display': f"{paid:,.2f}",
                'balance_display': f"{row_balance:,.2f}",
                'balance_color': '#15803d' if row_balance <= 0 else '#b91c1c',
            })

        payment_rows = []
        for p in ledger.payments.select_related('payment_type').order_by('date'):
            payment_rows.append({
                'date_display': p.date.strftime('%Y-%m-%d %H:%M'),
                'payment_type': p.payment_type.name,
                'amount_display': f"{p.amount:,.2f}",
            })

        context = {
            'ledger': ledger,
            'student': student,
            'passport_photo_url': student.passport_photo.url if getattr(student, 'passport_photo', None) else None,
            'breakdowns': breakdowns,
            'payments': payment_rows,
            'total_paid_display': total_paid_display,
            'balance_display': balance_display,
            'overall_balance_color': '#15803d' if balance <= 0 else '#b91c1c',
            'generated_on': datetime.now(),
        }

        pdf = _render_pdf('admin/finance/ledger/ledger_pdf.html', context)
        if not pdf:
            return HttpResponse('Failed to generate ledger PDF.', status=500)

        filename = f"ledger_{ledger.ledger_number}.pdf" if ledger.ledger_number else f"ledger_{ledger.id}.pdf"
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def pay_ledger(self, request, ledger_id):
        from django.contrib import messages
        from django.http import JsonResponse
        from django.shortcuts import redirect
        from academics.models import Enrollment
        from .models import Payment

        if request.method != 'POST':
            return redirect('admin:finance_ledger_change', ledger_id)

        try:
            ledger = Ledger.objects.select_related('student', 'study_year', 'semester').get(id=ledger_id)
            student = ledger.student
            enrollment = Enrollment.objects.filter(
                student=student,
                study_year=ledger.study_year,
                semester=ledger.semester,
            ).first()

            if not enrollment:
                return JsonResponse({'success': False, 'message': 'No enrollment found for this ledger. Payment could not be recorded.'})

            created_items = []
            total_created_amount = Decimal('0.00')
            for key, value in request.POST.items():
                if key.startswith('pay_amount_') and value:
                    try:
                        payment_type_id = int(key.replace('pay_amount_', ''))
                        amount = Decimal(value)
                    except (ValueError, InvalidOperation):
                        continue
                    if amount <= 0:
                        continue

                    payment = Payment.objects.create(
                        enrollment=enrollment,
                        payment_type_id=payment_type_id,
                        amount=amount,
                        ledger=ledger,
                    )
                    created_items.append({
                        'payment_type_id': payment.payment_type_id,
                        'payment_type': payment.payment_type.name,
                        'amount': f"{payment.amount:,.2f}",
                    })
                    total_created_amount += amount

            if not created_items:
                return JsonResponse({'success': False, 'message': 'No payment amounts were provided.'})

            payment_totals = Payment.objects.filter(
                enrollment__student=student,
                enrollment__study_year=ledger.study_year,
                enrollment__semester=ledger.semester,
            ).values('payment_type_id').annotate(total=Sum('amount'))

            per_type_paid = {str(row['payment_type_id']): f"{(row['total'] or Decimal('0.00')):,.2f}" for row in payment_totals}
            total_paid = sum((row['total'] or Decimal('0.00') for row in payment_totals), Decimal('0.00'))
            balance = ledger.required_amount - total_paid

            return JsonResponse({
                'success': True,
                'message': f"{len(created_items)} payment(s) recorded successfully.",
                'receipt': {
                    'items': created_items,
                    'total': f"{total_created_amount:,.2f}",
                },
                'ledger': {
                    'per_type_paid': per_type_paid,
                    'total_paid': f"{total_paid:,.2f}",
                    'balance': f"{balance:,.2f}",
                    'balance_color': 'green' if balance <= 0 else 'red',
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Payment failed: {str(e)}'})

    # Add print button in the admin page
    def print_button(self, obj):
        return format_html(
            '<a href="{}" class="button" target="_blank">Print Ledger</a> <a href="{}" class="button" target="_blank">PDF</a>',
            reverse('admin:print_ledger', args=[obj.id]),
            reverse('admin:ledger_pdf', args=[obj.id]),
        )

    print_button.short_description = 'Print'

    class Media:
        js = ('admin/js/vendor/jquery/jquery.js', 'admin/js/actions.js', 'js/print_ledger.js')
