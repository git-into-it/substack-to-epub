import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from .cli import parse_args
from .epub import build_epub
from .substack import SubstackClient, SubstackError


def _derive_output_path(client: SubstackClient, title: str, limit: int | None) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return Path(f"{slug}.epub")


def _derive_title(client: SubstackClient, posts: list[dict]) -> str:
    # Use the publication name from the first post if available
    for post in posts:
        pub = post.get("publication") or {}
        name = pub.get("name")
        if name:
            return name
    # Fall back to the subdomain
    parsed = urlparse(client.base_url)
    return parsed.hostname.split(".")[0].replace("-", " ").title()


def main() -> None:
    args = parse_args()

    try:
        client = SubstackClient(args.url)

        # Authenticate
        if args.email:
            print("Logging in…", file=sys.stderr)
            client.login(args.email, args.password)
        elif args.cookie:
            client.set_cookie(args.cookie)

        # Fetch posts
        if SubstackClient.is_single_post_url(args.url):
            print("Fetching single post…", file=sys.stderr)
            post = client.fetch_single_post(args.url)
            posts = [post]
        else:
            print("Fetching post list…", file=sys.stderr)
            stubs = client.get_all_posts(limit=args.limit)
            if not stubs:
                print("No posts found.", file=sys.stderr)
                sys.exit(1)

            posts = []
            for i, stub in enumerate(stubs, start=1):
                print(
                    f"  [{i}/{len(stubs)}] {stub.get('title', stub.get('slug', '?'))}",
                    file=sys.stderr,
                )
                full = client.fetch_post_content(stub)
                posts.append(full)

        # Title and output path
        title = args.title or _derive_title(client, posts)
        output_path = (
            Path(args.output)
            if args.output
            else _derive_output_path(client, title, args.limit)
        )

        # Build EPUB
        print(f"Building EPUB: {title!r}…", file=sys.stderr)
        build_epub(posts, title, output_path)
        print(f"Written to {output_path}")

    except SubstackError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
