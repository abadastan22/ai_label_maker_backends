from django.urls import path

from .views import (
    DailyPrepSummaryView,
    ExpiringItemsView,
    WasteSummaryView,
    PrintActivitySummaryView,
    PrintCopiesSummaryView,
)

urlpatterns = [
    path("reports/daily-prep-summary/", DailyPrepSummaryView.as_view(), name="daily-prep-summary"),
    path("reports/expiring-items/", ExpiringItemsView.as_view(), name="expiring-items"),
    path("reports/waste-summary/", WasteSummaryView.as_view(), name="waste-summary"),
    path("reports/print-activity-summary/", PrintActivitySummaryView.as_view(), name="print-activity-summary"),
    path("reports/print-copies-summary/", PrintCopiesSummaryView.as_view(), name="print-copies-summary"),
]