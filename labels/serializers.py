from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from prep.models import PrepItem
from stores.models import Department, Printer, Store

from .models import Label, PrintJob, PrintJobItem


class LabelSerializer(serializers.ModelSerializer):
    prep_task_id = serializers.IntegerField(source="prep_task.id", read_only=True)

    class Meta:
        model = Label
        fields = [
            "id",
            "prep_task",
            "prep_task_id",
            "label_title",
            "label_body",
            "ai_generated_text",
            "qr_payload",
            "paper_size",
            "rendered_html",
            "title",
            "item_name",
            "payload",
            "html_preview",
            "prepared_at_text",
            "use_by_text",
            "prepared_by_text",
            "station_text",
            "quantity_text",
            "batch_code_text",
            "allergens_text",
            "notes_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "prep_task_id"]


class PrintJobItemSerializer(serializers.ModelSerializer):
    label = LabelSerializer(read_only=True)
    label_id = serializers.PrimaryKeyRelatedField(
        source="label",
        queryset=Label.objects.all(),
        write_only=True,
    )

    class Meta:
        model = PrintJobItem
        fields = [
            "id",
            "print_job",
            "label",
            "label_id",
            "copies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "label"]


class PrintJobSerializer(serializers.ModelSerializer):
    items = PrintJobItemSerializer(many=True, read_only=True)
    printer_name = serializers.CharField(source="printer.name", read_only=True)
    requested_by_username = serializers.CharField(source="requested_by.username", read_only=True)

    class Meta:
        model = PrintJob
        fields = [
            "id",
            "printer",
            "printer_name",
            "requested_by",
            "requested_by_username",
            "status",
            "error_message",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requested_by",
            "requested_by_username",
            "printer_name",
            "items",
            "created_at",
            "updated_at",
        ]


class PrintJobItemCreateSerializer(serializers.ModelSerializer):
    label = serializers.PrimaryKeyRelatedField(queryset=Label.objects.all())

    class Meta:
        model = PrintJobItem
        fields = ["label", "copies"]

    def validate_copies(self, value):
        if value is None:
            return 1
        if value < 1:
            raise serializers.ValidationError("Copies must be at least 1.")
        return value


class PrintJobCreateSerializer(serializers.ModelSerializer):
    items = PrintJobItemCreateSerializer(many=True, required=False)

    class Meta:
        model = PrintJob
        fields = [
            "id",
            "printer",
            "status",
            "error_message",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_status(self, value):
        allowed_statuses = {
            PrintJob.STATUS_QUEUED,
            PrintJob.STATUS_SENT,
            PrintJob.STATUS_PRINTED,
            PrintJob.STATUS_FAILED,
        }
        if value not in allowed_statuses:
            raise serializers.ValidationError("Invalid print job status.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["requested_by"] = request.user

        print_job = PrintJob.objects.create(**validated_data)

        for item_data in items_data:
            PrintJobItem.objects.create(
                print_job=print_job,
                **item_data,
            )

        return print_job

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PrintJobItem.objects.create(
                    print_job=instance,
                    **item_data,
                )

        return instance


class OneClickPrintRequestSerializer(serializers.Serializer):
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
    )
    prep_item = serializers.PrimaryKeyRelatedField(queryset=PrepItem.objects.all())
    printer = serializers.PrimaryKeyRelatedField(queryset=Printer.objects.all())

    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    unit = serializers.CharField(required=False, allow_blank=True, default="each")
    copies = serializers.IntegerField(required=False, min_value=1, default=1)

    prepared_at = serializers.CharField(required=False, allow_blank=True)
    paper_size = serializers.CharField(required=False, allow_blank=True, default="4x2")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    batch_code = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.CharField(required=False, allow_blank=True)

    def validate_prepared_at(self, value):
        if value in (None, ""):
            return None
        dt = parse_datetime(value)
        if dt is None:
            raise serializers.ValidationError(
                "prepared_at must be a valid ISO-8601 datetime string."
            )
        return dt

    def validate_paper_size(self, value):
        normalized = (value or "4x2").strip().lower().replace(" ", "")
        allowed = {"4x2", "4×2", "3x2", "3×2", "2x1", "2×1"}
        if normalized not in allowed:
            raise serializers.ValidationError("paper_size must be one of: 4x2, 3x2, 2x1.")
        return normalized.replace("×", "x")

    def validate(self, attrs):
        store = attrs["store"]
        department = attrs.get("department")
        prep_item = attrs["prep_item"]
        printer = attrs["printer"]

        prep_item_store = getattr(prep_item, "store_id", None)
        if prep_item_store is not None and prep_item_store != store.id:
            raise serializers.ValidationError(
                {"prep_item": "Selected prep item does not belong to the selected store."}
            )

        prep_item_department = getattr(prep_item, "department_id", None)
        if department is not None and prep_item_department is not None:
            if prep_item_department != department.id:
                raise serializers.ValidationError(
                    {"prep_item": "Selected prep item does not belong to the selected department."}
                )

        printer_store = getattr(printer, "store_id", None)
        if printer_store is not None and printer_store != store.id:
            raise serializers.ValidationError(
                {"printer": "Selected printer does not belong to the selected store."}
            )

        attrs["unit"] = (attrs.get("unit") or "each").strip() or "each"
        attrs["notes"] = (attrs.get("notes") or "").strip()
        attrs["batch_code"] = (attrs.get("batch_code") or "").strip()
        attrs["status"] = (attrs.get("status") or "").strip()

        return attrs