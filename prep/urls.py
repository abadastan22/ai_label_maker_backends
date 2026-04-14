from rest_framework.routers import DefaultRouter

from .views import PrepItemViewSet, PrepTaskViewSet

router = DefaultRouter()
router.register(r"prep-items", PrepItemViewSet, basename="prep-item")
router.register(r"prep-tasks", PrepTaskViewSet, basename="prep-task")

urlpatterns = router.urls