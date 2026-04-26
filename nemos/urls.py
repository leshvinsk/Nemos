from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('', include('accounts.urls')),
    path('service-day/', include('ngo.urls')),
    path('service-day/', include('registrations.urls')),
    path('service-day/', include('notifications.urls')),
    path('api/', include('ngo.api_urls')),

    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
