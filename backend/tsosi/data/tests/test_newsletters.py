import io
from datetime import UTC, datetime

import pytest
import requests
from django.core.files.storage import default_storage
from django.test import Client
from PIL import Image
from tsosi.data import newsletters
from tsosi.data.github_api import GitHubClient, GitHubError
from tsosi.models import Newsletter

BANNER = "https://raw.githubusercontent.com/tsosi-org/branding/banner.png"


def png_bytes() -> bytes:
    content = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(content, format="PNG")
    return content.getvalue()


def newsletter_html(title: str = "New data providers") -> str:
    return f"""<!DOCTYPE html>
<html><head><link rel="preload" as="image" href="{BANNER}" /></head>
<body>Intro<table><tr><td>
<img alt="TSOSI" src="{BANNER}" />
<h2>{title}</h2><p>Text</p>
<h3> Save the  date </h3>
<img src="https://example.org/broken.png" />
<img src="data:image/png;base64,AAAA" />
</td></tr></table></body></html>"""


class FakeResponse:
    def __init__(
        self, status_code=200, json_data=None, content=b"", headers=None
    ):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.text = content.decode(errors="replace")
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeRepo:
    """Mock of the newsletter repository on GitHub."""

    def __init__(self):
        self.files = {"2025-10.html": newsletter_html(), "x.html": ""}
        self.shas = {"2025-10.html": "sha1", "x.html": "sha"}
        self.downloads: list[str] = []
        self.list_status = 200

    def get(self, url, params=None, headers=None, timeout=None):
        if url.endswith("/repos/tsosi-org/newsletter/contents/"):
            return FakeResponse(
                status_code=self.list_status,
                json_data=[
                    {
                        "name": name,
                        "type": "file",
                        "sha": self.shas[name],
                        "download_url": f"https://raw.example/{name}",
                    }
                    for name in self.files
                ]
                + [{"name": ".github", "type": "dir"}],
            )
        self.downloads.append(url)
        if url.startswith("https://raw.example/"):
            name = url.removeprefix("https://raw.example/")
            return FakeResponse(content=self.files[name].encode())
        if url == BANNER:
            return FakeResponse(
                content=png_bytes(), headers={"Content-Type": "image/png"}
            )
        return FakeResponse(status_code=404)


@pytest.fixture
def repo(mocker, settings, tmp_path) -> FakeRepo:
    settings.MEDIA_ROOT = str(tmp_path)
    settings.MEDIA_URL = "media/"
    fake = FakeRepo()
    mocker.patch.object(newsletters.requests, "get", side_effect=fake.get)
    return fake


def test_newsletter_date():
    assert newsletters.newsletter_date("2025-10") == datetime(
        2025, 10, 1, tzinfo=UTC
    )
    assert newsletters.newsletter_date("2026-02-04") == datetime(
        2026, 2, 4, tzinfo=UTC
    )
    assert newsletters.newsletter_date("draft") is None


@pytest.mark.django_db
def test_refresh_newsletters(repo):
    assert newsletters.refresh_newsletters(GitHubClient()) == 1

    newsletter = Newsletter.objects.get()
    assert newsletter.name == "2025-10"
    assert newsletter.date == datetime(2025, 10, 1, tzinfo=UTC)
    assert newsletter.key_points == ["New data providers", "Save the date"]
    assert newsletter.source_sha == "sha1"
    # The body only, with the images served by TSOSI
    html = newsletter.html
    assert html.startswith("Intro<table>") and "<head" not in html
    assert BANNER not in html
    [banner_path] = default_storage.listdir("newsletters/2025-10")[1]
    assert f'src="/media/newsletters/2025-10/{banner_path}"' in html
    assert banner_path.endswith(".png")
    # Failed downloads and inline images are kept as they are
    assert 'src="https://example.org/broken.png"' in html
    assert 'src="data:image/png;base64,AAAA"' in html

    # Unchanged newsletters are not downloaded again
    repo.downloads.clear()
    assert newsletters.refresh_newsletters(GitHubClient()) == 0
    assert repo.downloads == []

    # Changed ones are, but not their unchanged images
    repo.files["2025-10.html"] = newsletter_html("Hub launch")
    repo.shas["2025-10.html"] = "sha2"
    assert newsletters.refresh_newsletters(GitHubClient()) == 1
    assert BANNER not in repo.downloads
    newsletter.refresh_from_db()
    assert newsletter.key_points == ["Hub launch", "Save the date"]
    assert default_storage.listdir("newsletters/2025-10")[1] == [banner_path]

    # Removed ones are deleted, with their images
    repo.files = {"2026-10.html": newsletter_html()}
    repo.shas = {"2026-10.html": "sha3"}
    newsletters.refresh_newsletters(GitHubClient())
    assert list(Newsletter.objects.values_list("name", flat=True)) == [
        "2026-10"
    ]
    assert default_storage.listdir("newsletters/2025-10")[1] == []


@pytest.mark.django_db
def test_refresh_newsletters_keeps_stored_ones(repo):
    newsletters.refresh_newsletters(GitHubClient())
    repo.files, repo.shas = {}, {}
    assert newsletters.refresh_newsletters(GitHubClient()) == 0
    assert Newsletter.objects.count() == 1

    repo.list_status = 503
    with pytest.raises(GitHubError):
        newsletters.refresh_newsletters(GitHubClient())
    assert Newsletter.objects.count() == 1


@pytest.mark.django_db
def test_newsletter_views():
    for name in ["2025-10", "2026-02-04"]:
        Newsletter.objects.create(
            name=name,
            date=newsletters.newsletter_date(name),
            key_points=[f"Point {name}"],
            html=f"<p>{name}</p>",
            source_sha="sha",
        )
    client = Client()

    response = client.get("/api/newsletters")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "2026-02-04",
            "date": "2026-02-04T00:00:00+00:00",
            "key_points": ["Point 2026-02-04"],
        },
        {
            "id": "2025-10",
            "date": "2025-10-01T00:00:00+00:00",
            "key_points": ["Point 2025-10"],
        },
    ]

    response = client.get("/api/newsletters/2025-10")
    assert response.status_code == 200
    assert response.json()["html"] == "<p>2025-10</p>"
    assert client.get("/api/newsletters/2024-01").status_code == 404
