from django.contrib import admin

from .models import NGO, NGOAvailability


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_email", "contact_phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_email", "contact_phone")


@admin.register(NGOAvailability)
class NGOAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "ngo",
        "service_type",
        "location",
        "service_date",
        "cutoff_time",
        "max_slots",
        "is_active",
    )
    list_filter = ("is_active", "service_type", "ngo")
    search_fields = ("ngo__name", "service_type", "location", "description")
