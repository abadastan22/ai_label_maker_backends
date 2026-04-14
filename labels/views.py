import logging
import traceback

from django.db.models import Prefetch
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from prep.models import PrepTask
from .exceptions import PrinterDispatchError
from .models import Label, PrintJob, PrintJobItem
from .serializers import (
    LabelSerializer,
    PrintJobCreateSerializer,
    PrintJobSerializer,
)
from .services import PrinterService, build_label_from_prep_task

logger = logging.getLogger(__name__)


class LabelViewSet(viewsets.ModelViewSet):
    queryset = Label.objects.select_related("prep_task", "prep_task__prep_item").all()
    serializer_class = LabelSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["paper_size", "prep_task__store", "prep_task__department"]
    search_fields = [
        "label_title",
        "label_body",
        "ai_generated_text",
        "prep_task__prep_item__name",
    ]
    ordering_fields = ["created_at", "updated_at"]


class PrintJobViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["printer", "status"]
    search_fields = ["error_message", "printer__name", "requested_by__username"]
    ordering_fields = ["created_at", "updated_at", "status"]

    def get_queryset(self):
        return (
            PrintJob.objects
            .select_related("printer", "requested_by")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=PrintJobItem.objects.select_related("label"),
                )
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        current_action = getattr(self, "action", None)
        if current_action in ["create", "update", "partial_update"]:
            return PrintJobCreateSerializer
        return PrintJobSerializer

    def filter_queryset(self, queryset):
        current_action = getattr(self, "action", None)
        if current_action == "one_click_print":
            return queryset
        return super().filter_queryset(queryset)

    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_job(self, request, pk=None):
        job = self.get_object()
        printer_service = PrinterService()

        try:
            dispatch_result = printer_service.dispatch_print_job(job)
        except PrinterDispatchError as exc:
            logger.exception("Print job dispatch failed for print_job_id=%s", job.id)
            job.refresh_from_db()
            serializer = PrintJobSerializer(job, context={"request": request})
            return Response(
                {
                    "detail": "Print job dispatch failed.",
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                    "print_job": serializer.data,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception("Unexpected dispatch error for print_job_id=%s", job.id)
            return Response(
                {
                    "detail": "Unexpected print dispatch error.",
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                    "traceback": traceback.format_exc(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        refreshed_job = self.get_queryset().get(pk=job.pk)
        serializer = PrintJobSerializer(refreshed_job, context={"request": request})

        return Response(
            {
                "detail": "Print job dispatched successfully.",
                "dispatch_result": dispatch_result,
                "print_job": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def mark_printed(self, request, pk=None):
        job = self.get_object()
        job.status = PrintJob.STATUS_PRINTED
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])
        return Response(
            {"detail": "Print job marked as printed."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def mark_failed(self, request, pk=None):
        job = self.get_object()
        error_message = request.data.get("error_message", "Unknown print failure")
        job.status = PrintJob.STATUS_FAILED
        job.error_message = error_message
        job.save(update_fields=["status", "error_message", "updated_at"])
        return Response(
            {"detail": "Print job marked as failed."},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="one-click-print",
        filter_backends=[],
        pagination_class=None,
    )
    def one_click_print(self, request):
        payload = request.data

        prepared_at_raw = payload.get("prepared_at")
        prepared_at = None
        if prepared_at_raw:
            prepared_at = parse_datetime(prepared_at_raw)

            if prepared_at is None:
                return Response(
                    {"detail": "Invalid prepared_at format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if is_naive(prepared_at):
                prepared_at = make_aware(prepared_at)

        try:
            prep_task = PrepTask.objects.create(
                store_id=payload["store"],
                department_id=payload.get("department"),
                prep_item_id=payload["prep_item"],
                quantity=payload.get("quantity", 1),
                unit=payload.get("unit", "each"),
                prepared_by=request.user if request.user.is_authenticated else None,
                prepared_at=prepared_at,
                notes=payload.get("notes", ""),
                batch_code=payload.get("batch_code", ""),
                status=payload.get("status", PrepTask.STATUS_PENDING),
            )

            label = build_label_from_prep_task(
                prep_task=prep_task,
                paper_size=payload.get("paper_size", "4x2"),
            )

            print_job = PrintJob.objects.create(
                printer_id=payload["printer"],
                requested_by=request.user if request.user.is_authenticated else None,
                status=PrintJob.STATUS_QUEUED,
            )

            PrintJobItem.objects.create(
                print_job=print_job,
                label=label,
                copies=payload.get("copies", 1),
            )

            printer_service = PrinterService()
            dispatch_result = printer_service.dispatch_print_job(print_job)

        except KeyError as exc:
            return Response(
                {"detail": f"Missing required field: {exc.args[0]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PrinterDispatchError as exc:
            logger.exception(
                "Print dispatch failed for print_job_id=%s",
                locals().get("print_job").id if "print_job" in locals() else None,
            )

            if "print_job" in locals():
                print_job.refresh_from_db()
                serializer = PrintJobSerializer(print_job, context={"request": request})
                return Response(
                    {
                        "detail": "Print job dispatch failed.",
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                        "print_job": serializer.data,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {
                    "detail": "Print job dispatch failed.",
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception("Unexpected one-click print error.")
            return Response(
                {
                    "detail": "Unexpected one-click print error.",
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                    "traceback": traceback.format_exc(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        print_job.refresh_from_db()
        serializer = PrintJobSerializer(print_job, context={"request": request})

        return Response(
            {
                "detail": "One-click print completed.",
                "prep_task_id": prep_task.id,
                "label_id": label.id,
                "dispatch_result": dispatch_result,
                "print_job": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )