"""
Sitemap of the public frontend, served at `/sitemap.xml`.

URLs are built from `TSOSI_FRONTEND_URL` and must match the canonical URLs
set by the frontend (`frontend/src/utils/seo.ts`): entities by their TSOSI ID,
no trailing slash except for blog posts.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from tsosi.app_settings import app_settings
from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI
from tsosi.models import Identifier

logger = logging.getLogger(__name__)

STATIC_PAGES = [
    "/",
    "/explore",
    "/new-provider",
    "/pages/about",
    "/pages/faq",
    "/pages/blog",
    "/pages/newsletter",
    "/pages/legal-notice",
    "/pages/privacy-policy",
]


class FrontendSitemap(Sitemap):
    """Base sitemap listing URLs of the frontend instead of the API host."""

    def get_domain(self, site=None) -> str:
        return urlsplit(app_settings.FRONTEND_URL).netloc

    def get_protocol(self, protocol=None) -> str:
        return urlsplit(app_settings.FRONTEND_URL).scheme


class StaticPageSitemap(FrontendSitemap):
    def items(self) -> list[str]:
        return STATIC_PAGES

    def location(self, item: str) -> str:
        return item


class EntitySitemap(FrontendSitemap):
    def items(self):
        return (
            Identifier.objects.filter(
                registry_id=REGISTRY_TSOSI, entity__is_active=True
            )
            .select_related("entity")
            .order_by("value")
        )

    def location(self, item: Identifier) -> str:
        return f"/entities/{item.value}"

    def lastmod(self, item: Identifier) -> datetime:
        return item.entity.date_last_updated


class BlogSitemap(FrontendSitemap):
    """
    Blog posts, read from the blog index fetched in the frontend public
    directory by the `fetch_blog` command.
    """

    def items(self) -> list[dict]:
        index_path = (
            Path(settings.BASE_DIR)
            / app_settings.PUBLIC_RELPATH
            / "pages/blog/index.json"
        )
        try:
            with open(index_path) as f:
                return json.load(f)["posts"]
        except (OSError, ValueError, KeyError):
            logger.warning(f"Could not read the blog index at {index_path}")
            return []

    def location(self, item: dict) -> str:
        # The permalink looks like `/post/<id>/index.json`
        post_id = item["permalink"].split("/")[2]
        return f"/pages/blog/{post_id}/"

    def lastmod(self, item: dict) -> datetime:
        return datetime.fromisoformat(item["date"])


SITEMAPS = {
    "pages": StaticPageSitemap,
    "entities": EntitySitemap,
    "blog": BlogSitemap,
}
