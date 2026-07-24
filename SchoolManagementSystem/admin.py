from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.forms import UserChangeForm
from django import forms
from django.utils.safestring import mark_safe
from django.apps import apps
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q


class GroupedPermissionsWidget(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, renderer=None):
        selected_ids = {str(item) for item in (value or [])}
        choices = list(self.choices)
        permission_ids = [str(choice[0]) for choice in choices]
        permission_objects = Permission.objects.filter(
            id__in=permission_ids
        ).select_related('content_type')
        permissions = {str(permission.id): permission for permission in permission_objects}
        grouped_permissions = {}

        for choice in choices:
            permission_id = str(choice[0])
            permission = permissions.get(permission_id)
            if not permission:
                continue
            app_label = permission.content_type.app_label
            app_name = apps.get_app_config(app_label).verbose_name
            grouped_permissions.setdefault((app_label, app_name), []).append({
                'id': permission_id,
                'label': choice[1],
                'selected': permission_id in selected_ids,
            })

        html = [
            '<div class="permissions-control" data-permissions-control>',
            '<div class="permissions-toolbar">',
            '<div class="permissions-title">User permissions:</div>',
            '<div class="permissions-actions">',
            '<button type="button" class="permissions-action" data-select-all>Select All</button>',
            '<button type="button" class="permissions-action" data-deselect-all>Deselect All</button>',
            '</div>',
            '<input type="search" class="permissions-search" placeholder="Search permissions..." data-permissions-search>',
            '</div>',
            '<div class="permissions-app-list">',
        ]

        for (app_label, app_name), app_permissions in sorted(grouped_permissions.items()):
            selected_count = sum(permission['selected'] for permission in app_permissions)
            total_count = len(app_permissions)
            html.append(
                f'<section class="permissions-app" data-app="{app_label}">'
                f'<div class="permissions-app-header">'
                f'<strong>{app_name}</strong>'
                f'<span class="permissions-count" data-app-count>{selected_count}/{total_count}</span>'
                f'</div>'
                f'<div class="permissions-grid">'
                f'<label class="permissions-select-app"><input type="checkbox" data-select-app> '
                f'<span>Select all {app_name}</span></label>'
            )
            for permission in app_permissions:
                checked = ' checked' if permission['selected'] else ''
                html.append(
                    f'<label class="permission-item" data-permission-label="{permission["label"].lower()}">'
                    f'<input type="checkbox" name="{name}" value="{permission["id"]}"{checked} data-permission-checkbox>'
                    f'<span>{permission["label"]}</span></label>'
                )
            html.append('</div></section>')

        html.extend([
            '</div>',
            '<div class="permissions-help">Specific permissions for this user. Hold down “Control”, or “Command” on a Mac, to select more than one.</div>',
            '</div>',
            '<script>',
            '(function() {',
            'function initializePermissions(root) {',
            'if (root.dataset.permissionsReady) return;',
            'root.dataset.permissionsReady = "true";',
            'const boxes = () => Array.from(root.querySelectorAll("[data-permission-checkbox]"));',
            'const updateCounts = () => root.querySelectorAll("[data-app]").forEach(app => {',
            'const all = Array.from(app.querySelectorAll("[data-permission-checkbox]"));',
            'const selected = all.filter(box => box.checked).length;',
            'app.querySelector("[data-app-count]").textContent = selected + "/" + all.length;',
            'const appToggle = app.querySelector("[data-select-app]");',
            'appToggle.checked = all.length > 0 && selected === all.length;',
            'appToggle.indeterminate = selected > 0 && selected < all.length;',
            '});',
            'root.querySelector("[data-select-all]").addEventListener("click", () => { boxes().forEach(box => box.checked = true); updateCounts(); });',
            'root.querySelector("[data-deselect-all]").addEventListener("click", () => { boxes().forEach(box => box.checked = false); updateCounts(); });',
            'root.querySelectorAll("[data-select-app]").forEach(toggle => toggle.addEventListener("change", event => {',
            'const app = event.target.closest("[data-app]"); app.querySelectorAll("[data-permission-checkbox]").forEach(box => box.checked = event.target.checked); updateCounts();',
            '}));',
            'root.addEventListener("change", event => { if (event.target.matches("[data-permission-checkbox]")) updateCounts(); });',
            'root.querySelector("[data-permissions-search]").addEventListener("input", event => {',
            'const term = event.target.value.toLowerCase().trim();',
            'root.querySelectorAll(".permission-item, .permissions-select-app").forEach(item => { item.hidden = term && !item.textContent.toLowerCase().includes(term); });',
            '});',
            'updateCounts();',
            '}',
            'document.querySelectorAll("[data-permissions-control]").forEach(initializePermissions);',
            '})();',
            '</script>',
        ])
        return mark_safe(''.join(html))


class GroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].widget = GroupedPermissionsWidget()
        self.fields['permissions'].queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')


class CustomGroupAdmin(GroupAdmin):
    form = GroupAdminForm
    list_display = ('name', 'get_permissions_count')
    filter_horizontal = ()

    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = 'Permissions'


class UserAdminForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'user_permissions' in self.fields:
            self.fields['user_permissions'].widget = GroupedPermissionsWidget()
            self.fields['user_permissions'].queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')


class CustomUserAdmin(UserAdmin):
    form = UserAdminForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
    filter_horizontal = ()


# Unregister the default User and Group admins and register custom ones
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Group, CustomGroupAdmin)


@staff_member_required
@require_GET
def dashboard_stats(request):
    """API endpoint for dashboard statistics and chart data"""
    from academics.models import Student as AcademicStudent, Intake, AcademicYear, Course

    # Get filter parameters
    intake_id = request.GET.get('intake')
    course_id = request.GET.get('course')
    year_id = request.GET.get('year')
    gender = request.GET.get('gender')

    # Build base queryset
    queryset = AcademicStudent.objects.select_related('admission', 'intake')

    # Apply filters
    if intake_id:
        queryset = queryset.filter(intake_id=intake_id)
    if course_id:
        queryset = queryset.filter(admission__course_id=course_id)
    if year_id:
        queryset = queryset.filter(intake__academic_year_id=year_id)
    if gender:
        queryset = queryset.filter(admission__gender=gender)

    # Get filter options - all intakes including closed/inactive
    intakes = [{'id': i.id, 'name': i.name, 'status': i.status} for i in Intake.objects.all().order_by('-start_date')]
    courses = [{'id': c.id, 'name': c.name} for c in Course.objects.all()]
    years = [{'id': y.id, 'year': y.name} for y in AcademicYear.objects.all().order_by('-start_date')]

    # Intake statistics - show ALL intakes including those with 0 students
    all_intakes = Intake.objects.all().order_by('-start_date')
    intake_labels = []
    intake_data_list = []
    for intake in all_intakes:
        count = queryset.filter(intake_id=intake.id).count()
        intake_labels.append(intake.name)
        intake_data_list.append(count)
    # Also include students with no intake assigned
    no_intake_count = queryset.filter(intake__isnull=True).count()
    if no_intake_count > 0:
        intake_labels.append('No Intake')
        intake_data_list.append(no_intake_count)
    intake_stats = {
        'labels': intake_labels,
        'data': intake_data_list
    }

    # Course statistics
    course_data = queryset.values('admission__course__name').annotate(
        count=Count('id')
    ).order_by('-count')
    course_stats = {
        'labels': [item['admission__course__name'] or 'No Course' for item in course_data],
        'data': [item['count'] for item in course_data]
    }

    # Gender statistics
    gender_data = queryset.values('admission__gender').annotate(
        count=Count('id')
    ).order_by('-count')
    gender_stats = {
        'labels': [item['admission__gender'] or 'Unknown' for item in gender_data],
        'data': [item['count'] for item in gender_data]
    }

    # Academic year statistics (via intake.academic_year)
    year_data = queryset.filter(
        intake__academic_year__isnull=False
    ).values('intake__academic_year__name').annotate(
        count=Count('id')
    ).order_by('intake__academic_year__name')
    year_stats = {
        'labels': [item['intake__academic_year__name'] or 'No Academic Year' for item in year_data],
        'data': [item['count'] for item in year_data]
    }

    # Status statistics
    status_data = queryset.values('admission__enrollment_status').annotate(
        count=Count('id')
    ).order_by('-count')
    status_stats = {
        'labels': [item['admission__enrollment_status'] or 'Unknown' for item in status_data],
        'data': [item['count'] for item in status_data]
    }

    return JsonResponse({
        'intakes': intakes,
        'courses': courses,
        'years': years,
        'intake_stats': intake_stats,
        'course_stats': course_stats,
        'gender_stats': gender_stats,
        'year_stats': year_stats,
        'status_stats': status_stats,
    })
