from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('', include('accounts.urls')),
    path('service-day/', include('ngo.urls')),
    path('service-day/', include('registrations.urls')),
    path('service-day/', include('notifications.urls')),

    path('admin/', admin.site.urls),
]
