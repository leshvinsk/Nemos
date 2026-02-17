from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

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

        Registration.objects.create(employee=user, activity=slot)
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
        return True, "Registration cancelled."

    @staticmethod
    def monitor_summary():
        slots = list(NGOAvailability.objects.select_related("ngo").filter(is_active=True, ngo__is_active=True))

        counts = (
            Registration.objects.filter(activity__in=slots)
            .values("activity_id")
            .annotate(taken=Count("id"))
        )
        taken_by_slot_id = {row["activity_id"]: row["taken"] for row in counts}

        offered = sum(int(s.max_slots) for s in slots)
        taken_total = sum(int(taken_by_slot_id.get(s.id, 0)) for s in slots)
        remaining_total = offered - taken_total

        rows = []
        for s in slots:
            taken = int(taken_by_slot_id.get(s.id, 0))
            remaining = max(int(s.max_slots) - taken, 0)
            rows.append(
                {
                    "name": s.ngo.name,
                    "service_type": s.service_type,
                    "location": s.location,
                    "cutoff_time": s.cutoff_time,
                    "taken": taken,
                    "remaining": remaining,
                }
            )

        return {
            "offered": offered,
            "taken": taken_total,
            "remaining": remaining_total,
            "rows": rows,
        }

