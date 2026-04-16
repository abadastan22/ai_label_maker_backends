from rest_framework import serializers

from labels.models import Label, PrintJob, PrintJobItem

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
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "prep_task_id",
        ]


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
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "label",
        ]


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
        fields = [
            "label",
            "copies",
        ]

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
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

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