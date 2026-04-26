from django.urls import path, re_path

from nemos.microservices import gateway_views


urlpatterns = [
    path("", gateway_views.gateway_home, name="gateway-home"),
    path("registry/", gateway_views.gateway_registry, name="gateway-registry"),
    re_path(r"^api/users/(?P<downstream_path>.*)$", gateway_views.users_proxy, name="gateway-users-proxy"),
    re_path(r"^api/ngos/(?P<downstream_path>.*)$", gateway_views.ngos_proxy, name="gateway-ngos-proxy"),
    re_path(r"^api/registrations/(?P<downstream_path>.*)$", gateway_views.registrations_proxy, name="gateway-registrations-proxy"),
]
