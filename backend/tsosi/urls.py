from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from tsosi.api.newsletter import NewsletterRequestView
from tsosi.api.router import OptionalSlashRouter
from tsosi.api.views import (
    home_figures_view,
    news_view,
    newsletter_view,
    newsletters_view,
    stats_view,
)
from tsosi.api.viewsets import (
    AnalyticViewSet,
    CurrencyViewSet,
    EntityViewSet,
    TransferViewSet,
)
from tsosi.data.newsletter import NewsletterAction
from tsosi.sitemaps import SITEMAPS

app_name = "tsosi"

router = OptionalSlashRouter()
### Produced routes:
# entities/                     entity-list
# entities/all/                 entity-all
# entities/(?P<pk>[^/.]+)/      entity-detail
router.register(r"entities", EntityViewSet, basename="entity")
### Produced routes:
# transfers/                   transfer-list
# transfers/all/               transfer-all
# transfers/(?P<pk>[^/.]+)/    transfer-detail
router.register(r"transfers", TransferViewSet, basename="transfer")
### Produced routes:
# currencies/                   currency-list
# currencies/(?P<pk>[^/.]+)/    currency-detail useless
router.register(r"currencies", CurrencyViewSet, basename="currency")
### Produced routes:
# analytics/                   analytics-list
# analytics/(?P<pk>[^/.]+)/    analytics-detail useless
router.register(r"analytics", AnalyticViewSet, basename="analytic")

# print("\n\n")
# print(router.urls)
# print("\n\n")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/stats", stats_view),
    path("api/home-figures", home_figures_view),
    path("api/news", news_view),
    path("api/newsletters", newsletters_view),
    path("api/newsletters/<str:name>", newsletter_view),
    path(
        "api/newsletter/subscribe",
        NewsletterRequestView.as_view(action=NewsletterAction.SUBSCRIBE),
        name="newsletter-subscribe",
    ),
    path(
        "api/newsletter/unsubscribe",
        NewsletterRequestView.as_view(action=NewsletterAction.UNSUBSCRIBE),
        name="newsletter-unsubscribe",
    ),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}),
]
