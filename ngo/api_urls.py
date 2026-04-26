from django.urls import path

from ngo import api_views

urlpatterns = [
    path("v1/ngos/", api_views.NGOListCreateAPIView.as_view(), name="api-v1-ngo-list"),
    path("v1/ngos/<int:pk>/", api_views.NGODetailAPIView.as_view(), name="api-v1-ngo-detail"),
    path("v1/activities/", api_views.ActivityListAPIView.as_view(), name="api-v1-activity-list"),
    path("v1/registrations/", api_views.RegistrationCreateAPIView.as_view(), name="api-v1-registration-create"),
    path(
        "v1/registrations/<int:activity_id>/cancel/",
        api_views.RegistrationCancelAPIView.as_view(),
        name="api-v1-registration-cancel",
    ),
    path("v1/my-registrations/", api_views.RegistrationListAPIView.as_view(), name="api-v1-registration-list"),
    path("v2/activities/", api_views.ActivityListV2APIView.as_view(), name="api-v2-activity-list"),
]
