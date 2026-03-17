import pytest

from substack_to_epub.cli import parse_args


def test_valid_url_only():
    args = parse_args(["https://example.substack.com"])
    assert args.url == "https://example.substack.com"
    assert args.email is None
    assert args.password is None
    assert args.cookie is None
    assert args.limit is None
    assert args.output is None
    assert args.title is None


def test_valid_with_email_and_password():
    args = parse_args([
        "https://example.substack.com",
        "--email", "user@example.com",
        "--password", "secret",
    ])
    assert args.email == "user@example.com"
    assert args.password == "secret"


def test_valid_with_cookie():
    args = parse_args(["https://example.substack.com", "--cookie", "abc123"])
    assert args.cookie == "abc123"


def test_valid_with_limit():
    args = parse_args(["https://example.substack.com", "--limit", "5"])
    assert args.limit == 5


def test_valid_with_output():
    args = parse_args(["https://example.substack.com", "--output", "out.epub"])
    assert args.output == "out.epub"


def test_valid_with_title():
    args = parse_args(["https://example.substack.com", "--title", "My Book"])
    assert args.title == "My Book"


def test_email_without_password_raises(capsys):
    with pytest.raises(SystemExit):
        parse_args(["https://example.substack.com", "--email", "user@example.com"])


def test_password_without_email_raises(capsys):
    with pytest.raises(SystemExit):
        parse_args(["https://example.substack.com", "--password", "secret"])


def test_cookie_and_email_raises(capsys):
    with pytest.raises(SystemExit):
        parse_args([
            "https://example.substack.com",
            "--cookie", "abc",
            "--email", "user@example.com",
            "--password", "secret",
        ])


def test_limit_zero_raises(capsys):
    with pytest.raises(SystemExit):
        parse_args(["https://example.substack.com", "--limit", "0"])


def test_limit_negative_raises(capsys):
    with pytest.raises(SystemExit):
        parse_args(["https://example.substack.com", "--limit", "-1"])


def test_url_required(capsys):
    with pytest.raises(SystemExit):
        parse_args([])
