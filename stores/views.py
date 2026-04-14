from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Store, Department, Printer
from .serializers import StoreSerializer, DepartmentSerializer, PrinterSerializer


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code", "address"]
    ordering_fields = ["name", "code", "created_at"]


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("store").all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["store", "is_active"]
    search_fields = ["name", "code", "store__name"]
    ordering_fields = ["name", "code", "created_at"]


class PrinterViewSet(viewsets.ModelViewSet):
    queryset = Printer.objects.select_related("store").all()
    serializer_class = PrinterSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["store", "is_active", "paper_size", "is_default"]
    search_fields = ["name", "description", "ip_address", "store__name"]
    ordering_fields = ["name", "paper_size", "created_at"]