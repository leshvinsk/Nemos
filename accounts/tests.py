from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class CsrfFlowTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_user(
            username="alice",
            password="test-pass-123",
        )

    def test_login_page_sets_csrf_cookie_and_form_token(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        self.assertContains(response, 'name="csrfmiddlewaretoken"', html=False)

    def test_login_post_without_csrf_is_rejected(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": "test-pass-123"},
        )
        self.assertEqual(response.status_code, 403)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_post_with_csrf_succeeds(self):
        self.client.force_login(self.user)
        self.client.get(reverse("ngo:activity_list"))
        csrf_token = self.client.cookies["csrftoken"].value
        response = self.client.post(
            reverse("accounts:logout"),
            {"csrfmiddlewaretoken": csrf_token},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:login"))
