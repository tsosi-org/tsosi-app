import io
import json
import tarfile
from datetime import UTC, datetime, timedelta

import pytest
import requests
from django.test import Client
from django.utils import timezone
from PIL import Image

from tsosi.data import news
from tsosi.models import NewsItem, NewsProposal

NOW = timezone.now()


def linkedin_id(date: datetime) -> int:
    """A LinkedIn post ID created at the given date."""
    return (int(date.timestamp() * 1000) << 22) + 12345


RECENT = (NOW - timedelta(days=5)).replace(microsecond=0)
RECENT_POST_URL = (
    "https://www.linkedin.com/posts/tsosi_news-activity-"
    f"{linkedin_id(RECENT)}-AbCd"
)


def png_bytes() -> bytes:
    content = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(content, format="PNG")
    return content.getvalue()


def issue_form_body(
    text: str = "Big news!", image: str = "", url: str = ""
) -> str:
    return (
        f"### Post text\n\n{text}\n\n### Image\n\n{image or '_No response_'}"
        f"\n\n### LinkedIn URL\n\n{url or '_No response_'}\n\n"
        "### Notes\n\nTag https://www.linkedin.com/posts/partner-activity-1\n"
    )


## Parsing
def test_card_sections():
    body = issue_form_body(text="Line 1\nLine 2")
    assert news.card_sections(body) == {
        "post text": "Line 1\nLine 2",
        "image": "",
        "linkedin url": "",
        "notes": "Tag https://www.linkedin.com/posts/partner-activity-1",
    }


def test_card_link():
    # The link section wins, even when empty
    body = issue_form_body(url=RECENT_POST_URL)
    assert news.card_link("[LinkedIn] KU Leuven", body) == RECENT_POST_URL
    assert news.card_link("[LinkedIn] KU Leuven", issue_form_body()) is None
    # Else the title, then a LinkedIn post link, then the first link
    assert (
        news.card_link("https://tsosi.org/pages/blog/a/", "https://b.org")
        == "https://tsosi.org/pages/blog/a/"
    )
    body = f"See https://tsosi.org/entities/T1.\nPosted: {RECENT_POST_URL}"
    assert news.card_link("Title", body) == RECENT_POST_URL
    assert news.card_link("Title", "See https://b.org/x.") == "https://b.org/x"
    # Images are not links
    body = "![img](https://github.com/user-attachments/assets/1)"
    assert news.card_link("Title", body) is None
    assert news.card_link("Title", None) is None


def test_card_text():
    body = issue_form_body(
        text="**KU Leuven** joins [TSOSI](https://tsosi.org)!\n\n\n\nMore",
        image="![img](https://github.com/user-attachments/assets/1)",
    )
    assert news.card_text(body) == "KU Leuven joins TSOSI!\n\nMore"
    # Without sections: the body without images and lines of links only
    body = (
        "Some text\n<img alt='a' src='https://x.org/i.png'>\n"
        "https://tsosi.org/entities/T1\n<!-- hidden -->End"
    )
    assert news.card_text(body) == "Some text\n\nEnd"


def test_card_title():
    body = "### Link\n\nhttps://x.org\n\n### Title\n\nPKP  joins\nTSOSI"
    assert news.card_title("[News] Draft title", body) == "PKP joins TSOSI"
    assert news.card_title("[News] PKP joins TSOSI", "") == "PKP joins TSOSI"
    assert news.card_title("https://x.org", "") == ""


def test_card_images():
    body = (
        'Text <img width="300" alt="Logo" src="https://x.org/a.png" />\n'
        "![Chart](https://x.org/b.png)"
    )
    assert news.card_images(body) == [
        ("https://x.org/a.png", "Logo"),
        ("https://x.org/b.png", "Chart"),
    ]


def test_link_kind():
    assert news.link_kind(RECENT_POST_URL) == NewsItem.KIND_LINKEDIN
    assert news.link_kind("https://lnkd.in/p/e5cx-zKz") == "linkedin"
    assert news.link_kind("https://tsosi.org/pages/blog/a/") == "blog"
    assert news.link_kind("https://tsosi.org/pages/newsletter/2025-10") == (
        "newsletter"
    )
    assert news.link_kind("https://other.org/pages/blog/a/") == "other"
    assert news.link_kind("https://tsosi.org/pages/blog") == "other"


def test_linkedin_post_date():
    assert news.linkedin_post_date(RECENT_POST_URL) == RECENT
    url = f"https://www.linkedin.com/feed/update/urn:li:share:{linkedin_id(RECENT)}/"
    assert news.linkedin_post_date(url) == RECENT
    assert news.linkedin_post_date("https://www.linkedin.com/company/x") is None
    future = linkedin_id(NOW + timedelta(days=10))
    assert news.linkedin_post_date(f"urn:li:activity:{future}") is None


def test_linkedin_date(mocker):
    assert news.linkedin_date(RECENT_POST_URL) == RECENT
    head = mocker.patch.object(
        news.requests,
        "head",
        return_value=FakeResponse(
            status_code=301,
            headers={
                "Location": "https://www.linkedin.com/posts/news-share-"
                f"{linkedin_id(RECENT)}-pzAv/?utm_source=share"
            },
        ),
    )
    assert news.linkedin_date("https://lnkd.in/p/e5cx-zKz") == RECENT
    head.assert_called_once()
    head.side_effect = requests.ConnectionError
    assert news.linkedin_date("https://lnkd.in/p/e5cx-zKz") is None


def test_card_date():
    body = "### Date\n\n2026-10-15\n\n### Text\n\nHello"
    assert news.card_date(body) == datetime(2026, 10, 15, tzinfo=UTC)
    assert news.card_date("### Date\n\n_No response_") is None
    assert news.card_date("### Date\n\n15/10/2026") is None
    assert news.card_date("No sections") is None


def test_normalize_url():
    assert (
        news.normalize_url("http://TSOSI.org/pages/blog/a/?x=1#y")
        == "https://tsosi.org/pages/blog/a"
    )
    assert (
        news.normalize_url("http://localhost:5173/pages/blog/a/")
        == "https://localhost:5173/pages/blog/a"
    )


## Refresh workflow
class FakeResponse:
    def __init__(
        self, status_code=200, json_data=None, content=b"", headers=None
    ):
        self.status_code = status_code
        self._json = json_data
        self.content = content
        self.text = (
            content.decode(errors="replace")
            if content
            else json.dumps(json_data)
        )
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeGitHub:
    """Mock of GitHub API, dispatching requests by URL and query."""

    def __init__(self, cards: list[dict], issues: list[dict] | None = None):
        self.cards = cards
        self.issues = issues or []
        self.mutations: list[tuple[str, dict]] = []
        self.created_issues: list[dict] = []
        self.downloads: list[str] = []
        self.newsletters = ["2025-10.html", f"{RECENT:%Y-%m}.html", "x.html"]

    def board_node(self, card: dict) -> dict:
        content = {
            "__typename": card.get("type", "DraftIssue"),
            "title": card.get("title", ""),
            "body": card.get("body", ""),
            "createdAt": "2026-01-01T00:00:00Z",
        }
        if "url" in card:
            content["url"] = card["url"]
        return {
            "id": card["id"],
            "isArchived": card.get("archived", False),
            "status": {"name": card["status"]} if card.get("status") else None,
            "content": content,
        }

    def post(self, url, json=None, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer secret"
        if url.endswith("/repos/tsosi-org/newsletter/issues"):
            self.created_issues.append(json)
            return FakeResponse(
                json_data={"node_id": f"I_created{len(self.created_issues)}"}
            )
        query, variables = json["query"], json["variables"]
        if "projectV2(number" in query:
            return FakeResponse(
                json_data={
                    "data": {
                        "organization": {
                            "projectV2": {
                                "id": "PROJECT",
                                "field": {
                                    "id": "STATUS",
                                    "options": [
                                        {"id": "OPT_C", "name": "Candidates"},
                                        {"id": "OPT_H", "name": "Live"},
                                        {"id": "OPT_A", "name": "Archived"},
                                    ],
                                },
                                "items": {
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                    "nodes": [
                                        self.board_node(c) for c in self.cards
                                    ],
                                },
                            }
                        }
                    }
                }
            )
        self.mutations.append((query, variables))
        if "addProjectV2ItemById" in query:
            item_id = f"ITEM_{variables['content']}"
            data = {"addProjectV2ItemById": {"item": {"id": item_id}}}
        else:
            data = {"updateProjectV2ItemFieldValue": {"projectV2Item": {}}}
        return FakeResponse(json_data={"data": data})

    def get(self, url, params=None, headers=None, timeout=None):
        if url.endswith("/repos/tsosi-org/newsletter/contents/"):
            return FakeResponse(
                json_data=[
                    {
                        "name": name,
                        "type": "file",
                        "sha": f"sha-{name}",
                        "download_url": f"https://raw.example/{name}",
                    }
                    for name in self.newsletters
                ]
                + [{"name": "README.md", "type": "file"}]
            )
        if url.endswith("/repos/tsosi-org/newsletter/issues"):
            return FakeResponse(json_data=self.issues)
        self.downloads.append(url)
        if url.startswith("https://raw.example/"):
            return FakeResponse(
                content=b"<html><body><img src='https://img.example/b.png'>"
                b"<h2>New providers</h2><p>x</p>"
                b"<h3> Hub  launch </h3></body></html>"
            )
        if url.endswith(".png"):
            return FakeResponse(
                content=png_bytes(), headers={"Content-Type": "image/png"}
            )
        return FakeResponse(status_code=404)


@pytest.fixture
def news_settings(settings, tmp_path):
    settings.TSOSI_TRIGGER_JOBS = False
    # Card links don't depend on the server
    settings.TSOSI_FRONTEND_URL = "http://localhost:5173"
    settings.TSOSI_NEWS_BOARD = {
        "owner": "tsosi-org",
        "project_number": 7,
        "token": "secret",
    }
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.TSOSI_PUBLIC_RELPATH = str(tmp_path / "public")
    blog_dir = tmp_path / "public/pages/blog"
    blog_dir.mkdir(parents=True)
    with open(blog_dir / "index.json", "w") as f:
        json.dump(
            {
                "posts": [
                    {
                        "date": "2025-03-18T00:00:00Z",
                        "permalink": "/post/old-post/index.json",
                        "summary": "<p>Old</p>",
                        "title": "Old post",
                    },
                    {
                        "date": RECENT.isoformat(),
                        "permalink": "/post/ror-hierarchy/index.json",
                        "summary": "<p>TSOSI has <b>integrated</b>\n ROR!</p>",
                        "title": "ROR hierarchy",
                    },
                ]
            },
            f,
        )
    return settings


@pytest.fixture
def fake_github(mocker, news_settings):
    def install(cards, issues=None) -> FakeGitHub:
        fake = FakeGitHub(cards, issues)
        mocker.patch.object(news, "fetch_blog")
        mocker.patch.object(news.requests, "post", side_effect=fake.post)
        mocker.patch.object(news.requests, "get", side_effect=fake.get)
        return fake

    return install


def linkedin_card(id: str, status: str, image: str = "") -> dict:
    return {
        "id": id,
        "status": status,
        "type": "Issue",
        "title": "[LinkedIn] KU Leuven",
        "url": f"https://github.com/tsosi-org/newsletter/issues/{id}",
        "body": issue_form_body(
            text="KU Leuven joins TSOSI!", image=image, url=RECENT_POST_URL
        ),
    }


@pytest.mark.django_db
def test_refresh_news_stores_shown_cards(fake_github):
    image = "![Logo](https://github.com/user-attachments/assets/a.png)"
    fake = fake_github(
        [
            {"id": "C1", "status": "Candidates", "title": "Not shown"},
            {
                "id": "N1",
                "status": "Live",
                "title": "Newsletter",
                "body": f"https://tsosi.org/pages/newsletter/{RECENT:%Y-%m}",
            },
            linkedin_card("L1", "Live", image=image),
            {
                "id": "B1",
                "status": "Live",
                "title": "Blog: ROR",
                "body": "https://tsosi.org/pages/blog/ror-hierarchy/",
            },
            {
                "id": "O1",
                "status": "Live",
                "title": "Over the limit",
                "body": "https://pkp.sfu.ca/2026/09/01/pkp-joins-tsosi/",
            },
        ]
    )

    assert news.refresh_news() == 3

    items = list(NewsItem.objects.order_by("position"))
    assert [i.board_item_id for i in items] == ["N1", "L1", "B1"]
    newsletter, linkedin, blog = items
    assert newsletter.kind == "newsletter"
    assert newsletter.title == ""
    assert newsletter.text == "New providers\nHub launch"
    # The header image of the newsletter, copied from the storage
    assert newsletter.image.name.startswith("news/N1/image")
    assert newsletter.image_source_url.startswith("newsletters/")
    assert newsletter.url == (
        f"https://tsosi.org/pages/newsletter/{RECENT:%Y-%m}"
    )
    assert linkedin.kind == "linkedin"
    assert linkedin.title == "KU Leuven"
    assert linkedin.text == "KU Leuven joins TSOSI!"
    assert linkedin.url == RECENT_POST_URL
    assert linkedin.date == RECENT
    assert linkedin.image_alt == "Logo"
    assert linkedin.image.name.startswith("news/L1/image")
    assert blog.kind == "blog"
    assert blog.title == "ROR hierarchy"
    assert blog.text == "TSOSI has integrated ROR!"
    assert blog.url == "https://tsosi.org/pages/blog/ror-hierarchy/"
    assert len([d for d in fake.downloads if d.endswith("a.png")]) == 1

    # Images are downloaded only when they change, removed cards deleted
    fake.cards = [linkedin_card("L1", "Live", image=image)]
    assert news.refresh_news() == 1
    assert len([d for d in fake.downloads if d.endswith("a.png")]) == 1
    linkedin.refresh_from_db()
    assert linkedin.position == 0 and linkedin.image
    assert NewsItem.objects.count() == 1

    fake.cards = [linkedin_card("L1", "Live")]
    news.refresh_news()
    linkedin.refresh_from_db()
    assert not linkedin.image and linkedin.image_source_url is None


@pytest.mark.django_db
def test_refresh_news_skips_invalid_cards(fake_github):
    fake_github(
        [
            {"id": "X1", "status": "Live", "title": "No link"},
            {
                "id": "X2",
                "status": "Live",
                "title": "Unknown post",
                "body": "https://tsosi.org/pages/blog/unknown/",
            },
            {
                "id": "O1",
                "status": "Live",
                "title": "PKP joins TSOSI",
                "body": "https://pkp.sfu.ca/pkp-joins-tsosi/\n\nA blog post"
                "\n\n![img](https://x.org/broken.jpg)",
            },
        ]
    )
    assert news.refresh_news() == 1
    item = NewsItem.objects.get()
    assert item.kind == "other"
    assert item.title == "PKP joins TSOSI"
    assert item.text == "A blog post"
    # Without a Date section: the card creation date
    assert item.date == datetime(2026, 1, 1, tzinfo=UTC)
    # Failed image download: retried at the next refresh
    assert not item.image and item.image_source_url is None


@pytest.mark.django_db
def test_refresh_news_proposes_candidates(fake_github):
    issues = [
        {
            "node_id": "I_new",
            "html_url": "https://github.com/tsosi-org/newsletter/issues/30",
            "title": "[LinkedIn] KU Leuven",
            "body": issue_form_body(url=RECENT_POST_URL),
            "updated_at": NOW.isoformat(),
        },
        {
            # Not published yet
            "node_id": "I_draft",
            "html_url": "https://github.com/tsosi-org/newsletter/issues/31",
            "title": "[LinkedIn] Draft",
            "body": issue_form_body(),
            "updated_at": NOW.isoformat(),
        },
        {
            "node_id": "PR",
            "html_url": "https://github.com/tsosi-org/newsletter/pull/32",
            "title": "PR",
            "body": RECENT_POST_URL,
            "pull_request": {},
        },
    ]
    fake = fake_github(
        [
            # Already on the board: not proposed again
            {
                "id": "B1",
                "status": "Archived",
                "title": "Blog",
                "body": "https://tsosi.org/pages/blog/ror-hierarchy",
            }
        ],
        issues,
    )

    news.refresh_news()

    # An issue for the recent newsletter only: the old one and the old blog
    # post are too old, the recent blog post is on the board.
    newsletter_link = f"https://tsosi.org/pages/newsletter/{RECENT:%Y-%m}"
    assert len(fake.created_issues) == 1
    issue = fake.created_issues[0]
    assert issue["title"] == f"[Newsletter] {RECENT:%B %Y}"
    assert news.card_link(issue["title"], issue["body"]) == newsletter_link
    assert news.card_text(issue["body"]) == ""
    added = [v for q, v in fake.mutations if "addProjectV2ItemById" in q]
    assert added == [
        {"project": "PROJECT", "content": "I_created1"},
        {"project": "PROJECT", "content": "I_new"},
    ]
    statuses = [v for q, v in fake.mutations if "updateProjectV2Item" in q]
    assert [(s["item"], s["option"]) for s in statuses] == [
        ("ITEM_I_created1", "OPT_C"),
        ("ITEM_I_new", "OPT_C"),
    ]
    assert set(NewsProposal.objects.values_list("url", flat=True)) == {
        f"https://tsosi.org/pages/newsletter/{RECENT:%Y-%m}",
        "https://tsosi.org/pages/blog/ror-hierarchy",
        news.normalize_url(RECENT_POST_URL),
    }

    # Deleted cards are not proposed again
    fake.mutations.clear()
    news.refresh_news()
    assert fake.mutations == [] and len(fake.created_issues) == 1


@pytest.mark.django_db
def test_refresh_news_proposal_failure_keeps_refresh(fake_github, mocker):
    fake_github(
        [
            {
                "id": "B1",
                "status": "Live",
                "title": "Blog",
                "body": "https://tsosi.org/pages/blog/ror-hierarchy/",
            }
        ]
    )
    mocker.patch.object(
        news, "propose_candidates", side_effect=news.NewsError("Boom")
    )
    assert news.refresh_news() == 1


@pytest.mark.django_db
def test_refresh_news_board_failure_keeps_news(fake_github, mocker):
    fake_github([])
    NewsItem.objects.create(
        board_item_id="B1", position=0, kind="other", url="https://x.org"
    )
    mocker.patch.object(
        news.requests, "post", return_value=FakeResponse(status_code=502)
    )
    with pytest.raises(news.GitHubError):
        news.refresh_news()
    assert NewsItem.objects.count() == 1


@pytest.mark.django_db
def test_refresh_news_not_configured(settings, mocker):
    settings.TSOSI_NEWS_BOARD = None
    fetch_blog = mocker.patch.object(news, "fetch_blog")
    refresh_newsletters = mocker.patch.object(news, "refresh_newsletters")
    post = mocker.patch.object(news.requests, "post")
    assert news.refresh_news() == 0
    fetch_blog.assert_called_once()
    # Anonymously
    assert refresh_newsletters.call_args.args[0].token is None
    post.assert_not_called()


@pytest.mark.django_db
def test_news_view(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    NewsItem.objects.create(
        board_item_id="B",
        position=1,
        kind="blog",
        title="Post",
        url="https://tsosi.org/pages/blog/a/",
        date=datetime(2026, 3, 18, tzinfo=UTC),
    )
    NewsItem.objects.create(
        board_item_id="L",
        position=0,
        kind="linkedin",
        text="News",
        url=RECENT_POST_URL,
    )
    response = Client().get("/api/news")
    assert response.status_code == 200
    assert response.json() == [
        {
            "kind": "linkedin",
            "title": "",
            "text": "News",
            "url": RECENT_POST_URL,
            "date": None,
            "image": None,
            "image_alt": "",
        },
        {
            "kind": "blog",
            "title": "Post",
            "text": "",
            "url": "https://tsosi.org/pages/blog/a/",
            "date": "2026-03-18T00:00:00+00:00",
            "image": None,
            "image_alt": "",
        },
    ]


def test_fetch_blog(settings, tmp_path, mocker):
    from tsosi.data import blog

    settings.TSOSI_PUBLIC_RELPATH = str(tmp_path)
    package = io.BytesIO()
    with tarfile.open(fileobj=package, mode="w") as tar:
        data = b'{"posts": []}'
        info = tarfile.TarInfo("./index.json")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    get = mocker.patch.object(
        blog.requests,
        "get",
        return_value=FakeResponse(content=package.getvalue()),
    )
    blog.fetch_blog()
    get.assert_called_once_with(blog.BLOG_PKG_URL, timeout=60)
    assert (tmp_path / "pages/blog/index.json").read_bytes() == data
