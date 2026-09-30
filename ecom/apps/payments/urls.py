from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Razorpay Gateway Endpoints
    path('razorpay/create-order/', views.create_razorpay_order_view, name='razorpay_create_order'),
    path('razorpay/verify/', views.verify_razorpay_payment_view, name='razorpay_verify'),
    path('razorpay/payment-failed/', views.record_payment_failure_view, name='razorpay_payment_failed'),
    path('razorpay/webhook/', views.razorpay_webhook_view, name='razorpay_webhook'),

    # Customer Transactions History
    path('transactions/', views.payment_transactions_view, name='transactions'),
]
