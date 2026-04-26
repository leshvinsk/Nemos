from django.urls import path

from nemos.microservices import user_service_views


urlpatterns = [
    path("users/", user_service_views.user_list, name="user-service-list"),
    path("users/<int:user_id>/", user_service_views.user_detail, name="user-service-detail"),
]
