from django.contrib import admin
from .models import Department, Employee, EmployeeDocument

class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 1
    fields = ('name', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'department', 'category', 'role', 'email', 'phone', 'start_date', 'end_date')
    search_fields = ('first_name', 'last_name', 'email', 'role')
    list_filter = ('department', 'category')
    inlines = [EmployeeDocumentInline]
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Employment Details', {
            'fields': ('department', 'category', 'role', 'start_date', 'end_date')
        }),
    )
