from __future__ import annotations

from django.db import models

from .utils import TimestampedModel


def news_item_image_path(instance: NewsItem, filename: str) -> str:
    """Return the file path where to store the news image file"""
    return f"news/{instance.board_item_id}/{filename}"


class NewsItem(TimestampedModel):
    """
    A news shown on the home page: a card of the `Live` column of the
    GitHub "Homepage news" board, refreshed hourly (`tsosi.data.news`).
    """

    KIND_LINKEDIN = "linkedin"
    KIND_BLOG = "blog"
    KIND_NEWSLETTER = "newsletter"
    KIND_OTHER = "other"
    KIND_CHOICES = {
        KIND_LINKEDIN: "LinkedIn post",
        KIND_BLOG: "Blog post",
        KIND_NEWSLETTER: "Newsletter",
        KIND_OTHER: "Other",
    }

    # Node ID of the GitHub project item
    board_item_id = models.CharField(max_length=64, unique=True)
    # Order on the home page, from the board column order
    position = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    title = models.TextField(blank=True)
    text = models.TextField(blank=True)
    url = models.URLField(max_length=512)
    date = models.DateTimeField(null=True)
    image = models.ImageField(
        upload_to=news_item_image_path, max_length=256, null=True
    )
    image_alt = models.TextField(blank=True)
    # URL the image was downloaded from, to download it only when it changes
    image_source_url = models.URLField(max_length=1024, null=True)


class NewsProposal(TimestampedModel):
    """
    A blog post, newsletter or LinkedIn post already proposed on the board,
    so that it is not proposed again once its card is deleted.
    """

    # Normalized URL of the news
    url = models.CharField(max_length=512, unique=True)


class Newsletter(TimestampedModel):
    """
    A newsletter of https://github.com/tsosi-org/newsletter, refreshed hourly
    (`tsosi.data.newsletters`) and served at `/pages/newsletter/<name>`.
    """

    # File name without extension, ex: `2025-10` or `2026-02-04`
    name = models.CharField(max_length=32, unique=True)
    date = models.DateTimeField()
    # Texts of the `h2` and `h3` headings
    key_points = models.JSONField(default=list)
    # Content of the HTML body, with the images served by TSOSI
    html = models.TextField()
    # Git blob SHA of the file, to download it only when it changes
    source_sha = models.CharField(max_length=64)
