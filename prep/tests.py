from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from stores.models import Store, Department
from prep.models import PrepItem, PrepTask
from labels.models import Label

User = get_user_model()


class PrepTaskTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staff1",
            password="Password123!",
            is_staff=True,
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "staff1", "password": "Password123!"},
            format="json",
        )
        self.token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.store = Store.objects.create(name="Store A", code="STA")
        self.department = Department.objects.create(store=self.store, name="Deli", code="DELI")
        self.prep_item = PrepItem.objects.create(
            store=self.store,
            department=self.department,
            name="Chicken Salad",
            sku="SKU1",
            shelf_life_hours=24,
        )

    def test_create_prep_task_creates_label(self):
        response = self.client.post(
            "/api/prep-tasks/",
            {
                "store": self.store.id,
                "department": self.department.id,
                "prep_item": self.prep_item.id,
                "quantity": 3,
                "unit": "lbs",
                "notes": "Batch created",
                "batch_code": "B001",
                "status": "pending",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        prep_task = PrepTask.objects.get(id=response.data["id"])
        self.assertIsNotNone(prep_task.expires_at)
        self.assertTrue(Label.objects.filter(prep_task=prep_task).exists())