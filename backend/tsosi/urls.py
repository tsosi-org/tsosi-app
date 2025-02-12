from django.urls import include, path
from tsosi.api.router import OptionalSlashRouter
from tsosi.api.viewsets import (
    AnalyticViewSet,
    CurrencyViewSet,
    EntityViewSet,
    TransfertViewSet,
)

app_name = "tsosi"

router = OptionalSlashRouter()
### Produced routes:
# entities/                     entity-list
# entities/all/                 entity-all
# entities/(?P<pk>[^/.]+)/      entity-detail
router.register(r"entities", EntityViewSet, basename="entity")
### Produced routes:
# transferts/                   transfert-list
# transferts/all/               transfert-all
# transferts/(?P<pk>[^/.]+)/    transfert-detail
router.register(r"transferts", TransfertViewSet, basename="transfert")
### Produced routes:
# currencies/                   currency-list
# currencies/(?P<pk>[^/.]+)/    currency-detail useless
router.register(r"currencies", CurrencyViewSet, basename="currency")
### Produced routes:
# analytics/                   analytics-list
# analytics/(?P<pk>[^/.]+)/    analytics-detail useless
router.register(r"analytics", AnalyticViewSet, basename="analytic")

print("\n\n")
print(router.urls)
print("\n\n")

urlpatterns = [path("api/", include(router.urls))]
