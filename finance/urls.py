from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('payments/', views.payment_list, name='payment_list'),
    path('reports/', views.financial_reports, name='financial_reports'),
    path('reports/download/', views.download_financial_report, name='download_financial_report'),
    path('reports/summary/', views.download_financial_summary, name='download_financial_summary'),
]
