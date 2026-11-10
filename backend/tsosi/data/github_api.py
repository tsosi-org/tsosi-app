"""
Client of GitHub API, authenticated as the GitHub App or with the token of
the `TSOSI_NEWS_BOARD` setting, or anonymous (public data only, 60 requests
per hour).
"""

from urllib.parse import urlsplit

import requests
from github import Auth, Github

GITHUB_API_URL = "https://api.github.com"
REQUEST_TIMEOUT = 30


class GitHubError(Exception):
    pass


class GitHubClient:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._app_auth: Auth.AppInstallationAuth | None = None

    @property
    def token(self) -> str | None:
        if self.config.get("token"):
            return self.config["token"]
        if not self.config.get("app_id"):
            return None
        if self._app_auth is None:
            self._app_auth = Auth.AppInstallationAuth(
                Auth.AppAuth(self.config["app_id"], self.config["private_key"]),
                int(self.config["installation_id"]),
            )
            # Gives the auth the requester it needs to get the token.
            Github(auth=self._app_auth)
        # Installation tokens last 1 hour and are renewed when expired.
        return self._app_auth.token

    def auth_headers(self) -> dict:
        token = self.token
        return {"Authorization": f"Bearer {token}"} if token else {}

    def headers(self) -> dict:
        return {
            **self.auth_headers(),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        try:
            resp = requests.post(
                f"{GITHUB_API_URL}/graphql",
                json={"query": query, "variables": variables or {}},
                headers=self.headers(),
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise GitHubError(f"GitHub GraphQL request failed: {e}") from e
        data = resp.json()
        if data.get("errors"):
            raise GitHubError(f"GitHub GraphQL errors: {data['errors']}")
        return data["data"]

    def rest_get(self, path: str, params: dict | None = None) -> list | dict:
        try:
            resp = requests.get(
                f"{GITHUB_API_URL}/{path}",
                params=params,
                headers=self.headers(),
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise GitHubError(f"GitHub request failed: {path}: {e}") from e
        return resp.json()

    def rest_post(self, path: str, data: dict) -> dict:
        try:
            resp = requests.post(
                f"{GITHUB_API_URL}/{path}",
                json=data,
                headers=self.headers(),
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise GitHubError(f"GitHub request failed: {path}: {e}") from e
        return resp.json()

    def download(self, url: str) -> requests.Response:
        """
        Download a file, with the GitHub token for the files hosted by GitHub
        (images of issues). `requests` drops it on redirects to other hosts.
        """
        headers = {}
        host = urlsplit(url).hostname or ""
        if host == "github.com" or host.endswith(".githubusercontent.com"):
            headers = self.auth_headers()
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
