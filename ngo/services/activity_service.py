from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ngo.models import NGO, NGOAvailability
from registrations.models import Registration


class ActivityService:
    @staticmethod
    def _raise_validation_error(exc: ValidationError):
        if hasattr(exc, "message_dict"):
            parts = []
            for field, messages in exc.message_dict.items():
                parts.extend(f"{field}: {message}" for message in messages)
            raise ValueError(" ".join(parts))
        raise ValueError(" ".join(exc.messages))

    @staticmethod
    def _combine_date_time(date_part, time_part):
        date_part = (date_part or "").strip()
        time_part = (time_part or "").strip()
        if not date_part or not time_part:
            return None
        return f"{date_part}T{time_part}"

    @staticmethod
    def _parse_dt(value):
        if value is None:
            return None
        if hasattr(value, "tzinfo"):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            dt = parse_datetime(value)
            if dt is None:
                # `datetime-local` can come without seconds; try appending ":00"
                if len(value) == 16 and "T" in value:
                    dt = parse_datetime(value + ":00")
            if dt is None:
                return None
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        return None

    # --------------------
    # NGO (master) methods
    # --------------------
    @staticmethod
    def list_ngos_admin():
        return (
            NGO.objects.filter(is_active=True)
            .prefetch_related("availabilities")
            .order_by("name")
        )

    @staticmethod
    def create_ngo(data):
        ngo = NGO(
            name=(data.get("name") or "").strip(),
            description=(data.get("description") or "").strip(),
            contact_email=(data.get("contact_email") or "").strip(),
            contact_phone=(data.get("contact_phone") or "").strip(),
            is_active=True,
        )
        try:
            ngo.full_clean()
        except ValidationError as exc:
            ActivityService._raise_validation_error(exc)
        ngo.save()
        return ngo

    @staticmethod
    @transaction.atomic
    def update_ngo(ngo_id, data):
        ngo = NGO.objects.select_for_update().get(id=ngo_id)
        for field in ("name", "description", "contact_email", "contact_phone"):
            if field in data:
                setattr(ngo, field, (data.get(field) or "").strip())
        try:
            ngo.full_clean()
        except ValidationError as exc:
            ActivityService._raise_validation_error(exc)
        ngo.save(update_fields=["name", "description", "contact_email", "contact_phone"])
        return ngo

    @staticmethod
    @transaction.atomic
    def deactivate_ngo(ngo_id):
        ngo = NGO.objects.select_for_update().get(id=ngo_id)
        ngo.is_active = False
        ngo.save(update_fields=["is_active"])
        return ngo

    # -----------------------------
    # Availability (slot) methods
    # -----------------------------
    @staticmethod
    def list_available_slots_for_employees():
        slots = list(NGOAvailability.objects.select_related("ngo").filter(is_active=True, ngo__is_active=True))

        counts = (
            Registration.objects.filter(activity__in=slots)
            .values("activity_id")
            .annotate(taken=Count("id"))
        )
        taken_by_slot_id = {row["activity_id"]: row["taken"] for row in counts}

        for slot in slots:
            slots_taken = int(taken_by_slot_id.get(slot.id, 0))
            slots_remaining = max(int(slot.max_slots) - slots_taken, 0)
            slot.slots_taken = slots_taken
            slot.slots_remaining = slots_remaining

        return slots

    @staticmethod
    def list_slots_admin():
        return (
            NGOAvailability.objects.select_related("ngo")
            .prefetch_related("registrations")
            .filter(is_active=True, ngo__is_active=True)
            .order_by("-service_date")
        )

    @staticmethod
    def create_slot(data):
        ngo_id = data.get("ngo_id")
        service_date_raw = data.get("service_date") or ActivityService._combine_date_time(
            data.get("service_date_date"),
            data.get("service_date_time"),
        )
        cutoff_time_raw = data.get("cutoff_time") or ActivityService._combine_date_time(
            data.get("cutoff_date"),
            data.get("cutoff_time_only"),
        )

        slot = NGOAvailability(
            ngo_id=ngo_id,
            service_type=(data.get("service_type") or "General").strip(),
            description=data.get("description"),
            location=data.get("location"),
            service_date=ActivityService._parse_dt(service_date_raw),
            cutoff_time=ActivityService._parse_dt(cutoff_time_raw),
            max_slots=int(data.get("max_slots") or 0),
            is_active=True,
        )
        try:
            slot.full_clean()
        except ValidationError as exc:
            ActivityService._raise_validation_error(exc)
        slot.save()
        return slot

    @staticmethod
    @transaction.atomic
    def update_slot(slot_id, data):
        slot = NGOAvailability.objects.select_for_update().get(id=slot_id)

        field_updates = {}

        if "ngo_id" in data and (data.get("ngo_id") or "").strip():
            slot.ngo_id = data.get("ngo_id")
            field_updates["ngo_id"] = slot.ngo_id

        for field in ("service_type", "location", "description"):
            if field in data and (data.get(field) is not None):
                val = data.get(field)
                if isinstance(val, str):
                    val = val.strip()
                if val != "":
                    setattr(slot, field, val)
                    field_updates[field] = val

        if "service_date" in data:
            dt = ActivityService._parse_dt(data.get("service_date"))
            if dt is not None:
                slot.service_date = dt
                field_updates["service_date"] = dt

        if "cutoff_time" in data:
            dt = ActivityService._parse_dt(data.get("cutoff_time"))
            if dt is not None:
                slot.cutoff_time = dt
                field_updates["cutoff_time"] = dt

        if "max_slots" in data and (data.get("max_slots") not in (None, "")):
            slot.max_slots = int(data.get("max_slots"))
            field_updates["max_slots"] = slot.max_slots

        if field_updates:
            try:
                slot.full_clean()
            except ValidationError as exc:
                ActivityService._raise_validation_error(exc)
            slot.save(update_fields=list(field_updates.keys()))
        return slot

    @staticmethod
    @transaction.atomic
    def deactivate_slot(slot_id):
        slot = NGOAvailability.objects.select_for_update().get(id=slot_id)
        slot.is_active = False
        slot.save(update_fields=["is_active"])
        return slot

    # ----------------------------------------------------
    # Backwards-compatible methods used by current views
    # (we will refactor views/templates in a later phase)
    # ----------------------------------------------------
    @staticmethod
    def list_active_with_slots():
        return ActivityService.list_available_slots_for_employees()

    @staticmethod
    def list_all_admin():
        return ActivityService.list_slots_admin()

    @staticmethod
    def create_activity(data):
        # Legacy admin form doesn't yet have NGO/service_type fields.
        # Create (or reuse) NGO by name and create an availability slot.
        ngo_name = (data.get("name") or "").strip()
        ngo, _ = NGO.objects.get_or_create(name=ngo_name, defaults={"is_active": True})
        if (data.get("description") or "").strip() and not ngo.description:
            ngo.description = (data.get("description") or "").strip()
            ngo.save(update_fields=["description"])

        return NGOAvailability.objects.create(
            ngo=ngo,
            service_type="General",
            description=data.get("description"),
            location=data.get("location"),
            service_date=ActivityService._parse_dt(data.get("service_date")),
            cutoff_time=ActivityService._parse_dt(data.get("cutoff_time")),
            max_slots=int(data.get("max_slots") or 0),
            is_active=True,
        )

    @staticmethod
    @transaction.atomic
    def update_activity(activity_id, data):
        return ActivityService.update_slot(activity_id, data)

    @staticmethod
    @transaction.atomic
    def deactivate_activity(activity_id):
        return ActivityService.deactivate_slot(activity_id)

