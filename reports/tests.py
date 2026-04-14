from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from stores.models import Store, Department
from prep.models import PrepItem, PrepTask

User = get_user_model()


class ReportsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reportuser",
            password="Password123!",
            is_staff=True,
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "reportuser", "password": "Password123!"},
            format="json",
        )
        token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        store = Store.objects.create(name="Store A", code="STA")
        department = Department.objects.create(store=store, name="Bakery", code="BAK")
        item = PrepItem.objects.create(
            store=store,
            department=department,
            name="Bread",
            shelf_life_hours=12,
        )

        PrepTask.objects.create(
            store=store,
            department=department,
            prep_item=item,
            quantity=10,
            status="pending",
        )

    def test_daily_prep_summary(self):
        response = self.client.get("/api/reports/daily-prep-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)