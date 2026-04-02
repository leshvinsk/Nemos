from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ngo.models import NGO, NGOAvailability


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

        self.client.post(reverse("ngo:admin_ngo_delete", args=[ngo.id]))
        self.client.post(reverse("ngo:admin_activity_delete", args=[activity.id]))

        ngo_page = self.client.get(reverse("ngo:admin_ngo_manage"))
        self.assertNotContains(ngo_page, "Hidden NGO")

        activity_page = self.client.get(reverse("ngo:admin_activity_manage"))
        self.assertNotContains(activity_page, "Hidden activity")
