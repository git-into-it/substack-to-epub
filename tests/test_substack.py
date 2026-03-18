"""Integration tests against a real public Substack publication.

These tests make real HTTP requests. Run with:
    uv run pytest tests/test_substack.py -v
"""
import pytest

from substack_to_epub.substack import SubstackClient

# A stable, fully-free Substack.
TEST_PUB_URL = "https://www.noahpinion.blog"


@pytest.fixture(scope="module")
def client():
    return SubstackClient(TEST_PUB_URL)


def test_is_single_post_url_false():
    assert SubstackClient.is_single_post_url(TEST_PUB_URL) is False


def test_is_single_post_url_true():
    assert SubstackClient.is_single_post_url(f"{TEST_PUB_URL}/p/some-slug") is True


def test_is_single_post_url_no_trailing_slash():
    assert SubstackClient.is_single_post_url("https://example.substack.com/p/hello") is True


def test_is_single_post_url_archive():
    assert SubstackClient.is_single_post_url("https://example.substack.com/archive") is False


@pytest.mark.network
def test_get_all_posts_returns_list(client):
    posts = client.get_all_posts(limit=3)
    assert isinstance(posts, list)
    assert len(posts) > 0


@pytest.mark.network
def test_get_all_posts_limit(client):
    posts = client.get_all_posts(limit=5)
    assert len(posts) <= 5


@pytest.mark.network
def test_posts_have_required_keys(client):
    posts = client.get_all_posts(limit=3)
    for post in posts:
        assert "title" in post
        assert "slug" in post


@pytest.mark.network
def test_fetch_post_content_has_body_html(client):
    stubs = client.get_all_posts(limit=1)
    assert stubs, "Need at least one post to test"
    full = client.fetch_post_content(stubs[0])
    assert "body_html" in full
    assert full["body_html"]  # non-empty


@pytest.mark.network
def test_fetch_post_content_body_not_truncated(client):
    """Full fetch should return more content than the stub preview."""
    stubs = client.get_all_posts(limit=1)
    assert stubs
    stub_html = stubs[0].get("body_html") or ""
    full = client.fetch_post_content(stubs[0])
    full_html = full.get("body_html") or ""
    # Full content should be at least as long as the stub
    assert len(full_html) >= len(stub_html)
