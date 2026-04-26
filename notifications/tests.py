from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from ngo.models import NGO, NGOAvailability
from notifications.models import AttendanceRecord, NotificationJob, QRCheckInSession
from registrations.models import Registration


class NotificationQueueTests(TestCase):
    def setUp(self):
        self.client.force_login(
            get_user_model().objects.create_user(
                username="notify-admin",
                password="test-pass-123",
                is_staff=True,
            )
        )
        base_time = timezone.now()
        ngo = NGO.objects.create(name="Reminder NGO", is_active=True)
        self.activity = NGOAvailability.objects.create(
            ngo=ngo,
            service_type="Food Packing",
            description="Pack food boxes",
            location="Cyberjaya",
            service_date=base_time + timedelta(days=6),
            cutoff_time=base_time + timedelta(days=2),
            max_slots=10,
            is_active=True,
        )

    @patch("notifications.views.process_broadcast_job.delay")
    def test_broadcast_is_queued_to_celery(self, mock_delay):
        response = self.client.post(
            reverse("notifications:broadcast"),
            {"audience": "employees", "message": "Please check the new update."},
        )
        self.assertEqual(response.status_code, 302)
        job = NotificationJob.objects.get(job_type="broadcast")
        self.assertEqual(job.status, "Queued")
        mock_delay.assert_called_once_with(job.id)

    @patch("notifications.views.process_activity_reminder.delay")
    def test_immediate_reminder_is_queued_to_celery(self, mock_delay):
        response = self.client.post(
            reverse("notifications:schedule"),
            {"activity_id": self.activity.id},
        )
        self.assertEqual(response.status_code, 302)
        job = NotificationJob.objects.get(job_type="reminder")
        self.assertEqual(job.activity, self.activity)
        mock_delay.assert_called_once_with(job.id)

    def test_periodic_schedule_is_saved_to_beat(self):
        response = self.client.post(
            reverse("notifications:schedule"),
            {"activity_id": self.activity.id, "intervals": ["3", "1"]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PeriodicTask.objects.filter(name=f"Reminder-{self.activity.id}-3d").exists())
        self.assertTrue(PeriodicTask.objects.filter(name=f"Reminder-{self.activity.id}-1d").exists())


class RealQrCheckInTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="qr-admin",
            password="test-pass-123",
            is_staff=True,
        )
        self.employee = get_user_model().objects.create_user(
            username="qr-employee",
            password="test-pass-123",
            email="employee@example.com",
        )
        base_time = timezone.now()
        ngo = NGO.objects.create(name="QR NGO", is_active=True)
        self.activity = NGOAvailability.objects.create(
            ngo=ngo,
            service_type="Beach Cleaning",
            description="Clean-up event",
            location="Melaka",
            service_date=base_time + timedelta(minutes=5),
            cutoff_time=base_time - timedelta(days=1),
            max_slots=5,
            is_active=True,
        )
        Registration.objects.create(employee=self.employee, activity=self.activity)

    def test_admin_can_create_and_activate_qr_session(self):
        self.client.force_login(self.admin)
        create_response = self.client.post(
            reverse("notifications:create_qr_session"),
            {"activity_id": self.activity.id},
        )
        self.assertEqual(create_response.status_code, 201)
        session = QRCheckInSession.objects.get(activity=self.activity)
        self.assertFalse(session.is_live)

        activate_response = self.client.post(
            reverse("notifications:activate_qr_session", args=[session.id]),
        )
        self.assertEqual(activate_response.status_code, 200)
        session.refresh_from_db()
        self.assertTrue(session.is_live)

    def test_registered_employee_can_check_in_once(self):
        session = QRCheckInSession.objects.create(activity=self.activity, is_live=True)
        self.client.force_login(self.employee)
        response = self.client.post(reverse("notifications:confirm_employee_checkin", args=[session.token]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AttendanceRecord.objects.filter(session=session, employee=self.employee).exists())

        second_response = self.client.post(reverse("notifications:confirm_employee_checkin", args=[session.token]))
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(AttendanceRecord.objects.filter(session=session, employee=self.employee).count(), 1)

    def test_qr_page_only_lists_same_day_registered_activities(self):
        future_ngo = NGO.objects.create(name="Future NGO", is_active=True)
        future_activity = NGOAvailability.objects.create(
            ngo=future_ngo,
            service_type="Future Event",
            description="Future",
            location="KL",
            service_date=timezone.now() + timedelta(days=1),
            cutoff_time=timezone.now() - timedelta(days=1),
            max_slots=5,
            is_active=True,
        )
        Registration.objects.create(employee=self.employee, activity=future_activity)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("notifications:qr_checkin"))
        self.assertContains(response, "Beach Cleaning")
        self.assertNotContains(response, "Future Event")

    def test_qr_session_cannot_be_created_after_grace_window(self):
        expired_ngo = NGO.objects.create(name="Expired NGO", is_active=True)
        expired_activity = NGOAvailability.objects.create(
            ngo=expired_ngo,
            service_type="Expired Event",
            description="Expired",
            location="Johor",
            service_date=timezone.now() - timedelta(minutes=20),
            cutoff_time=timezone.now() - timedelta(days=1),
            max_slots=5,
            is_active=True,
        )
        Registration.objects.create(employee=self.employee, activity=expired_activity)

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("notifications:create_qr_session"),
            {"activity_id": expired_activity.id},
        )
        self.assertEqual(response.status_code, 400)
