import re
from urllib.parse import urlparse

import requests


class SubstackError(Exception):
    pass


class AuthError(SubstackError):
    pass


class NetworkError(SubstackError):
    pass


_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_ARCHIVE_PAGE_SIZE = 12


class SubstackClient:
    def __init__(self, base_url: str):
        parsed = urlparse(base_url)
        # Normalise to scheme + netloc only, strip trailing slash
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.api_base = f"{self.base_url}/api/v1"
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _USER_AGENT})

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> None:
        """Authenticate via Substack's login API.  Session cookie is retained."""
        url = "https://substack.com/api/v1/login"
        payload = {"email": email, "password": password, "for_pub": ""}
        try:
            resp = self._session.post(url, json=payload, timeout=30)
        except requests.RequestException as exc:
            raise NetworkError(f"Login request failed: {exc}") from exc

        if resp.status_code == 401:
            raise AuthError("Invalid email or password")
        if not resp.ok:
            raise AuthError(f"Login failed with status {resp.status_code}: {resp.text[:200]}")

    def set_cookie(self, value: str) -> None:
        """Inject a substack.sid cookie into the session."""
        self._session.cookies.set("substack.sid", value, domain="substack.com")

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def get_all_posts(self, limit: int | None = None) -> list[dict]:
        """Return newsletter posts from the archive, newest first.

        Paginates until exhausted or *limit* posts have been collected.
        """
        posts: list[dict] = []
        offset = 0

        while True:
            fetch_size = _ARCHIVE_PAGE_SIZE
            if limit is not None:
                remaining = limit - len(posts)
                if remaining <= 0:
                    break
                fetch_size = min(_ARCHIVE_PAGE_SIZE, remaining)

            url = f"{self.api_base}/archive"
            params = {"sort": "new", "offset": offset, "limit": fetch_size}
            try:
                resp = self._session.get(url, params=params, timeout=30)
                resp.raise_for_status()
            except requests.HTTPError as exc:
                raise NetworkError(f"Archive fetch failed: {exc}") from exc
            except requests.RequestException as exc:
                raise NetworkError(f"Network error: {exc}") from exc

            page: list[dict] = resp.json()
            newsletter_posts = [p for p in page if p.get("type") == "newsletter"]
            posts.extend(newsletter_posts)

            if len(page) < _ARCHIVE_PAGE_SIZE:
                break  # last page
            offset += len(page)

        return posts[:limit] if limit is not None else posts

    def fetch_post_content(self, post: dict) -> dict:
        """Fetch the full post via the posts API to get complete body_html."""
        slug = post.get("slug")
        if not slug:
            raise SubstackError("Post has no slug")

        url = f"{self.api_base}/posts/{slug}"
        try:
            resp = self._session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise NetworkError(f"Post fetch failed ({slug}): {exc}") from exc
        except requests.RequestException as exc:
            raise NetworkError(f"Network error: {exc}") from exc

        return resp.json()

    def fetch_single_post(self, url: str) -> dict:
        """Fetch a single post given its full URL."""
        slug = self._slug_from_url(url)
        return self.fetch_post_content({"slug": slug})

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_single_post_url(url: str) -> bool:
        """Return True when *url* points to an individual post (/p/<slug>)."""
        return bool(re.search(r"/p/[^/]+", urlparse(url).path))

    @staticmethod
    def _slug_from_url(url: str) -> str:
        match = re.search(r"/p/([^/?#]+)", urlparse(url).path)
        if not match:
            raise SubstackError(f"Cannot extract slug from URL: {url}")
        return match.group(1)
