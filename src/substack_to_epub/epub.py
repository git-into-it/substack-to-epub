import datetime
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from ebooklib import epub

# Substack-specific CSS classes / identifiers that are UI chrome, not content.
_PAYWALL_SELECTORS = [
    ".paywall",
    ".subscribe-widget",
    ".subscription-widget",
    ".paywall-prompt",
    "div[class*='paywall']",
    "div[class*='subscribe']",
    "div[class*='wall']",
    ".post-upsell",
    ".footer-subscribe",
]


def clean_html(raw_html: str, base_url: str) -> str:
    """Strip non-content elements and fix relative URLs.

    Returns a clean HTML *fragment* (no <html>/<body> wrapper).
    """
    soup = BeautifulSoup(raw_html or "", "lxml")

    # Remove script / style / iframe
    for tag in soup.find_all(["script", "style", "iframe"]):
        tag.decompose()

    # Remove paywall / subscribe divs
    for selector in _PAYWALL_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # Fix relative URLs on <a href> and <img src>
    for tag in soup.find_all("a", href=True):
        tag["href"] = urljoin(base_url, tag["href"])
    for tag in soup.find_all("img", src=True):
        tag["src"] = urljoin(base_url, tag["src"])

    # Return the inner content (lxml wraps in <html><body>)
    body = soup.find("body")
    if body:
        return "".join(str(child) for child in body.children)
    return str(soup)


def post_to_xhtml(post: dict, base_url: str) -> str:
    """Return a complete XHTML document string for one post."""
    title = _escape_xml(post.get("title") or "Untitled")
    date_str = _format_date(post.get("post_date") or "")
    body_html = post.get("body_html") or ""
    content = clean_html(body_html, base_url)

    return (
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        "<head>\n"
        f"  <title>{title}</title>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>{title}</h1>\n"
        f"  <p><em>{date_str}</em></p>\n"
        f"  {content}\n"
        "</body>\n"
        "</html>\n"
    )


def build_epub(posts: list[dict], title: str, output_path: str | Path) -> None:
    """Assemble and write an EPUB file from *posts*."""
    output_path = Path(output_path)
    book = epub.EpubBook()
    book.set_identifier(f"substack-{re.sub(r'[^a-z0-9]', '-', title.lower())}")
    book.set_title(title)
    book.set_language("en")

    chapters: list[epub.EpubHtml] = []

    for i, post in enumerate(posts, start=1):
        post_title = post.get("title") or f"Chapter {i}"
        base_url = post.get("canonical_url") or ""
        xhtml = post_to_xhtml(post, base_url)
        slug = post.get("slug") or f"chapter-{i}"
        chapter = epub.EpubHtml(
            title=post_title,
            file_name=f"{slug}.xhtml",
            lang="en",
        )
        chapter.content = xhtml
        book.add_item(chapter)
        chapters.append(chapter)

    # Try to set cover image from the first post that has one
    for post in posts:
        cover_url = post.get("cover_image")
        if cover_url:
            try:
                import requests

                resp = requests.get(cover_url, timeout=15)
                if resp.ok:
                    ext = cover_url.rsplit(".", 1)[-1].split("?")[0].lower()
                    book.set_cover(f"cover.{ext}", resp.content, create_page=True)
            except Exception:
                pass  # cover is optional
            break

    book.toc = tuple(epub.Link(c.file_name, c.title, c.file_name) for c in chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub.write_epub(str(output_path), book)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _format_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%B %-d, %Y")
    except ValueError:
        return date_str
