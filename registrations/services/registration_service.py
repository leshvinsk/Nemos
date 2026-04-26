from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, IntegerField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.cache_utils import (
    PARTICIPANT_SUMMARY_CACHE_KEY,
    cache_timeout,
    clear_participant_cache,
)
from ngo.models import NGOAvailability
from registrations.models import Registration


class RegistrationService:
    @staticmethod
    @transaction.atomic
    def register_employee(user, activity_id):
        try:
            slot = NGOAvailability.objects.select_related("ngo").select_for_update().get(
                id=activity_id, is_active=True, ngo__is_active=True
            )
        except NGOAvailability.DoesNotExist:
            return False, "Slot not found or inactive."

        now = timezone.now()
        if now > slot.cutoff_time:
            return False, "Registration cutoff time has passed."

        if Registration.objects.filter(employee=user, activity=slot).exists():
            return False, "You are already registered for this activity."

        taken = Registration.objects.filter(activity=slot).count()
        if taken >= slot.max_slots:
            return False, "No slots remaining for this activity."

        registration = Registration(employee=user, activity=slot)
        try:
            registration.full_clean()
        except ValidationError as exc:
            return False, " ".join(exc.messages)

        registration.save()
        clear_participant_cache()
        return True, "Registration successful."

    @staticmethod
    @transaction.atomic
    def cancel_registration(user, activity_id):
        try:
            slot = NGOAvailability.objects.select_related("ngo").select_for_update().get(
                id=activity_id, is_active=True, ngo__is_active=True
            )
        except NGOAvailability.DoesNotExist:
            return False, "Slot not found or inactive."

        now = timezone.now()
        if now > slot.cutoff_time:
            return False, "Cancellation cutoff time has passed."

        qs = Registration.objects.filter(employee=user, activity=slot)
        if not qs.exists():
            return False, "No registration found to cancel."

        qs.delete()
        clear_participant_cache()
        return True, "Registration cancelled."

    @staticmethod
    def monitor_summary():
        cached_summary = cache.get(PARTICIPANT_SUMMARY_CACHE_KEY)
        if cached_summary is not None:
            return cached_summary

        summary = RegistrationService.monitor_summary_uncached()
        cache.set(PARTICIPANT_SUMMARY_CACHE_KEY, summary, cache_timeout())
        return summary

    @staticmethod
    def monitor_summary_uncached():
        slots = list(RegistrationService._activity_summary_queryset())

        offered = sum(int(s.max_slots) for s in slots)
        taken_total = sum(int(s.registration_count) for s in slots)
        remaining_total = sum(int(s.slots_remaining) for s in slots)

        rows = []
        for s in slots:
            rows.append(
                {
                    "name": s.ngo.name,
                    "service_type": s.service_type,
                    "location": s.location,
                    "service_date": s.service_date,
                    "cutoff_time": s.cutoff_time,
                    "taken": int(s.registration_count),
                    "remaining": int(s.slots_remaining),
                }
            )

        return {
            "offered": offered,
            "taken": taken_total,
            "remaining": remaining_total,
            "rows": rows,
        }

    @staticmethod
    def employee_history(user):
        return (
            Registration.objects.filter(employee=user)
            .select_related("activity__ngo")
            .order_by("-registered_at")
        )

    @staticmethod
    def _activity_summary_queryset():
        return (
            NGOAvailability.objects.select_related("ngo")
            .filter(is_active=True, ngo__is_active=True)
            .annotate(registration_count=Count("registrations", distinct=True))
            .annotate(
                slots_remaining=F("max_slots")
                - Coalesce(F("registration_count"), Value(0), output_field=IntegerField())
            )
            .order_by("service_date", "ngo__name")
        )


