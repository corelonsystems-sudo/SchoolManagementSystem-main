from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('portal/', views.portal_landing, name='portal_landing'),
    path('apply/', views.apply_view, name='apply'),
    path('apply/success/', views.apply_success, name='apply_success'),
    path('lookup/', views.lookup_application, name='lookup_application'),
    path('update/application/<int:application_id>/', views.update_application, name='update_application'),
    path('update/student/<int:student_id>/', views.update_student, name='update_student'),
    path('update/success/', views.update_success, name='update_success'),
    path('old-application/', views.add_old_application, name='add_old_application'),
    path('old-application/success/', views.old_application_success, name='old_application_success'),
    path('student-login/', views.student_login, name='student_login'),
    path('student-logout/', views.student_logout, name='student_logout'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/admission-form/<int:student_id>/', views.student_admission_form, name='student_admission_form'),
    path('admission-letter/<int:student_id>/', views.admission_letter, name='admission_letter'),
]
