import json

import pytest
from django.test import Client

from tsosi.data.pid_registry.tsosi import REGISTRY_TSOSI

from .factories import EntityFactory, IdentifierFactory


@pytest.mark.django_db
def test_sitemap(registries, settings, tmp_path):
    blog_dir = tmp_path / "pages/blog"
    blog_dir.mkdir(parents=True)
    with open(blog_dir / "index.json", "w") as f:
        json.dump(
            {
                "posts": [
                    {
                        "date": "2026-03-18T00:00:00Z",
                        "permalink": "/post/2026-02-10-ror-hierarchy/index.json",
                    }
                ]
            },
            f,
        )
    settings.TSOSI_PUBLIC_RELPATH = str(tmp_path)

    entity = EntityFactory.create()
    IdentifierFactory.create(
        entity=entity, registry_id=REGISTRY_TSOSI, value="T123456"
    )
    # Entities are listed by their TSOSI ID only
    IdentifierFactory.create(entity=entity, value="05amyt365")
    inactive = EntityFactory.create(is_active=False)
    IdentifierFactory.create(
        entity=inactive, registry_id=REGISTRY_TSOSI, value="T654321"
    )

    response = Client().get("/sitemap.xml")
    assert response.status_code == 200
    content = response.content.decode()

    base_url = settings.TSOSI_FRONTEND_URL
    assert f"<loc>{base_url}/</loc>" in content
    assert f"<loc>{base_url}/pages/faq</loc>" in content
    assert f"<loc>{base_url}/entities/T123456</loc>" in content
    assert "05amyt365" not in content
    assert "T654321" not in content
    assert (
        f"<loc>{base_url}/pages/blog/2026-02-10-ror-hierarchy/</loc>"
        "<lastmod>2026-03-18</lastmod>"
    ) in content


@pytest.mark.django_db
def test_sitemap_without_blog(settings, tmp_path):
    settings.TSOSI_PUBLIC_RELPATH = str(tmp_path)
    response = Client().get("/sitemap.xml")
    assert response.status_code == 200
    assert "/pages/blog/" not in response.content.decode()
