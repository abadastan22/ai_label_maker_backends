from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from prep.models import PrepTask
from labels.models import PrintJob, PrintJobItem


class DailyPrepSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()

        qs = (
            PrepTask.objects.filter(prepared_at__date=today)
            .values("store__id", "store__name", "status")
            .annotate(
                total_tasks=Count("id"),
                total_quantity=Coalesce(Sum("quantity"), 0),
            )
            .order_by("store__name", "status")
        )

        return Response(list(qs))


class ExpiringItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        next_24h = now + timezone.timedelta(hours=24)

        qs = (
            PrepTask.objects.filter(
                status__in=["pending", "printed", "completed"],
                expires_at__isnull=False,
                expires_at__range=(now, next_24h),
            )
            .select_related("store", "department", "prep_item", "prepared_by")
            .order_by("expires_at")
        )

        data = [
            {
                "id": task.id,
                "store": task.store.name,
                "department": task.department.name if task.department else None,
                "prep_item": task.prep_item.name,
                "quantity": task.quantity,
                "unit": task.unit,
                "prepared_by": task.prepared_by.username if task.prepared_by else None,
                "prepared_at": task.prepared_at,
                "expires_at": task.expires_at,
                "status": task.status,
            }
            for task in qs
        ]
        return Response(data)


class WasteSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            PrepTask.objects.filter(status="discarded")
            .values("store__id", "store__name", "department__id", "department__name")
            .annotate(
                discarded_tasks=Count("id"),
                discarded_quantity=Coalesce(Sum("quantity"), 0),
            )
            .order_by("store__name", "department__name")
        )

        return Response(list(qs))


class PrintActivitySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            PrintJob.objects.values("printer__id", "printer__name", "status")
            .annotate(total_jobs=Count("id"))
            .order_by("printer__name", "status")
        )

        return Response(list(qs))


class PrintCopiesSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            PrintJobItem.objects.values(
                "print_job__printer__id",
                "print_job__printer__name",
                "label__prep_task__store__id",
                "label__prep_task__store__name",
            )
            .annotate(total_copies=Coalesce(Sum("copies"), 0))
            .order_by("label__prep_task__store__name", "print_job__printer__name")
        )

        return Response(list(qs))