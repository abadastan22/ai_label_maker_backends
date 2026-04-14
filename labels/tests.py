from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from stores.models import Store, Department, Printer
from prep.models import PrepItem, PrepTask
from labels.models import PrintJob
from labels.services import build_label_from_prep_task

User = get_user_model()


class PrintDispatchTests(APITestCase):
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
        self.printer = Printer.objects.create(
            store=self.store,
            name="Mock Printer",
            ip_address="127.0.0.1",
            port=9100,
            paper_size="4x2",
            is_default=True,
            is_active=True,
        )
        self.prep_item = PrepItem.objects.create(
            store=self.store,
            department=self.department,
            name="Chicken Salad",
            sku="SKU1",
            shelf_life_hours=24,
        )
        self.prep_task = PrepTask.objects.create(
            store=self.store,
            department=self.department,
            prep_item=self.prep_item,
            quantity=3,
            status="pending",
            prepared_by=self.user,
        )
        self.label = build_label_from_prep_task(self.prep_task)

    def test_dispatch_print_job(self):
        create_response = self.client.post(
            "/api/print-jobs/",
            {
                "printer": self.printer.id,
                "status": "queued",
                "item_ids": [{"label": self.label.id, "copies": 2}],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        job_id = create_response.data["id"]

        dispatch_response = self.client.post(f"/api/print-jobs/{job_id}/dispatch/")
        self.assertEqual(dispatch_response.status_code, status.HTTP_200_OK)

        job = PrintJob.objects.get(id=job_id)
        self.assertEqual(job.status, "sent")