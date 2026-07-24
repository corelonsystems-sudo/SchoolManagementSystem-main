from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.course_list, name='course_list'),
    path('student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('student/<int:student_id>/enroll/', views.enroll_student, name='enroll_student'),
    path('academic-data/', views.get_academic_data, name='get_academic_data'),
    path('bulk-enroll/', views.bulk_enroll_students, name='bulk_enroll_students'),
]
