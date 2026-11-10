"""
TSOSI blog, built from https://github.com/tsosi-org/tsosi-org.github.io:
each push on its master branch publishes a release with the built posts,
extracted in the frontend public directory under `pages/blog/`.
"""

import json
import logging
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from django.conf import settings
from lxml import html as lxml_html

from tsosi.app_settings import app_settings

logger = logging.getLogger(__name__)

BLOG_PKG_URL = "https://github.com/tsosi-org/tsosi-org.github.io/releases/latest/download/public.tar"
REQUEST_TIMEOUT = 60


def blog_dir() -> Path:
    return Path(settings.BASE_DIR) / app_settings.PUBLIC_RELPATH / "pages/blog"


def fetch_blog():
    """
    Download the latest blog package and extract it in the frontend public
    directory, overwriting the existing posts.
    """
    resp = requests.get(BLOG_PKG_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    target = blog_dir()
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as f:
        f.write(resp.content)
        f.seek(0)
        with tarfile.open(fileobj=f) as tar:
            tar.extractall(target, filter="data")
    logger.info("Blog content updated.")


def read_blog_index() -> list[dict]:
    """
    The blog posts, latest first, with their `id`, `title`, `summary` as
    plain text and `date`.
    """
    index_path = blog_dir() / "index.json"
    try:
        with open(index_path) as f:
            posts = json.load(f)["posts"]
    except (OSError, ValueError, KeyError):
        logger.warning(f"Could not read the blog index at {index_path}")
        return []
    result = []
    for post in posts:
        try:
            result.append(
                {
                    # The permalink looks like `/post/<id>/index.json`
                    "id": post["permalink"].split("/")[2],
                    "title": post["title"],
                    "summary": html_to_text(post.get("summary") or ""),
                    "date": datetime.fromisoformat(post["date"]),
                }
            )
        except (KeyError, IndexError, ValueError):
            logger.warning(f"Skipped invalid blog index entry: {post}")
    result.sort(key=lambda p: p["date"], reverse=True)
    return result


def html_to_text(content: str) -> str:
    if not content.strip():
        return ""
    return " ".join(lxml_html.fromstring(content).text_content().split())
