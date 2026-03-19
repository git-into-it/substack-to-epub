import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from substack_to_epub.epub import build_epub, clean_html

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


def test_clean_html_removes_anchor_tags():
    html = '<a href="/p/my-post">link</a>'
    result = clean_html(html, BASE_URL)
    assert "<a" not in result
    assert "link" in result


def test_clean_html_fixes_relative_img_src():
    html = '<img src="/images/photo.jpg"/>'
    result = clean_html(html, BASE_URL)
    assert f"{BASE_URL}/images/photo.jpg" in result


def test_clean_html_removes_anchor_keeps_text():
    html = '<a href="https://other.com/page">click here</a>'
    result = clean_html(html, BASE_URL)
    assert "<a" not in result
    assert "click here" in result


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


# ------------------------------------------------------------------
# Image embedding
# ------------------------------------------------------------------

IMAGE_URL = "https://example.substack.com/images/photo.jpg"
IMAGE_BYTES = b"\xff\xd8\xff"  # minimal JPEG magic bytes

POST_WITH_IMAGE = {
    "title": "Post With Image",
    "slug": "post-with-image",
    "post_date": "2024-03-01T10:00:00Z",
    "body_html": f'<p>Look at this.</p><img src="{IMAGE_URL}"/>',
    "canonical_url": BASE_URL + "/p/post-with-image",
}


def _mock_get(url, timeout=15):
    resp = MagicMock()
    resp.ok = True
    resp.content = IMAGE_BYTES
    resp.headers = {"Content-Type": "image/jpeg"}
    return resp


def test_build_epub_embeds_images(tmp_path):
    output = tmp_path / "images.epub"
    with patch("substack_to_epub.epub.requests.get", side_effect=_mock_get):
        build_epub([POST_WITH_IMAGE], "Image Book", output)

    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()

    image_files = [n for n in names if "images/img-" in n]
    assert image_files, f"No embedded image found in EPUB; files: {names}"


def test_build_epub_image_src_rewritten(tmp_path):
    output = tmp_path / "images.epub"
    with patch("substack_to_epub.epub.requests.get", side_effect=_mock_get):
        build_epub([POST_WITH_IMAGE], "Image Book", output)

    with zipfile.ZipFile(output) as zf:
        xhtml_names = [n for n in zf.namelist() if n.endswith("post-with-image.xhtml")]
        assert xhtml_names
        xhtml_content = zf.read(xhtml_names[0]).decode("utf-8")

    assert IMAGE_URL not in xhtml_content, "External image URL should be replaced"
    assert "images/img-" in xhtml_content, "Local image path should appear in XHTML"


def test_build_epub_image_deduplication(tmp_path):
    """Same image URL in two posts is downloaded only once."""
    output = tmp_path / "dedup.epub"
    post1 = {**POST_WITH_IMAGE, "slug": "post-one"}
    post2 = {**POST_WITH_IMAGE, "slug": "post-two"}

    call_count = 0

    def counting_get(url, timeout=15):
        nonlocal call_count
        call_count += 1
        return _mock_get(url, timeout)

    with patch("substack_to_epub.epub.requests.get", side_effect=counting_get):
        build_epub([post1, post2], "Dedup Book", output)

    # One call per unique image URL (cover fetch skipped — no cover_image key)
    assert call_count == 1, f"Expected 1 download, got {call_count}"


def test_build_epub_failed_image_download_leaves_external_url(tmp_path):
    """If image download fails, the external URL is preserved (graceful degradation)."""
    output = tmp_path / "fail.epub"

    def failing_get(url, timeout=15):
        resp = MagicMock()
        resp.ok = False
        return resp

    with patch("substack_to_epub.epub.requests.get", side_effect=failing_get):
        build_epub([POST_WITH_IMAGE], "Fail Book", output)

    with zipfile.ZipFile(output) as zf:
        xhtml_names = [n for n in zf.namelist() if n.endswith("post-with-image.xhtml")]
        xhtml_content = zf.read(xhtml_names[0]).decode("utf-8")

    assert IMAGE_URL in xhtml_content, (
        "External URL should be preserved on download failure"
    )
