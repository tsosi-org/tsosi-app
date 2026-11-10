"""
TSOSI newsletters: HTML files named by their publication date (`YYYY-MM` or
`YYYY-MM-DD`) in https://github.com/tsosi-org/newsletter, written with
maily.to. The hourly `refresh_news` task stores the new and changed ones,
with their images, so that visitors of `/pages/newsletter` only request
tsosi.org.
"""

import hashlib
import logging
import mimetypes
from datetime import UTC, datetime

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from lxml import html as lxml_html

from tsosi.models import Newsletter

from .github_api import GitHubClient

logger = logging.getLogger(__name__)

NEWSLETTER_REPO = "tsosi-org/newsletter"


def newsletter_date(name: str) -> datetime | None:
    """Newsletters are named `YYYY-MM` or `YYYY-MM-DD`."""
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(name, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def list_newsletter_files(client: GitHubClient) -> list[dict]:
    """
    The newsletter files of the repository, with their `name` (without
    extension), `date`, `sha` and `download_url`.
    """
    repo = client.config.get("newsletter_repo", NEWSLETTER_REPO)
    files = []
    for f in client.rest_get(f"repos/{repo}/contents/"):
        if f.get("type") != "file" or not f["name"].endswith(".html"):
            continue
        name = f["name"].removesuffix(".html")
        date = newsletter_date(name)
        if date is None:
            logger.warning(f"Skipped newsletter with invalid name: {name}")
            continue
        files.append(
            {
                "name": name,
                "date": date,
                "sha": f["sha"],
                "download_url": f["download_url"],
            }
        )
    return files


def key_points(body: lxml_html.HtmlElement) -> list[str]:
    """The texts of the `h2` and `h3` headings."""
    return [
        text
        for h in body.xpath(".//h2 | .//h3")
        if (text := " ".join(h.text_content().split()))
    ]


def image_path(name: str, url: str) -> str:
    """Path of a newsletter image in the media storage, by source URL."""
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"newsletters/{name}/{digest}"


def media_url(path: str) -> str:
    url = default_storage.url(path)
    return url if url.startswith(("/", "http")) else f"/{url}"


def store_image(client: GitHubClient, name: str, url: str) -> str | None:
    """
    Store a newsletter image, unless already stored. Return its path in the
    media storage, `None` if it can't be downloaded.
    """
    prefix = image_path(name, url)
    folder = f"newsletters/{name}"
    if default_storage.exists(folder):
        for filename in default_storage.listdir(folder)[1]:
            if f"{folder}/{filename}".startswith(prefix):
                return f"{folder}/{filename}"
    try:
        resp = client.download(url)
    except requests.RequestException as e:
        logger.warning(f"Failed to download newsletter image {url}: {e}")
        return None
    content_type = resp.headers.get("Content-Type", "").split(";")[0]
    if not content_type.startswith("image/"):
        logger.warning(f"Newsletter image {url} is not an image.")
        return None
    extension = mimetypes.guess_extension(content_type) or ""
    return default_storage.save(prefix + extension, ContentFile(resp.content))


def parse_newsletter(
    client: GitHubClient, name: str, content: str
) -> tuple[str, list[str], set[str]]:
    """
    The HTML of the newsletter body with its images served by TSOSI, its key
    points and the paths of its images.
    """
    body = lxml_html.document_fromstring(content).find("body")
    if body is None:
        return "", [], set()
    paths = set()
    for img in body.iter("img"):
        src = img.get("src") or ""
        if not src.startswith(("http://", "https://")):
            continue
        path = store_image(client, name, src)
        if path is not None:
            paths.add(path)
            img.set("src", media_url(path))
    html = (body.text or "") + "".join(
        lxml_html.tostring(child, encoding="unicode") for child in body
    )
    return html.strip(), key_points(body), paths


def header_image(newsletter: Newsletter) -> str | None:
    """
    The storage path of the header image of a newsletter, its first image,
    `None` if it has none stored.
    """
    if not newsletter.html.strip():
        return None
    root = lxml_html.fragment_fromstring(newsletter.html, create_parent="div")
    img = root.find(".//img")
    if img is None:
        return None
    src = img.get("src") or ""
    prefix = media_url("")
    if not src.startswith(prefix):
        return None
    return src.removeprefix(prefix)


def delete_images(name: str, keep: frozenset[str] | set[str] = frozenset()):
    folder = f"newsletters/{name}"
    if not default_storage.exists(folder):
        return
    for filename in default_storage.listdir(folder)[1]:
        if f"{folder}/{filename}" not in keep:
            default_storage.delete(f"{folder}/{filename}")


def refresh_newsletters(client: GitHubClient) -> int:
    """
    Store the new and changed newsletters, delete the removed ones. Return
    the number of newsletters stored or updated.
    """
    files = list_newsletter_files(client)
    if not files:
        # Safer to keep the stored ones than to empty the page.
        logger.warning("No newsletter found, keeping the stored ones.")
        return 0

    existing = {n.name: n for n in Newsletter.objects.all()}
    updated = 0
    for f in files:
        newsletter = existing.pop(f["name"], None)
        if newsletter is not None and newsletter.source_sha == f["sha"]:
            continue
        try:
            content = client.download(f["download_url"]).text
        except requests.RequestException as e:
            logger.warning(f"Failed to download newsletter {f['name']}: {e}")
            continue
        html, points, images = parse_newsletter(client, f["name"], content)
        newsletter = newsletter or Newsletter(name=f["name"])
        newsletter.date = f["date"]
        newsletter.html = html
        newsletter.key_points = points
        newsletter.source_sha = f["sha"]
        newsletter.save()
        delete_images(f["name"], keep=images)
        updated += 1
        logger.info(f"Stored newsletter {f['name']}.")

    with transaction.atomic():
        for newsletter in existing.values():
            delete_images(newsletter.name)
            newsletter.delete()
            logger.info(f"Deleted newsletter {newsletter.name}.")
    return updated
