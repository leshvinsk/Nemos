from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from ngo.models import NGO, NGOAvailability
from ngo.services.activity_service import ActivityService
from registrations.models import Registration


class AdminNgoCsrfTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_user(
            username="staff1",
            password="test-pass-123",
            is_staff=True,
        )
        self.ngo = NGO.objects.create(name="Test NGO", is_active=True)

    def test_deactivate_without_csrf_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("ngo:admin_ngo_delete", args=[self.ngo.id]))
        self.assertEqual(response.status_code, 403)

    def test_deactivate_with_csrf_succeeds(self):
        self.client.force_login(self.user)
        self.client.get(reverse("ngo:admin_ngo_manage"))
        csrf_token = self.client.cookies["csrftoken"].value

        response = self.client.post(
            reverse("ngo:admin_ngo_delete", args=[self.ngo.id]),
            {"csrfmiddlewaretoken": csrf_token},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ngo:admin_ngo_manage"))

        self.ngo.refresh_from_db()
        self.assertFalse(self.ngo.is_active)


class AdminVisibilityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="staff2",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_inactive_ngo_and_activity_are_hidden_from_admin_pages(self):
        ngo = NGO.objects.create(name="Hidden NGO", is_active=True)
        base_time = timezone.now()
        activity = NGOAvailability.objects.create(
            ngo=ngo,
            service_type="General",
            description="Hidden activity",
            location="Test",
            service_date=base_time + timedelta(days=4),
            cutoff_time=base_time + timedelta(days=1),
            max_slots=5,
            is_active=True,
        )

        self.client.post(reverse("ngo:admin_activity_delete", args=[activity.id]))
        self.client.post(reverse("ngo:admin_ngo_delete", args=[ngo.id]))

        ngo_page = self.client.get(reverse("ngo:admin_ngo_manage"))
        self.assertNotContains(ngo_page, "Hidden NGO")

        activity_page = self.client.get(reverse("ngo:admin_activity_manage"))
        self.assertNotContains(activity_page, "Hidden activity")

    def test_ngo_with_planned_activity_cannot_be_deactivated(self):
        ngo = NGO.objects.create(name="Protected NGO", is_active=True)
        base_time = timezone.now()
        NGOAvailability.objects.create(
            ngo=ngo,
            service_type="Planned Event",
            description="Upcoming",
            location="Test",
            service_date=base_time + timedelta(days=2),
            cutoff_time=base_time - timedelta(days=1),
            max_slots=5,
            is_active=True,
        )

        response = self.client.post(reverse("ngo:admin_ngo_delete", args=[ngo.id]))
        self.assertEqual(response.status_code, 302)
        ngo.refresh_from_db()
        self.assertTrue(ngo.is_active)

    def test_ongoing_activity_cannot_be_deactivated(self):
        ngo = NGO.objects.create(name="Ongoing NGO", is_active=True)
        base_time = timezone.now() - timedelta(hours=1)
        activity = NGOAvailability.objects.create(
            ngo=ngo,
            service_type="Ongoing Event",
            description="Current",
            location="Test",
            service_date=base_time,
            cutoff_time=base_time - timedelta(days=1),
            max_slots=5,
            is_active=True,
        )

        response = self.client.post(reverse("ngo:admin_activity_delete", args=[activity.id]))
        self.assertEqual(response.status_code, 302)
        activity.refresh_from_db()
        self.assertTrue(activity.is_active)

    def test_completed_activity_allows_ngo_deactivation(self):
        ngo = NGO.objects.create(name="Completed NGO", is_active=True)
        base_time = timezone.now() - timedelta(days=2)
        NGOAvailability.objects.create(
            ngo=ngo,
            service_type="Completed Event",
            description="Done",
            location="Test",
            service_date=base_time,
            cutoff_time=base_time - timedelta(days=3),
            max_slots=5,
            is_active=True,
        )

        response = self.client.post(reverse("ngo:admin_ngo_delete", args=[ngo.id]))
        self.assertEqual(response.status_code, 302)
        ngo.refresh_from_db()
        self.assertFalse(ngo.is_active)


@override_settings(INTERNAL_API_TOKEN="secure-admin-token")
class AdminNgoApiSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = get_user_model().objects.create_user(
            username="apiadmin",
            password="test-pass-123",
            is_staff=True,
        )
        NGO.objects.create(name="API NGO", is_active=True)

    def test_admin_api_requires_login(self):
        response = self.client.get(reverse("ngo:admin_ngo_api"))
        self.assertEqual(response.status_code, 302)

    def test_admin_api_requires_token(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("ngo:admin_ngo_api"))
        self.assertEqual(response.status_code, 401)

    def test_admin_api_rejects_invalid_token(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("ngo:admin_ngo_api"),
            HTTP_X_API_TOKEN="wrong-token",
        )
        self.assertEqual(response.status_code, 401)

    def test_admin_api_returns_json_for_valid_token(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("ngo:admin_ngo_api"),
            HTTP_X_API_TOKEN="secure-admin-token",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertContains(response, "API NGO")


class RestApiTests(TestCase):
    def setUp(self):
        base_time = timezone.now()
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            username="rest-admin",
            password="test-pass-123",
            is_staff=True,
        )
        self.employee = get_user_model().objects.create_user(
            username="rest-employee",
            password="test-pass-123",
        )
        self.ngo = NGO.objects.create(
            name="Bright Future",
            description="Education support",
            contact_email="hello@brightfuture.org",
            contact_phone="+60123456789",
            is_active=True,
        )
        self.activity = NGOAvailability.objects.create(
            ngo=self.ngo,
            service_type="Tutoring",
            description="Weekend tutoring session",
            location="Kuala Lumpur",
            service_date=base_time + timedelta(days=7),
            cutoff_time=base_time + timedelta(days=3),
            max_slots=2,
            is_active=True,
        )

    def test_admin_can_list_ngos_in_v1_api(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/ngos/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_employee_cannot_access_admin_ngo_api(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/ngos/")
        self.assertEqual(response.status_code, 403)

    def test_employee_can_filter_activities(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/activities/?location=Kuala%20Lumpur")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["ngo_name"], "Bright Future")

    def test_employee_can_register_with_json(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            "/api/v1/registrations/",
            {"activity_id": self.activity.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Registration.objects.filter(employee=self.employee, activity=self.activity).exists()
        )

    def test_registration_validation_blocks_duplicate_submission(self):
        Registration.objects.create(employee=self.employee, activity=self.activity)
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            "/api/v1/registrations/",
            {"activity_id": self.activity.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("activity_id", response.json())

    def test_employee_can_cancel_registration_with_delete(self):
        Registration.objects.create(employee=self.employee, activity=self.activity)
        self.client.force_authenticate(user=self.employee)
        response = self.client.delete(f"/api/v1/registrations/{self.activity.id}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Registration.objects.filter(employee=self.employee, activity=self.activity).exists()
        )

    def test_v2_activities_returns_simplified_payload(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v2/activities/")
        self.assertEqual(response.status_code, 200)
        first = response.json()["results"][0]
        self.assertEqual(set(first.keys()), {"id", "ngo", "service_type", "location", "service_date"})


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class NgoCachingTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_ngo_listing_cache_returns_stale_data_until_invalidated(self):
        NGO.objects.create(name="Cached NGO", is_active=True)
        first = ActivityService.list_ngos_admin()
        self.assertEqual(len(first), 1)

        NGO.objects.create(name="Fresh NGO", is_active=True)
        second = ActivityService.list_ngos_admin()
        self.assertEqual(len(second), 1)

        ActivityService.create_ngo({"name": "Third NGO"})
        refreshed = ActivityService.list_ngos_admin()
        self.assertEqual(len(refreshed), 3)
