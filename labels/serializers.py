from django.db import transaction
from rest_framework import serializers
from prep.models import PrepItem
from django.utils.dateparse import parse_datetime

from .models import Label, PrintJob, PrintJobItem


class LabelSerializer(serializers.ModelSerializer):
    prep_item_name = serializers.CharField(source="prep_task.prep_item.name", read_only=True)

    class Meta:
        model = Label
        fields = "__all__"


class PrintJobItemSerializer(serializers.ModelSerializer):
    label_id = serializers.SerializerMethodField()
    label_title = serializers.SerializerMethodField()
    label_body = serializers.SerializerMethodField()
    paper_size = serializers.SerializerMethodField()

    class Meta:
        model = PrintJobItem
        fields = [
            "id",
            "print_job",
            "label",
            "label_id",
            "label_title",
            "label_body",
            "paper_size",
            "copies",
            "created_at",
            "updated_at",
        ]

    def get_label_id(self, obj):
        return obj.label.id if obj.label else None

    def get_label_title(self, obj):
        return obj.label.label_title if obj.label else None

    def get_label_body(self, obj):
        return obj.label.label_body if obj.label else None

    def get_paper_size(self, obj):
        return obj.label.paper_size if obj.label else None


class PrintJobSerializer(serializers.ModelSerializer):
    items = PrintJobItemSerializer(many=True, read_only=True)
    printer_name = serializers.SerializerMethodField()
    printer_ip = serializers.SerializerMethodField()
    requested_by_username = serializers.SerializerMethodField()

    class Meta:
        model = PrintJob
        fields = "__all__"

    def get_printer_name(self, obj):
        return obj.printer.name if obj.printer else None

    def get_printer_ip(self, obj):
        return obj.printer.ip_address if obj.printer else None

    def get_requested_by_username(self, obj):
        return obj.requested_by.username if obj.requested_by else None


class PrintJobCreateItemInputSerializer(serializers.Serializer):
    label = serializers.IntegerField(min_value=1)
    copies = serializers.IntegerField(min_value=1, default=1)


class PrintJobCreateSerializer(serializers.ModelSerializer):
    item_ids = PrintJobCreateItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = PrintJob
        fields = ["id", "printer", "status", "item_ids"]

    def validate_item_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one print job item is required.")

        label_ids = [item["label"] for item in value]
        found = set(Label.objects.filter(id__in=label_ids).values_list("id", flat=True))
        missing = sorted(set(label_ids) - found)
        if missing:
            raise serializers.ValidationError(f"Unknown label ids: {missing}")

        return value

    @transaction.atomic
    def create(self, validated_data):
        item_ids = validated_data.pop("item_ids", [])
        request = self.context["request"]

        if request.user and request.user.is_authenticated:
            validated_data["requested_by"] = request.user

        print_job = PrintJob.objects.create(**validated_data)

        for item in item_ids:
            PrintJobItem.objects.create(
                print_job=print_job,
                label_id=item["label"],
                copies=item.get("copies", 1),
            )

        return print_job

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
            raise serializers.ValidationError(
                "paper_size must be one of: 4x2, 3x2, 2x1."
            )
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