from django.contrib import admin
from django.urls import path, include
import SchoolManagementSystem.admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect  # Add this

urlpatterns = [
    path('', lambda request: redirect('admin:index')),  # Redirect root to admin
    path('jet/', include('jet.urls', 'jet')),
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
    path('admin/dashboard-stats/', SchoolManagementSystem.admin.dashboard_stats, name='dashboard_stats'),
    path('admin/export-database/', SchoolManagementSystem.admin.export_database, name='export_database'),
    path('admin/import-database/', SchoolManagementSystem.admin.import_database, name='import_database'),
    path('admin/', admin.site.urls),
    path('admissions/', include('admissions.urls')),
    path('academics/', include('academics.urls')),
    path('finance/', include('finance.urls')),
    path('staff/', include('staff.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)