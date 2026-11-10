"""
Latest news of the home page, picked by the TSOSI team on a GitHub project
board, "Homepage news" (setting `TSOSI_NEWS_BOARD`).
"""

import logging
import mimetypes
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

import requests
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from tsosi.app_settings import app_settings
from tsosi.models import NewsItem, Newsletter, NewsProposal

from .blog import fetch_blog, read_blog_index
from .github_api import GitHubClient, GitHubError
from .newsletters import refresh_newsletters

logger = logging.getLogger(__name__)

# Links of the blog posts and newsletters on the board, whatever the server
# that adds them (the home page only uses their path).
TSOSI_URL = "https://tsosi.org"


class NewsError(GitHubError):
    pass


BOARD_QUERY = """
query($owner: String!, $number: Int!, $cursor: String) {
  organization(login: $owner) {
    projectV2(number: $number) {
      id
      field(name: "Status") {
        ... on ProjectV2SingleSelectField { id options { id name } }
      }
      items(
        first: 100, after: $cursor,
        orderBy: {field: POSITION, direction: ASC}
      ) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isArchived
          status: fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue { name }
          }
          content {
            __typename
            ... on DraftIssue { title body createdAt }
            ... on Issue { title body url createdAt }
          }
        }
      }
    }
  }
}
"""

ADD_ITEM_MUTATION = """
mutation($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
    item { id }
  }
}
"""

SET_STATUS_MUTATION = """
mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $project, itemId: $item, fieldId: $field,
    value: {singleSelectOptionId: $option}
  }) { projectV2Item { id } }
}
"""


def fetch_board(client: GitHubClient) -> dict:
    """
    The board's `id`, `status_field` (`id` and `options` by name) and
    `cards`, in the board order. Each card has its item `id`, `status`,
    `type` (`DraftIssue` or `Issue`), `title`, `body`, `url` (issues only)
    and `created_at`.
    """
    config = client.config
    cards = []
    cursor = None
    while True:
        data = client.graphql(
            BOARD_QUERY,
            {
                "owner": config["owner"],
                "number": int(config["project_number"]),
                "cursor": cursor,
            },
        )
        project = (data.get("organization") or {}).get("projectV2")
        if project is None:
            raise NewsError(
                f"GitHub project {config['owner']}/"
                f"{config['project_number']} not found."
            )
        for node in project["items"]["nodes"]:
            content = node.get("content") or {}
            if node.get("isArchived") or content.get("__typename") not in (
                "DraftIssue",
                "Issue",
            ):
                continue
            cards.append(
                {
                    "id": node["id"],
                    "status": (node.get("status") or {}).get("name"),
                    "type": content["__typename"],
                    "title": content.get("title") or "",
                    "body": content.get("body") or "",
                    "url": content.get("url"),
                    "created_at": parse_datetime(content.get("createdAt")),
                }
            )
        page_info = project["items"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    field = project.get("field")
    if not field:
        raise NewsError("The board has no `Status` single select field.")
    return {
        "id": project["id"],
        "status_field": {
            "id": field["id"],
            "options": {o["name"]: o["id"] for o in field["options"]},
        },
        "cards": cards,
    }


def stored_newsletters() -> list[dict]:
    """The stored newsletters, latest first: `id`, `date`, `key_points`."""
    return [
        {"id": n.name, "date": n.date, "key_points": n.key_points}
        for n in Newsletter.objects.order_by("-date")
    ]


def fetch_linkedin_issues(client: GitHubClient, since: datetime) -> list[dict]:
    """
    The issues of `linkedin_repos` updated since `since` that have a
    LinkedIn post URL, with their `node_id`, `url`, `linkedin_url` and
    `date` (of the post if known, else of the issue update).
    """
    issues = []
    for repo in client.config["linkedin_repos"]:
        page = 1
        while True:
            batch = client.rest_get(
                f"repos/{repo}/issues",
                {
                    "state": "all",
                    "since": since.isoformat(),
                    "per_page": 100,
                    "page": page,
                },
            )
            for issue in batch:
                if "pull_request" in issue:
                    continue
                link = card_link(issue.get("title") or "", issue.get("body"))
                if link is None or link_kind(link) != NewsItem.KIND_LINKEDIN:
                    continue
                issues.append(
                    {
                        "node_id": issue["node_id"],
                        "url": issue["html_url"],
                        "linkedin_url": link,
                        "date": linkedin_post_date(link)
                        or parse_datetime(issue.get("updated_at")),
                    }
                )
            if len(batch) < 100:
                break
            page += 1
    return issues


## Card parsing
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*(https?://[^\s)]+)[^)]*\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HTML_ATTR_RE = r"\b{}\s*=\s*[\"']([^\"']*)[\"']"
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*https?://[^)]*\)")
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
# Placeholder of an empty optional field in issue forms
NO_RESPONSE = "_No response_"
LINK_SECTIONS = ["linkedin url", "link"]
TEXT_SECTIONS = ["post text", "text"]
# Tag at the start of an issue title, ex: `[News] `
TITLE_TAG_RE = re.compile(r"^\s*\[[^\]]*\]\s*")
# LinkedIn post IDs embed their creation time, like Twitter's snowflake IDs
LINKEDIN_POST_URL_RE = re.compile(
    r"https?://(?:[\w-]+\.)?linkedin\.com/(?:posts|feed/update)/[^\s<>()\[\]\"'`]+"
)
LINKEDIN_ID_RE = re.compile(r"(?:activity|share|ugcPost)[:-](\d{16,20})")


def card_sections(body: str) -> dict[str, str]:
    """The `### Heading` sections of a card body, by lowercase heading."""
    parts = SECTION_RE.split(body)
    sections = {}
    # parts = [before, heading 1, content 1, heading 2, content 2, ...]
    for heading, content in zip(parts[1::2], parts[2::2]):
        content = content.strip()
        sections[heading.strip().lower()] = (
            "" if content == NO_RESPONSE else content
        )
    return sections


def card_images(body: str) -> list[tuple[str, str]]:
    """The `(url, alt)` of the images of a card body, in order."""
    images = []
    for match in re.finditer(
        f"{MD_IMAGE_RE.pattern}|{HTML_IMAGE_RE.pattern}", body, re.IGNORECASE
    ):
        if match.group(2):
            images.append((match.group(2), match.group(1)))
            continue
        tag = match.group(0)
        src = re.search(HTML_ATTR_RE.format("src"), tag, re.IGNORECASE)
        alt = re.search(HTML_ATTR_RE.format("alt"), tag, re.IGNORECASE)
        if src:
            images.append((src.group(1), alt.group(1) if alt else ""))
    return images


def strip_images(text: str) -> str:
    return HTML_IMAGE_RE.sub("", MD_IMAGE_RE.sub("", text))


def first_url(text: str) -> str | None:
    match = URL_RE.search(text)
    return match.group(0).rstrip(".,;:!?") if match else None


def card_link(title: str, body: str | None) -> str | None:
    """
    The link of a card: its link section if it has one, else the first link
    of its title, else the first LinkedIn post link of its body, else its
    first link.
    """
    body = strip_images(HTML_COMMENT_RE.sub("", body or ""))
    sections = card_sections(body)
    for name in LINK_SECTIONS:
        if name in sections:
            # Empty until the post is published (LinkedIn post issue form)
            return first_url(sections[name])
    if url := first_url(title):
        return url
    if match := LINKEDIN_POST_URL_RE.search(body):
        return match.group(0).rstrip(".,;:!?")
    return first_url(body)


def card_text(body: str | None) -> str:
    """Plain text of a card, paragraphs separated by blank lines."""
    body = HTML_COMMENT_RE.sub("", body or "")
    sections = card_sections(body)
    for name in TEXT_SECTIONS:
        if name in sections:
            text = sections[name]
            break
    else:
        # Cards made with sections but none for the text: the text before.
        text = SECTION_RE.split(body)[0] if sections else body
    text = MD_LINK_RE.sub(r"\1", strip_images(text))
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    lines = [
        line.strip()
        for line in text.splitlines()
        if not URL_RE.fullmatch(line.strip())
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def link_kind(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return NewsItem.KIND_LINKEDIN
    tsosi_hosts = {
        "tsosi.org",
        "www.tsosi.org",
        urlsplit(app_settings.FRONTEND_URL).hostname,
    }
    if host in tsosi_hosts:
        if re.match(r"^/pages/blog/[^/]+", parts.path):
            return NewsItem.KIND_BLOG
        if re.match(r"^/pages/newsletter/[^/]+", parts.path):
            return NewsItem.KIND_NEWSLETTER
    return NewsItem.KIND_OTHER


def page_id(url: str) -> str:
    """ID of a blog post or newsletter: `/pages/<blog|newsletter>/<id>`."""
    return urlsplit(url).path.split("/")[3]


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    return urlunsplit(("https", parts.netloc.lower(), path, "", ""))


def linkedin_post_date(url: str) -> datetime | None:
    match = LINKEDIN_ID_RE.search(url)
    if not match:
        return None
    # The first 41 bits of the 64-bit ID are the Unix time in milliseconds.
    date = datetime.fromtimestamp((int(match.group(1)) >> 22) / 1000, tz=UTC)
    if not datetime(2003, 1, 1, tzinfo=UTC) < date < timezone.now():
        return None
    return date


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def blog_url(post_id: str) -> str:
    return f"{TSOSI_URL}/pages/blog/{post_id}/"


def newsletter_url(newsletter_id: str) -> str:
    return f"{TSOSI_URL}/pages/newsletter/{newsletter_id}"


def newsletter_title(date: datetime) -> str:
    return f"Newsletter {date.strftime('%B %Y')}"


## Candidates
def propose_candidates(
    client: GitHubClient,
    board: dict,
    blog_posts: list[dict],
    newsletters: list[dict],
) -> int:
    """
    Add the recent blog posts, newsletters and LinkedIn posts that were
    never proposed to the `Candidates` column. Return the number of cards
    added.
    """
    config = client.config
    option_id = board["status_field"]["options"].get(
        config["candidates_status"]
    )
    if option_id is None:
        raise NewsError(
            f"The board has no `{config['candidates_status']}` status."
        )

    on_board = {c["url"] for c in board["cards"] if c["url"]}
    for card in board["cards"]:
        if link := card_link(card["title"], card["body"]):
            on_board.add(normalize_url(link))
    proposed = set(NewsProposal.objects.values_list("url", flat=True))
    since = timezone.now() - timedelta(days=config["propose_days"])

    # (news URL, issue title, issue node ID if it exists)
    candidates: list[tuple[str, str, str | None]] = []
    for post in blog_posts:
        if post["date"] >= since:
            title = f"[Blog] {post['title']}"
            candidates.append((blog_url(post["id"]), title, None))
    for newsletter in newsletters:
        if newsletter["date"] >= since:
            title = f"[Newsletter] {newsletter['date']:%B %Y}"
            candidates.append((newsletter_url(newsletter["id"]), title, None))
    for issue in fetch_linkedin_issues(client, since):
        if issue["url"] in on_board:
            NewsProposal.objects.get_or_create(
                url=normalize_url(issue["linkedin_url"])
            )
            continue
        if issue["date"] is not None and issue["date"] >= since:
            candidates.append((issue["linkedin_url"], "", issue["node_id"]))

    added = 0
    for url, title, issue_id in candidates:
        key = normalize_url(url)
        if key in proposed:
            continue
        if key not in on_board:
            if issue_id is None:
                issue_id = create_news_issue(client, title, url)
            data = client.graphql(
                ADD_ITEM_MUTATION,
                {"project": board["id"], "content": issue_id},
            )
            item_id = data["addProjectV2ItemById"]["item"]["id"]
            client.graphql(
                SET_STATUS_MUTATION,
                {
                    "project": board["id"],
                    "item": item_id,
                    "field": board["status_field"]["id"],
                    "option": option_id,
                },
            )
            added += 1
            logger.info(f"Proposed news on the board: {url}")
        NewsProposal.objects.create(url=key)
        proposed.add(key)
    return added


def create_news_issue(client: GitHubClient, title: str, url: str) -> str:
    """
    Create the issue of a blog post or newsletter, in the sections of the
    "Homepage news" issue form. Return its node ID.
    """
    if link_kind(url) == NewsItem.KIND_NEWSLETTER:
        what = "newsletter"
    else:
        what = "blog post"
    body = (
        f"### Link\n\n{url}\n\n### Notes\n\nAdded by tsosi.org. The home "
        f"page shows the title, summary and date of the {what} once this "
        'issue is in the **Live** column of the "Homepage news" board.\n'
    )
    issue = client.rest_post(
        f"repos/{client.config['issue_repo']}/issues",
        {"title": title, "body": body},
    )
    return issue["node_id"]


## Home page news
def build_news_item(
    client: GitHubClient,
    card: dict,
    blog_posts: list[dict],
    newsletters: list[dict],
) -> dict | None:
    """The data of the news shown for a card, `None` if it can't be shown."""
    link = card_link(card["title"], card["body"])
    if link is None:
        logger.warning(f"Skipped news card without link: {card['title']}")
        return None
    kind = link_kind(link)
    data = {
        "kind": kind,
        "title": "",
        "text": "",
        "url": link,
        "date": None,
        "image_source_url": None,
        "image_alt": "",
    }

    if kind == NewsItem.KIND_BLOG:
        post = next((p for p in blog_posts if p["id"] == page_id(link)), None)
        if post is None:
            logger.warning(f"Skipped news card of unknown blog post: {link}")
            return None
        data |= {
            "title": post["title"],
            "text": post["summary"],
            "url": blog_url(post["id"]),
            "date": post["date"],
        }
        return data

    if kind == NewsItem.KIND_NEWSLETTER:
        newsletter = next(
            (n for n in newsletters if n["id"] == page_id(link)), None
        )
        if newsletter is None:
            logger.warning(f"Skipped news card of unknown newsletter: {link}")
            return None
        data |= {
            "title": newsletter_title(newsletter["date"]),
            "text": " · ".join(newsletter["key_points"]),
            "url": newsletter_url(newsletter["id"]),
            "date": newsletter["date"],
        }
        return data

    images = card_images(card["body"])
    if images:
        data["image_source_url"], data["image_alt"] = images[0]
    data["text"] = card_text(card["body"])
    if kind == NewsItem.KIND_LINKEDIN:
        data["date"] = linkedin_post_date(link) or card["created_at"]
    else:
        data["title"] = card_title(card["title"], card["body"])
    return data


def card_title(title: str, body: str | None) -> str:
    """
    The `Title` section of a card, else its title without its tag
    (ex: `[News] `), unless it is a link.
    """
    sections = card_sections(HTML_COMMENT_RE.sub("", body or ""))
    if sections.get("title"):
        return " ".join(sections["title"].split())
    if first_url(title) is not None:
        return ""
    return TITLE_TAG_RE.sub("", title).strip()


def download_image(client: GitHubClient, url: str) -> ContentFile | None:
    try:
        resp = client.download(url)
    except requests.RequestException as e:
        logger.warning(f"Failed to download news image {url}: {e}")
        return None
    content_type = resp.headers.get("Content-Type", "").split(";")[0]
    if not content_type.startswith("image/"):
        logger.warning(f"News image {url} is not an image: {content_type}")
        return None
    extension = mimetypes.guess_extension(content_type) or ".jpg"
    return ContentFile(resp.content, name=f"image{extension}")


def store_news_items(
    client: GitHubClient,
    board: dict,
    blog_posts: list[dict],
    newsletters: list[dict],
) -> int:
    """
    Replace the stored news with the cards of the `Live` column.
    Images are downloaded only for new or changed ones. Return the number of
    news stored.
    """
    config = client.config
    cards = [c for c in board["cards"] if c["status"] == config["shown_status"]]
    items = []
    for card in cards:
        data = build_news_item(client, card, blog_posts, newsletters)
        if data is not None:
            items.append((card["id"], data))
        if len(items) >= config["max_items"]:
            break

    existing = {i.board_item_id: i for i in NewsItem.objects.all()}
    images = {}
    for card_id, data in items:
        source = data["image_source_url"]
        current = existing.get(card_id)
        if source is not None and (
            current is None
            or current.image_source_url != source
            or not current.image
        ):
            images[card_id] = download_image(client, source)

    with transaction.atomic():
        for position, (card_id, data) in enumerate(items):
            item = existing.pop(card_id, None) or NewsItem(
                board_item_id=card_id
            )
            image_changed = item.image_source_url != data["image_source_url"]
            if item.image and (image_changed or card_id in images):
                item.image.delete(save=False)
            for field, value in data.items():
                setattr(item, field, value)
            item.position = position
            if image_file := images.get(card_id):
                item.image.save(image_file.name, image_file, save=False)
            elif card_id in images:
                # Failed download: retried at the next refresh.
                item.image_source_url = None
            item.save()

        for item in existing.values():
            if item.image:
                item.image.delete(save=False)
            item.delete()

    logger.info(f"Refreshed {len(items)} home page news.")
    return len(items)


## Workflow
def refresh_news() -> int:
    """
    Download the blog and the newsletters, propose the new news on the board
    and store the news shown on the home page. Return the number of news shown.
    """
    try:
        fetch_blog()
    except (requests.RequestException, OSError) as e:
        logger.warning(f"Failed to fetch the blog: {e}")

    config = app_settings.NEWS_BOARD
    # Anonymous without board: the newsletter repository is public.
    client = GitHubClient(config)
    try:
        refresh_newsletters(client)
    except GitHubError as e:
        logger.error(f"Failed to refresh the newsletters: {e}")

    if config is None:
        logger.info("The news board is not configured, skipping news refresh.")
        return 0

    board = fetch_board(client)
    blog_posts = read_blog_index()
    newsletters = stored_newsletters()
    try:
        propose_candidates(client, board, blog_posts, newsletters)
    except GitHubError as e:
        # The news shown are still refreshed.
        logger.error(f"Failed to propose news on the board: {e}")
    return store_news_items(client, board, blog_posts, newsletters)
