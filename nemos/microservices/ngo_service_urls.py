from django.urls import path

from nemos.microservices import ngo_service_views


urlpatterns = [
    path("ngos/", ngo_service_views.ngo_list, name="ngo-service-list"),
    path("activities/", ngo_service_views.activity_list, name="ngo-service-activity-list"),
]
