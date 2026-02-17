from django.contrib.auth.models import User
from django.db import models

from ngo.models import NGOAvailability

class Registration(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(NGOAvailability, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.employee.username} - {self.activity.ngo.name}"
