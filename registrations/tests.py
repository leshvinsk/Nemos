from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ngo.models import NGO, NGOAvailability
from registrations.models import Registration
from registrations.services.registration_service import RegistrationService


class RegistrationRulesTests(TestCase):
    def setUp(self):
        base_time = timezone.now()
        self.user = get_user_model().objects.create_user(username="employee1", password="test-pass-123")
        self.ngo = NGO.objects.create(name="Care For All", is_active=True)
        self.activity = NGOAvailability.objects.create(
            ngo=self.ngo,
            service_type="Beach Cleanup",
            description="Community effort",
            location="Port Klang",
            service_date=base_time + timedelta(days=5),
            cutoff_time=base_time + timedelta(days=2),
            max_slots=1,
            is_active=True,
        )

    def test_duplicate_registration_is_blocked(self):
        Registration.objects.create(employee=self.user, activity=self.activity)
        registration = Registration(employee=self.user, activity=self.activity)

        with self.assertRaises(ValidationError):
            registration.full_clean()

    def test_full_activity_is_blocked(self):
        other_user = get_user_model().objects.create_user(username="employee2", password="test-pass-123")
        Registration.objects.create(employee=other_user, activity=self.activity)

        success, message = RegistrationService.register_employee(self.user, self.activity.id)

        self.assertFalse(success)
        self.assertIn("No slots remaining", message)


class ReportingViewsTests(TestCase):
    def setUp(self):
        self.client.force_login(
            get_user_model().objects.create_user(
                username="admin1",
                password="test-pass-123",
                is_staff=True,
            )
        )

    def test_admin_monitor_view_loads(self):
        response = self.client.get(reverse("registrations:admin_monitor"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monitor")
