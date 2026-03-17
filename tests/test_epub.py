import zipfile
from pathlib import Path

import pytest

from substack_to_epub.epub import build_epub, clean_html, post_to_xhtml

BASE_URL = "https://example.substack.com"


# ------------------------------------------------------------------
# clean_html
# ------------------------------------------------------------------


def test_clean_html_strips_script():
    html = "<p>Hello</p><script>alert('xss')</script>"
    result = clean_html(html, BASE_URL)
    assert "<script" not in result
    assert "Hello" in result


def test_clean_html_strips_style():
    html = "<p>Hi</p><style>body { color: red; }</style>"
    result = clean_html(html, BASE_URL)
    assert "<style" not in result


def test_clean_html_strips_iframe():
    html = "<p>Text</p><iframe src='https://evil.com'></iframe>"
    result = clean_html(html, BASE_URL)
    assert "<iframe" not in result


def test_clean_html_removes_paywall_div():
    html = '<p>Free part</p><div class="paywall">Subscribe to read more</div>'
    result = clean_html(html, BASE_URL)
    assert "Subscribe to read more" not in result
    assert "Free part" in result


def test_clean_html_fixes_relative_urls():
    html = '<a href="/p/my-post">link</a>'
    result = clean_html(html, BASE_URL)
    assert f"{BASE_URL}/p/my-post" in result


def test_clean_html_fixes_relative_img_src():
    html = '<img src="/images/photo.jpg"/>'
    result = clean_html(html, BASE_URL)
    assert f"{BASE_URL}/images/photo.jpg" in result


def test_clean_html_keeps_absolute_urls():
    html = '<a href="https://other.com/page">link</a>'
    result = clean_html(html, BASE_URL)
    assert "https://other.com/page" in result


def test_clean_html_empty_string():
    result = clean_html("", BASE_URL)
    assert result == ""


# ------------------------------------------------------------------
# build_epub
# ------------------------------------------------------------------

SAMPLE_POST = {
    "title": "Test Post",
    "slug": "test-post",
    "post_date": "2024-01-15T12:00:00Z",
    "body_html": "<p>This is the post content.</p>",
    "canonical_url": BASE_URL + "/p/test-post",
}

SAMPLE_POST_2 = {
    "title": "Second Post",
    "slug": "second-post",
    "post_date": "2024-02-01T10:00:00Z",
    "body_html": "<p>Second post content.</p>",
    "canonical_url": BASE_URL + "/p/second-post",
}


def test_build_epub_creates_file(tmp_path):
    output = tmp_path / "test.epub"
    build_epub([SAMPLE_POST], "Test Book", output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_build_epub_is_valid_zip(tmp_path):
    output = tmp_path / "test.epub"
    build_epub([SAMPLE_POST], "Test Book", output)
    assert zipfile.is_zipfile(output)


def test_build_epub_multiple_posts(tmp_path):
    output = tmp_path / "multi.epub"
    posts = [SAMPLE_POST, SAMPLE_POST_2]
    build_epub(posts, "Multi Book", output)
    assert output.exists()

    # Each post should have its own XHTML file inside the ZIP
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
    xhtml_files = [n for n in names if n.endswith(".xhtml") and "nav" not in n]
    assert len(xhtml_files) >= 2


def test_build_epub_contains_title(tmp_path):
    output = tmp_path / "titled.epub"
    build_epub([SAMPLE_POST], "My Great Book", output)
    with zipfile.ZipFile(output) as zf:
        # Check OPF or content files for the title
        content = " ".join(
            zf.read(name).decode("utf-8", errors="ignore")
            for name in zf.namelist()
            if name.endswith((".opf", ".xhtml", ".ncx"))
        )
    assert "My Great Book" in content


def test_build_epub_string_path(tmp_path):
    output = str(tmp_path / "str_path.epub")
    build_epub([SAMPLE_POST], "Test", output)
    assert Path(output).exists()
