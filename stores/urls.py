from rest_framework.routers import DefaultRouter

from .views import StoreViewSet, DepartmentViewSet, PrinterViewSet

router = DefaultRouter()
router.register(r"stores", StoreViewSet, basename="store")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"printers", PrinterViewSet, basename="printer")

urlpatterns = router.urls