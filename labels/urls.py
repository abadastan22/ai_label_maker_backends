from rest_framework.routers import DefaultRouter

from .views import LabelViewSet, PrintJobViewSet

router = DefaultRouter()
router.register(r"labels", LabelViewSet, basename="label")
router.register(r"print-jobs", PrintJobViewSet, basename="print-job")

urlpatterns = router.urls