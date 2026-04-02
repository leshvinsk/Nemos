from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class NGO(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name_plural = "NGOs"
        ordering = ["name"]


class NGOAvailability(models.Model):
    ngo = models.ForeignKey(NGO, on_delete=models.PROTECT, related_name="availabilities")
    service_type = models.CharField(max_length=80, default="General")
    description = models.TextField()
    location = models.CharField(max_length=150)
    service_date = models.DateTimeField()
    cutoff_time = models.DateTimeField()
    max_slots = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.ngo.name} - {self.service_date}"

    class Meta:
        verbose_name_plural = "NGOAvailabilities"
        ordering = ["service_date", "ngo__name"]

    def clean(self):
        if self.max_slots < 1:
            raise ValidationError({"max_slots": "Maximum slots must be at least 1."})

        if self.service_date and timezone.is_naive(self.service_date):
            raise ValidationError({"service_date": "Service date must include timezone information."})

        if self.cutoff_time and timezone.is_naive(self.cutoff_time):
            raise ValidationError({"cutoff_time": "Cut-off time must include timezone information."})

        if self.cutoff_time and self.service_date:
            latest_cutoff_date = (self.service_date - timedelta(days=3)).date()
            if self.cutoff_time.date() > latest_cutoff_date:
                raise ValidationError(
                    {
                        "cutoff_time": (
                            "Cut-off date must be at least 3 days earlier than the service date."
                        )
                    }
                )

    # Compatibility for existing templates/services that reference `name`.
    @property
    def name(self) -> str:
        return self.ngo.name


class _NGOActivityManager(models.Manager):
    """
    Backwards-compatible manager so existing code that still creates NGOActivity
    with a `name=` field can continue working until other apps are refactored.
    """

    def create(self, **kwargs):
        ngo_name = kwargs.pop("name", None)
        if "ngo" not in kwargs:
            if ngo_name:
                ngo, _ = NGO.objects.get_or_create(name=ngo_name, defaults={"is_active": True})
            else:
                ngo = NGO.objects.create(name="Unnamed NGO", is_active=True)
            kwargs["ngo"] = ngo

        if "service_type" not in kwargs:
            kwargs["service_type"] = "General"

        return super().create(**kwargs)


class NGOActivity(NGOAvailability):
    """
    Temporary proxy for legacy references (e.g., registrations FK, existing services).
    Do not build new features on this; use `NGOAvailability` instead.
    """

    objects = _NGOActivityManager()

    class Meta:
        proxy = True
