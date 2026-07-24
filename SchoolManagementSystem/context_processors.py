from admissions.models import Student as AdmissionStudent
from academics.models import Student as AcademicStudent


def dashboard_stats(request):
    """Context processor to provide student statistics for the dashboard."""
    # Count from admissions model for status-based stats
    total_admissions = AdmissionStudent.objects.count()
    enrolled = AdmissionStudent.objects.filter(enrollment_status='ENROLLED').count()
    completed = AdmissionStudent.objects.filter(enrollment_status='COMPLETED').count()
    withdrawn = AdmissionStudent.objects.filter(enrollment_status='WITHDRAWN').count()
    deferred = AdmissionStudent.objects.filter(enrollment_status='DEFERRED').count()
    pending = AdmissionStudent.objects.filter(enrollment_status='PENDING').count()

    # Count students who have been enrolled in the academic system
    active_enrolled = AcademicStudent.objects.count()

    return {
        'stats_total_students': total_admissions,
        'stats_enrolled': active_enrolled,
        'stats_completed': completed,
        'stats_withdrawn': withdrawn,
        'stats_deferred': deferred,
        'stats_pending': pending,
    }
