from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import PrepItem, PrepTask
from .serializers import (
    PrepItemSerializer,
    PrepTaskSerializer,
    PrepTaskCreateSerializer,
)


class PrepItemViewSet(viewsets.ModelViewSet):
    queryset = PrepItem.objects.select_related("store", "department").all()
    serializer_class = PrepItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["store", "department", "is_active"]
    search_fields = ["name", "sku", "description", "ingredients", "allergen_info"]
    ordering_fields = ["name", "sku", "created_at", "updated_at"]


class PrepTaskViewSet(viewsets.ModelViewSet):
    queryset = PrepTask.objects.select_related(
        "store",
        "department",
        "prep_item",
        "prepared_by",
    ).all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ["store", "department", "prep_item", "status"]
    search_fields = ["prep_item__name", "batch_code", "notes"]
    ordering_fields = ["prepared_at", "expires_at", "created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PrepTaskCreateSerializer
        return PrepTaskSerializer