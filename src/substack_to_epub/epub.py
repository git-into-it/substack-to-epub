import datetime
import hashlib
import mimetypes
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
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


def _embed_images(
    html_fragment: str, book: epub.EpubBook, image_cache: dict[str, str]
) -> str:
    """Download images referenced in *html_fragment*, embed them in *book*,
    and rewrite src attributes to local EPUB paths.

    *image_cache* maps remote URL → local EPUB path to avoid re-downloading
    the same image across posts.
    """
    soup = BeautifulSoup(html_fragment, "lxml")
    changed = False

    for tag in soup.find_all("img", src=True):
        url = tag["src"]
        if not url.startswith(("http://", "https://")):
            continue

        if url not in image_cache:
            try:
                resp = requests.get(url, timeout=15)
                if not resp.ok:
                    continue

                # Derive extension from URL, fall back to Content-Type
                ext = url.rsplit(".", 1)[-1].split("?")[0].lower()
                if not ext or len(ext) > 5:
                    ct = resp.headers.get("Content-Type", "")
                    guessed = mimetypes.guess_extension(ct.split(";")[0].strip())
                    ext = (guessed or ".jpg").lstrip(".")

                url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
                local_path = f"images/img-{url_hash}.{ext}"

                img_item = epub.EpubImage()
                img_item.file_name = local_path
                img_item.media_type = (
                    resp.headers.get("Content-Type", f"image/{ext}")
                    .split(";")[0]
                    .strip()
                )
                img_item.content = resp.content
                book.add_item(img_item)

                image_cache[url] = local_path
            except Exception:
                continue  # leave external URL if download fails

        if url in image_cache:
            tag["src"] = image_cache[url]
            changed = True

    if not changed:
        return html_fragment

    body = soup.find("body")
    if body:
        return "".join(str(child) for child in body.children)
    return str(soup)


def _xhtml_document(post: dict, content: str) -> str:
    """Wrap *content* (HTML fragment) in a complete XHTML document."""
    title = _escape_xml(post.get("title") or "Untitled")
    date_str = _format_date(post.get("post_date") or "")
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


def post_to_xhtml(post: dict, base_url: str) -> str:
    """Return a complete XHTML document string for one post."""
    body_html = post.get("body_html") or ""
    content = clean_html(body_html, base_url)
    return _xhtml_document(post, content)


def build_epub(posts: list[dict], title: str, output_path: str | Path) -> None:
    """Assemble and write an EPUB file from *posts*."""
    output_path = Path(output_path)
    book = epub.EpubBook()
    book.set_identifier(f"substack-{re.sub(r'[^a-z0-9]', '-', title.lower())}")
    book.set_title(title)
    book.set_language("en")

    chapters: list[epub.EpubHtml] = []
    image_cache: dict[str, str] = {}  # remote URL → local EPUB path

    for i, post in enumerate(posts, start=1):
        post_title = post.get("title") or f"Chapter {i}"
        base_url = post.get("canonical_url") or ""
        body_html = post.get("body_html") or ""
        slug = post.get("slug") or f"chapter-{i}"

        content = clean_html(body_html, base_url)
        content = _embed_images(content, book, image_cache)
        xhtml = _xhtml_document(post, content)

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
