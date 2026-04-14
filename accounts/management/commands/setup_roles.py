from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from prep.models import PrepItem, PrepTask
from labels.models import Label, PrintJob, PrintJobItem
#from reports.models import Report  # adjust if you have this model


class Command(BaseCommand):
    help = "Create default user roles and assign permissions"

    def handle(self, *args, **kwargs):
        roles = [
            "Admin",
            "Store Manager",
            "Supervisor",
            "Prep Associate",
            #"Report Viewer",
        ]

        for role in roles:
            Group.objects.get_or_create(name=role)

        admin_group = Group.objects.get(name="Admin")
        store_manager_group = Group.objects.get(name="Store Manager")
        supervisor_group = Group.objects.get(name="Supervisor")
        prep_associate_group = Group.objects.get(name="Prep Associate")
        #report_viewer_group = Group.objects.get(name="Report Viewer")

        # Example permissions
        prepitem_ct = ContentType.objects.get_for_model(PrepItem)
        preptask_ct = ContentType.objects.get_for_model(PrepTask)
        label_ct = ContentType.objects.get_for_model(Label)
        printjob_ct = ContentType.objects.get_for_model(PrintJob)
        printjobitem_ct = ContentType.objects.get_for_model(PrintJobItem)
        #report_ct = ContentType.objects.get_for_model(Report)

        # Admin: all permissions
        admin_group.permissions.set(Permission.objects.all())

        # Store Manager: broad operational access
        store_manager_perms = Permission.objects.filter(
            content_type__in=[
                prepitem_ct,
                preptask_ct,
                label_ct,
                printjob_ct,
                printjobitem_ct,
                #report_ct,
            ]
        )
        store_manager_group.permissions.set(store_manager_perms)

        # Supervisor: manage prep + labels + view reports
        supervisor_perms = Permission.objects.filter(
            content_type__in=[
                prepitem_ct,
                preptask_ct,
                label_ct,
                printjob_ct,
                printjobitem_ct,
                #report_ct,
            ],
            codename__in=[
                "add_prepitem", "change_prepitem", "view_prepitem",
                "add_preptask", "change_preptask", "view_preptask",
                "add_label", "change_label", "view_label",
                "add_printjob", "change_printjob", "view_printjob",
                "add_printjobitem", "change_printjobitem", "view_printjobitem",
                #"view_report",
            ]
        )
        supervisor_group.permissions.set(supervisor_perms)

        # Prep Associate: limited prep + label access
        prep_associate_perms = Permission.objects.filter(
            codename__in=[
                "view_prepitem",
                "change_prepitem",
                "view_preptask",
                "change_preptask",
                "view_label",
                "add_printjob",
                "view_printjob",
                "add_printjobitem",
                "view_printjobitem",
            ]
        )
        prep_associate_group.permissions.set(prep_associate_perms)

        # Report Viewer: reports only
        # report_viewer_perms = Permission.objects.filter(
        #     content_type=report_ct,
        #     codename__in=["view_report"]
        # )
        # report_viewer_group.permissions.set(report_viewer_perms)

        self.stdout.write(self.style.SUCCESS("Roles and permissions created successfully."))