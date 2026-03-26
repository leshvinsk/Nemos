from django.contrib import admin

from .models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("employee", "activity", "registered_at")
    list_filter = ("activity__ngo", "activity__service_type")
    search_fields = ("employee__username", "activity__ngo__name", "activity__service_type")
