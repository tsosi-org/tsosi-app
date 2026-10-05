"""
python -m tsosi.data.infra_curation 304             # one issue
python -m tsosi.data.infra_curation                 # all open [Infra curation] issues
python -m tsosi.data.infra_curation 304 --dry-run   # print instead of posting
"""

import argparse
import logging
import os
import sys

from github import Auth, Github
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.Repository import Repository

from .curation import BOT_MARKER, curate
from .ticket import TITLE_PREFIX, Ticket, is_curation_issue

logger = logging.getLogger("infra_curation")

DEFAULT_REPO = "tsosi-org/tsosi-app"


def find_bot_comment(issue: Issue) -> IssueComment | None:
    return next(
        (c for c in issue.get_comments() if BOT_MARKER in (c.body or "")),
        None,
    )


def process(
    repo: str, issue: Issue, comment: IssueComment | None, dry_run: bool
) -> None:
    """
    Create the bot comment of the issue, or update the existing one.
    """
    body = curate(Ticket(repo, issue.number, issue.title, issue.body))
    if dry_run:
        print(f"--- {repo}#{issue.number}: {issue.title}\n{body}")
        return
    if comment is None:
        issue.create_comment(body)
        status = "created"
    elif comment.body.strip() == body.strip():
        status = "unchanged"
    else:
        comment.edit(body)
        status = "updated"
    logger.info(f"{repo}#{issue.number}: comment {status}")


def process_all(repo: Repository, force: bool, dry_run: bool) -> int:
    """
    Process the open curation issues, skipping the ones already commented
    by the bot unless `force` is set.
    """
    issues = [
        i
        for i in repo.get_issues(state="open")
        if i.pull_request is None and is_curation_issue(i.title)
    ]
    logger.info(f"Found {len(issues)} {TITLE_PREFIX} issues")
    failures = 0
    for issue in issues:
        try:
            comment = find_bot_comment(issue)
            if comment and not force:
                logger.info(
                    f"{repo.full_name}#{issue.number}: already commented"
                )
                continue
            process(repo.full_name, issue, comment, dry_run)
        except Exception:
            failures += 1
            logger.exception(f"{repo.full_name}#{issue.number}: failed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tsosi.data.infra_curation",
        description="The repository and the token are read from the "
        f"GITHUB_REPOSITORY (default: {DEFAULT_REPO}) and GITHUB_TOKEN "
        "env variables.",
    )
    parser.add_argument(
        "issue",
        nargs="?",
        type=int,
        help=f"Issue number. Defaults to all the open {TITLE_PREFIX} issues.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="When processing all the issues, also update the ones already "
        "commented by the bot.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the comments instead of posting them.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    token = os.environ.get("GITHUB_TOKEN")
    gh = Github(auth=Auth.Token(token)) if token else Github()
    repo = gh.get_repo(os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO))
    if args.issue is None:
        return process_all(repo, args.force, args.dry_run)
    issue = repo.get_issue(args.issue)
    process(repo.full_name, issue, find_bot_comment(issue), args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
