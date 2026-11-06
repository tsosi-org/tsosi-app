from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from tsosi.api.hub.declarations import (
    EntityDeclarationsView,
    EntityDeclarationView,
)
from tsosi.api.hub.entities import EntityPreviewView, EntityTransfersView
from tsosi.api.hub.organizations import (
    EntityOrganizationsView,
    OrganizationSearchView,
)
from tsosi.api.hub.session import LoginLinkView, LoginView, LogoutView, MeView
from tsosi.api.hub.submissions import (
    EntityPublicationPreviewView,
    EntitySubmissionsView,
)
from tsosi.api.router import OptionalSlashRouter
from tsosi.api.views import home_figures_view, stats_view
from tsosi.api.viewsets import (
    AnalyticViewSet,
    CurrencyViewSet,
    EntityViewSet,
    TransferViewSet,
)
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
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}),
    path("api/hub/login-link", LoginLinkView.as_view()),
    path("api/hub/login", LoginView.as_view()),
    path("api/hub/logout", LogoutView.as_view()),
    path("api/hub/me", MeView.as_view()),
    path("api/hub/organizations", OrganizationSearchView.as_view()),
    path("api/hub/entities/<str:entity_id>", EntityPreviewView.as_view()),
    path(
        "api/hub/entities/<str:entity_id>/transfers",
        EntityTransfersView.as_view(),
    ),
    path(
        "api/hub/entities/<str:entity_id>/declarations",
        EntityDeclarationsView.as_view(),
    ),
    path(
        "api/hub/entities/<str:entity_id>/declarations/<int:declaration_id>",
        EntityDeclarationView.as_view(),
    ),
    path(
        "api/hub/entities/<str:entity_id>/organizations",
        EntityOrganizationsView.as_view(),
    ),
    path(
        "api/hub/entities/<str:entity_id>/submissions",
        EntitySubmissionsView.as_view(),
    ),
    path(
        "api/hub/entities/<str:entity_id>/publication-preview",
        EntityPublicationPreviewView.as_view(),
    ),
]
