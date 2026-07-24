from django.shortcuts import render
from .models import Payment

def payment_list(request):
    payments = Payment.objects.all()
    return render(request, 'finance/payment_list.html', {'payments': payments})

