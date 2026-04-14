from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from stores.models import Store, Department, Printer
from prep.models import PrepItem, PrepTask
from labels.models import PrintJob, PrintJobItem
from labels.services import build_label_from_prep_task

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data for AI Label Maker backend"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding demo data..."))

        # -------------------------
        # Users
        # -------------------------
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "System",
                "last_name": "Admin",
            },
        )
        admin_user.email = "admin@example.com"
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.first_name = "System"
        admin_user.last_name = "Admin"
        admin_user.set_password("Password123!")
        admin_user.save()

        manager_user, _ = User.objects.get_or_create(
            username="manager1",
            defaults={
                "email": "manager1@example.com",
                "is_staff": True,
                "first_name": "Store",
                "last_name": "Manager",
            },
        )
        manager_user.email = "manager1@example.com"
        manager_user.is_staff = True
        manager_user.first_name = "Store"
        manager_user.last_name = "Manager"
        manager_user.set_password("Password123!")
        manager_user.save()

        prep_user, _ = User.objects.get_or_create(
            username="prep1",
            defaults={
                "email": "prep1@example.com",
                "is_staff": False,
                "first_name": "Prep",
                "last_name": "Associate",
            },
        )
        prep_user.email = "prep1@example.com"
        prep_user.is_staff = False
        prep_user.first_name = "Prep"
        prep_user.last_name = "Associate"
        prep_user.set_password("Password123!")
        prep_user.save()

        # Optional: attach role groups if they already exist
        for username, group_names in {
            "manager1": ["Manager"],
            "prep1": ["Prep Associate"],
        }.items():
            user = User.objects.get(username=username)
            for group_name in group_names:
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                except Group.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Group '{group_name}' does not exist yet; skipping assignment.")
                    )

        # -------------------------
        # Stores
        # -------------------------
        tampa_store, _ = Store.objects.update_or_create(
            code="TMP001",
            defaults={
                "name": "Tampa Store",
                "address": "123 Main St, Tampa, FL",
                "is_active": True,
            },
        )

        orlando_store, _ = Store.objects.update_or_create(
            code="ORL001",
            defaults={
                "name": "Orlando Store",
                "address": "456 Central Ave, Orlando, FL",
                "is_active": True,
            },
        )

        # -------------------------
        # Departments
        # -------------------------
        tampa_deli, _ = Department.objects.update_or_create(
            store=tampa_store,
            name="Deli",
            defaults={"code": "DELI", "is_active": True},
        )
        tampa_bakery, _ = Department.objects.update_or_create(
            store=tampa_store,
            name="Bakery",
            defaults={"code": "BAK", "is_active": True},
        )
        orlando_deli, _ = Department.objects.update_or_create(
            store=orlando_store,
            name="Deli",
            defaults={"code": "DELI", "is_active": True},
        )
        orlando_produce, _ = Department.objects.update_or_create(
            store=orlando_store,
            name="Produce",
            defaults={"code": "PROD", "is_active": True},
        )

        # -------------------------
        # Printers
        # -------------------------
        printer_1, _ = Printer.objects.update_or_create(
            store=tampa_store,
            name="Smart Label Printer 620 (Copy 1)",
            defaults={
                "description": "Primary deli label printer",
                "driver_type": "mock_file",
                "ip_address": "192.168.1.50",
                "port": 9100,
                "device_name": "",
                "paper_size": "4x2",
                "dpi": 300,
                "connection_options": {"timeout": 10},
                "is_default": True,
                "is_active": True,
            },
        )

        printer_2, _ = Printer.objects.update_or_create(
            store=tampa_store,
            name="Bakery Zebra",
            defaults={
                "description": "Bakery Zebra network printer",
                "driver_type": "zpl",
                "ip_address": "192.168.1.51",
                "port": 9100,
                "device_name": "",
                "paper_size": "3x2",
                "dpi": 203,
                "connection_options": {"timeout": 10},
                "is_default": False,
                "is_active": True,
            },
        )

        printer_3, _ = Printer.objects.update_or_create(
            store=orlando_store,
            name="Smart Label Printer 620",
            defaults={
                "description": "Produce area label printer",
                "driver_type": "raw_tcp",
                "ip_address": "192.168.2.50",
                "port": 9100,
                "device_name": "",
                "paper_size": "4x2",
                "dpi": 300,
                "connection_options": {"timeout": 10},
                "is_default": True,
                "is_active": True,
            },
        )

        preview_printer, _ = Printer.objects.update_or_create(
            store=tampa_store,
            name="Preview Printer",
            defaults={
                "description": "HTML preview-only printer",
                "driver_type": "html_preview",
                "ip_address": None,
                "port": 9100,
                "device_name": "",
                "paper_size": "4x2",
                "dpi": 203,
                "connection_options": {},
                "is_default": False,
                "is_active": True,
            },
        )

        pdf_printer, _ = Printer.objects.update_or_create(
            store=orlando_store,
            name="PDF Export Printer",
            defaults={
                "description": "PDF output generator",
                "driver_type": "pdf_file",
                "ip_address": None,
                "port": 9100,
                "device_name": "",
                "paper_size": "4x2",
                "dpi": 203,
                "connection_options": {},
                "is_default": False,
                "is_active": True,
            },
        )

        windows_printer, _ = Printer.objects.update_or_create(
            store=tampa_store,
            name="Windows Office Printer",
            defaults={
                "description": "Windows spooler printer",
                "driver_type": "windows_spooler",
                "ip_address": None,
                "port": 9100,
                "device_name": "Brother QL-820NWB",
                "paper_size": "3x2",
                "dpi": 300,
                "connection_options": {},
                "is_default": False,
                "is_active": True,
            },
        )

        # -------------------------
        # Prep Items
        # -------------------------
        items = [
            {
                "store": tampa_store,
                "department": tampa_deli,
                "sku": "SKU-1001",
                "name": "Chicken Salad",
                "description": "Fresh deli chicken salad",
                "ingredients": "Chicken, mayo, celery, pepper",
                "allergen_info": "Egg",
                "shelf_life_hours": 24,
                "storage_notes": "Keep refrigerated",
                "is_active": True,
            },
            {
                "store": tampa_store,
                "department": tampa_deli,
                "sku": "SKU-1002",
                "name": "Tuna Salad",
                "description": "Fresh deli tuna salad",
                "ingredients": "Tuna, mayo, celery",
                "allergen_info": "Fish, Egg",
                "shelf_life_hours": 24,
                "storage_notes": "Keep refrigerated",
                "is_active": True,
            },
            {
                "store": tampa_store,
                "department": tampa_bakery,
                "sku": "SKU-2001",
                "name": "Blueberry Muffin",
                "description": "Bakery fresh muffin",
                "ingredients": "Flour, eggs, milk, blueberries",
                "allergen_info": "Wheat, Egg, Milk",
                "shelf_life_hours": 12,
                "storage_notes": "Room temp display",
                "is_active": True,
            },
            {
                "store": tampa_store,
                "department": tampa_bakery,
                "sku": "SKU-2002",
                "name": "Banana Bread",
                "description": "Fresh baked banana bread",
                "ingredients": "Flour, banana, egg, butter",
                "allergen_info": "Wheat, Egg, Milk",
                "shelf_life_hours": 18,
                "storage_notes": "Room temp display",
                "is_active": True,
            },
            {
                "store": orlando_store,
                "department": orlando_deli,
                "sku": "SKU-3001",
                "name": "Pasta Salad",
                "description": "Cold pasta salad",
                "ingredients": "Pasta, peppers, dressing",
                "allergen_info": "Wheat",
                "shelf_life_hours": 24,
                "storage_notes": "Keep refrigerated",
                "is_active": True,
            },
            {
                "store": orlando_store,
                "department": orlando_produce,
                "sku": "SKU-4001",
                "name": "Fruit Bowl",
                "description": "Mixed cut fruit",
                "ingredients": "Melon, pineapple, grape, strawberry",
                "allergen_info": "",
                "shelf_life_hours": 8,
                "storage_notes": "Keep refrigerated",
                "is_active": True,
            },
            {
                "store": orlando_store,
                "department": orlando_produce,
                "sku": "SKU-4002",
                "name": "Veggie Pack",
                "description": "Fresh cut vegetables",
                "ingredients": "Carrot, celery, cucumber",
                "allergen_info": "",
                "shelf_life_hours": 10,
                "storage_notes": "Keep refrigerated",
                "is_active": True,
            },
            {
                "store": tampa_store,
                "department": tampa_deli,
                "sku": "SKU-1003",
                "name": "Macaroni Salad",
                "description": "Creamy macaroni salad",
                "ingredients": "Pasta, mayo, celery",
                "allergen_info": "Wheat, Egg",
                "shelf_life_hours": 24,
                "storage_notes": "Keep refrigerated",
                "is_active": True,
            },
        ]

        prep_items = []
        for item_data in items:
            prep_item, _ = PrepItem.objects.update_or_create(
                store=item_data["store"],
                name=item_data["name"],
                defaults=item_data,
            )
            prep_items.append(prep_item)

        # -------------------------
        # Prep Tasks
        # -------------------------
        now = timezone.now()
        task_specs = [
            {
                "store": tampa_store,
                "department": tampa_deli,
                "prep_item": prep_items[0],
                "quantity": 5,
                "unit": "lbs",
                "prepared_by": prep_user,
                "prepared_at": now - timedelta(hours=1),
                "status": "pending",
                "notes": "Morning batch",
                "batch_code": "TMP-DEL-001",
            },
            {
                "store": tampa_store,
                "department": tampa_deli,
                "prep_item": prep_items[1],
                "quantity": 3,
                "unit": "lbs",
                "prepared_by": prep_user,
                "prepared_at": now - timedelta(hours=2),
                "status": "printed",
                "notes": "Lunch prep",
                "batch_code": "TMP-DEL-002",
            },
            {
                "store": tampa_store,
                "department": tampa_bakery,
                "prep_item": prep_items[2],
                "quantity": 24,
                "unit": "each",
                "prepared_by": manager_user,
                "prepared_at": now - timedelta(hours=3),
                "status": "completed",
                "notes": "Display stock",
                "batch_code": "TMP-BAK-001",
            },
            {
                "store": tampa_store,
                "department": tampa_bakery,
                "prep_item": prep_items[3],
                "quantity": 10,
                "unit": "loaf",
                "prepared_by": manager_user,
                "prepared_at": now - timedelta(hours=4),
                "status": "discarded",
                "notes": "Damaged batch",
                "batch_code": "TMP-BAK-002",
            },
            {
                "store": orlando_store,
                "department": orlando_deli,
                "prep_item": prep_items[4],
                "quantity": 4,
                "unit": "lbs",
                "prepared_by": prep_user,
                "prepared_at": now - timedelta(hours=1, minutes=30),
                "status": "pending",
                "notes": "Afternoon prep",
                "batch_code": "ORL-DEL-001",
            },
            {
                "store": orlando_store,
                "department": orlando_produce,
                "prep_item": prep_items[5],
                "quantity": 12,
                "unit": "bowls",
                "prepared_by": prep_user,
                "prepared_at": now - timedelta(minutes=45),
                "status": "pending",
                "notes": "Front display",
                "batch_code": "ORL-PRO-001",
            },
        ]

        prep_tasks = []
        for spec in task_specs:
            prep_task, _ = PrepTask.objects.update_or_create(
                batch_code=spec["batch_code"],
                defaults=spec,
            )
            prep_tasks.append(prep_task)

        # -------------------------
        # Labels
        # -------------------------
        labels = []
        for task in prep_tasks:
            label = build_label_from_prep_task(task, paper_size="4x2")
            labels.append(label)

        # -------------------------
        # Demo Print Jobs
        # -------------------------
        demo_job_specs = [
            {
                "job_key": "DEMO-MOCK-001",
                "printer": printer_1,
                "requested_by": manager_user,
                "status": "queued",
                "items": [
                    {"label": labels[0], "copies": 2},
                    {"label": labels[1], "copies": 1},
                ],
            },
            {
                "job_key": "DEMO-RAWTCP-001",
                "printer": printer_3,
                "requested_by": prep_user,
                "status": "printed",
                "items": [
                    {"label": labels[4], "copies": 3},
                ],
            },
            {
                "job_key": "DEMO-ZPL-001",
                "printer": printer_2,
                "requested_by": manager_user,
                "status": "queued",
                "items": [
                    {"label": labels[2], "copies": 2},
                ],
            },
            {
                "job_key": "DEMO-PREVIEW-001",
                "printer": preview_printer,
                "requested_by": manager_user,
                "status": "queued",
                "items": [
                    {"label": labels[3], "copies": 1},
                ],
            },
            {
                "job_key": "DEMO-PDF-001",
                "printer": pdf_printer,
                "requested_by": prep_user,
                "status": "queued",
                "items": [
                    {"label": labels[5], "copies": 2},
                ],
            },
            {
                "job_key": "DEMO-WIN-001",
                "printer": windows_printer,
                "requested_by": manager_user,
                "status": "queued",
                "items": [
                    {"label": labels[0], "copies": 1},
                ],
            },
        ]

        for job_spec in demo_job_specs:
            job_key = job_spec["job_key"]

            # Remove old job with same demo key if your model has no dedicated key field.
            # We use error_message as a seed marker to keep it simple.
            PrintJob.objects.filter(error_message=f"seed:{job_key}").delete()

            print_job = PrintJob.objects.create(
                printer=job_spec["printer"],
                requested_by=job_spec["requested_by"],
                status=job_spec["status"],
                error_message=f"seed:{job_key}",
            )

            for item in job_spec["items"]:
                PrintJobItem.objects.create(
                    print_job=print_job,
                    label=item["label"],
                    copies=item["copies"],
                )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write(self.style.SUCCESS("Admin: admin / Password123!"))
        self.stdout.write(self.style.SUCCESS("Manager: manager1 / Password123!"))
        self.stdout.write(self.style.SUCCESS("Prep: prep1 / Password123!"))