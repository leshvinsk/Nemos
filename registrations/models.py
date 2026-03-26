from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from ngo.models import NGOAvailability


class Registration(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(
        NGOAvailability,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.employee.username} - {self.activity.ngo.name}"

    class Meta:
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "activity"],
                name="unique_employee_activity_registration",
            ),
        ]

    def clean(self):
        if self.activity_id is None or self.employee_id is None:
            return

        if self.activity.cutoff_time and timezone.now() > self.activity.cutoff_time:
            raise ValidationError("Registration cut-off time has passed.")

        duplicate_exists = (
            Registration.objects.exclude(pk=self.pk)
            .filter(employee_id=self.employee_id, activity_id=self.activity_id)
            .exists()
        )
        if duplicate_exists:
            raise ValidationError("Employee is already registered for this activity.")

        taken = Registration.objects.exclude(pk=self.pk).filter(activity_id=self.activity_id).count()
        if taken >= self.activity.max_slots:
            raise ValidationError("No slots remaining for this activity.")
