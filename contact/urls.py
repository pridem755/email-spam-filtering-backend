from django.urls import path
from .views import ContactSubmitView, HealthCheckView

urlpatterns = [
    path('contact/submit/', ContactSubmitView.as_view(), name='contact-submit'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]