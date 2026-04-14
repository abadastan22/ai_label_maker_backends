from rest_framework import serializers

from .models import PrepItem, PrepTask


class PrepItemSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = PrepItem
        fields = "__all__"


class PrepTaskSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    prep_item_name = serializers.CharField(source="prep_item.name", read_only=True)
    prepared_by_username = serializers.CharField(source="prepared_by.username", read_only=True)

    class Meta:
        model = PrepTask
        fields = "__all__"
        read_only_fields = ("expires_at",)


class PrepTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrepTask
        fields = [
            "id",
            "store",
            "department",
            "prep_item",
            "quantity",
            "unit",
            "prepared_at",
            "notes",
            "batch_code",
            "status",
        ]

def create(self, validated_data):
    request = self.context["request"]
    if request.user and request.user.is_authenticated:
        validated_data.setdefault("prepared_by", request.user)

    prep_task = super().create(validated_data)
    build_label_from_prep_task(prep_task)
    return prep_task