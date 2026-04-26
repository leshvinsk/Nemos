from django.urls import path

from nemos.microservices import registration_service_views


urlpatterns = [
    path("registrations/", registration_service_views.registration_list, name="registration-service-list"),
    path("registrations/summary/", registration_service_views.registration_summary, name="registration-service-summary"),
]
