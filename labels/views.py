import logging
import traceback

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from prep.models import PrepTask

from .exceptions import PrinterDispatchError
from .models import Label, PrintJob, PrintJobItem
from .serializers import (
    LabelSerializer,
    OneClickPrintRequestSerializer,
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
        "title",
        "item_name",
        "payload",
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
        if self.action in ["create", "update", "partial_update"]:
            return PrintJobCreateSerializer
        return PrintJobSerializer

    def filter_queryset(self, queryset):
        if self.action == "one_click_print":
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

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, pk=None):
        job = self.get_object()

        return Response(
            {
                "id": job.id,
                "status": job.status,
                "error_message": job.error_message,
                "printer": job.printer_id,
                "printer_name": job.printer.name if job.printer else None,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            },
            status=status.HTTP_200_OK,
        )
    
    @action(detail=True, methods=["post"])
    def mark_printed(self, request, pk=None):
        job = self.get_object()
        job.status = PrintJob.STATUS_PRINTED
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])
        return Response({"detail": "Print job marked as printed."}, status=status.HTTP_200_OK)
    
    @action(
        detail=False,
        methods=["post"],
        url_path="preview-label",
        filter_backends=[],
        pagination_class=None,
    )
        
    def preview_label(self, request):
        request_serializer = OneClickPrintRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        prep_item = data["prep_item"]

        title = prep_item.name
        prepared_at = data.get("prepared_at")
        quantity_text = f"{data.get('quantity', 1)} {data.get('unit', 'each')}".strip()

        use_by_text = ""
        if prepared_at and getattr(prep_item, "shelf_life_hours", None):
            from django.utils.timezone import localtime
            from datetime import timedelta

            use_by = prepared_at + timedelta(hours=prep_item.shelf_life_hours)
            use_by_text = localtime(use_by).strftime("%m/%d/%Y, %I:%M %p")

        from .services import render_label_html

        html = render_label_html(
            title=title,
            prepared_at_text=prepared_at.strftime("%m/%d/%Y, %I:%M %p") if prepared_at else "",
            use_by_text=use_by_text,
            prepared_by_text=request.user.get_full_name() or request.user.username,
            station_text=getattr(prep_item.department, "name", "") if prep_item.department else "",
            quantity_text=quantity_text,
            batch_code_text=data.get("batch_code", ""),
            allergens_text=getattr(prep_item, "allergen_info", "") or "",
            notes_text=data.get("notes", ""),
            paper_size=data.get("paper_size", "4x2"),
        )

        return Response(
            {
                "html": html,
                "paper_size": data.get("paper_size", "4x2"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def mark_failed(self, request, pk=None):
        job = self.get_object()
        error_message = request.data.get("error_message", "Unknown print failure")
        job.status = PrintJob.STATUS_FAILED
        job.error_message = error_message
        job.save(update_fields=["status", "error_message", "updated_at"])
        return Response({"detail": "Print job marked as failed."}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="one-click-print",
        filter_backends=[],
        pagination_class=None,
    )
    def one_click_print(self, request):
        request_serializer = OneClickPrintRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        try:
            with transaction.atomic():
                prep_task = PrepTask(
                    store=data["store"],
                    department=data.get("department"),
                    prep_item=data["prep_item"],
                    quantity=data.get("quantity", 1),
                    unit=data.get("unit", "each"),
                    prepared_by=request.user if request.user.is_authenticated else None,
                    prepared_at=data.get("prepared_at"),
                    notes=data.get("notes", ""),
                    batch_code=data.get("batch_code", ""),
                    status=data.get("status", "") or PrepTask.STATUS_PENDING,
                )
                prep_task._skip_auto_label_sync = True
                prep_task.save()

                label = build_label_from_prep_task(
                    prep_task=prep_task,
                    paper_size=data.get("paper_size", "4x2"),
                )

                print_job = PrintJob.objects.create(
                    printer=data["printer"],
                    requested_by=request.user if request.user.is_authenticated else None,
                    status=PrintJob.STATUS_QUEUED,
                )

                PrintJobItem.objects.create(
                    print_job=print_job,
                    label=label,
                    copies=data.get("copies", 1),
                )

            printer_service = PrinterService()
            dispatch_result = printer_service.dispatch_print_job(print_job)

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

        print_job = self.get_queryset().get(pk=print_job.pk)
        serializer = PrintJobSerializer(print_job, context={"request": request})

        return Response(
            {
                "detail": "One-click print completed.",
                "prep_task_id": prep_task.id,
                "label_id": label.id,
                "print_job_id": print_job.id,
                "dispatch_result": dispatch_result,
                "print_job": serializer.data,
            },
    status=status.HTTP_201_CREATED,
)