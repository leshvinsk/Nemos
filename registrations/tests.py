from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
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


class EmployeeAccessControlTests(TestCase):
    def setUp(self):
        base_time = timezone.now()
        self.client = Client()
        self.employee = get_user_model().objects.create_user(
            username="employee-access",
            password="test-pass-123",
        )
        self.admin = get_user_model().objects.create_user(
            username="admin-access",
            password="test-pass-123",
            is_staff=True,
        )
        ngo = NGO.objects.create(name="Secure NGO", is_active=True)
        self.activity = NGOAvailability.objects.create(
            ngo=ngo,
            service_type="Food Aid",
            description="Pack supplies",
            location="Shah Alam",
            service_date=base_time + timedelta(days=5),
            cutoff_time=base_time + timedelta(days=2),
            max_slots=3,
            is_active=True,
        )

    def test_employee_can_register(self):
        self.client.force_login(self.employee)
        response = self.client.post(reverse("registrations:register", args=[self.activity.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Registration.objects.filter(employee=self.employee, activity=self.activity).exists()
        )

    def test_admin_cannot_register_as_employee(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("registrations:register", args=[self.activity.id]))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Registration.objects.filter(employee=self.admin, activity=self.activity).exists()
        )

    def test_admin_cannot_open_employee_history(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("registrations:my_history"))
        self.assertEqual(response.status_code, 403)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "registration-cache",
        }
    }
)
class ParticipantCachingTests(TestCase):
    def setUp(self):
        cache.clear()
        base_time = timezone.now()
        self.user = get_user_model().objects.create_user(username="cache-employee", password="test-pass-123")
        self.ngo = NGO.objects.create(name="Cache NGO", is_active=True)
        self.activity = NGOAvailability.objects.create(
            ngo=self.ngo,
            service_type="Planting",
            description="Tree planting",
            location="Putrajaya",
            service_date=base_time + timedelta(days=5),
            cutoff_time=base_time + timedelta(days=2),
            max_slots=2,
            is_active=True,
        )

    def test_monitor_summary_cache_is_invalidated_after_registration(self):
        summary_before = RegistrationService.monitor_summary()
        self.assertEqual(summary_before["taken"], 0)

        RegistrationService.register_employee(self.user, self.activity.id)
        summary_after = RegistrationService.monitor_summary()
        self.assertEqual(summary_after["taken"], 1)
