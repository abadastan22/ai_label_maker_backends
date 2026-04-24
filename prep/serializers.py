from rest_framework import serializers

from .models import PrepItem, PrepTask


class PrepItemSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = PrepItem
        fields = [
            "id",
            "store",
            "store_name",
            "department",
            "department_name",
            "sku",
            "name",
            "description",
            "ingredients",
            "allergen_info",
            "shelf_life_hours",
            "storage_notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "store_name",
            "department_name",
        ]


class PrepTaskSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    prep_item_name = serializers.CharField(source="prep_item.name", read_only=True)
    prepared_by_username = serializers.CharField(source="prepared_by.username", read_only=True)

    class Meta:
        model = PrepTask
        fields = [
            "id",
            "store",
            "store_name",
            "department",
            "department_name",
            "prep_item",
            "prep_item_name",
            "quantity",
            "unit",
            "prepared_by",
            "prepared_by_username",
            "prepared_at",
            "expires_at",
            "status",
            "notes",
            "batch_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "expires_at",
            "created_at",
            "updated_at",
            "store_name",
            "department_name",
            "prep_item_name",
            "prepared_by_username",
        ]


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
            "status",
            "notes",
            "batch_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["prepared_by"] = request.user
        return PrepTask.objects.create(**validated_data)