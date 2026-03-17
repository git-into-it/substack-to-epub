import argparse
import sys


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="substack-to-epub",
        description="Convert a Substack publication or post to an EPUB file.",
    )
    parser.add_argument(
        "url",
        help="Publication root URL (https://example.substack.com) or single post URL",
    )
    parser.add_argument("--email", help="Substack login email")
    parser.add_argument("--password", help="Substack login password")
    parser.add_argument(
        "--cookie", help="substack.sid cookie value (alternative to email/password)"
    )
    parser.add_argument("--output", "-o", help="Output filename (default: derived from publication name)")
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of posts to include (default: all)",
    )
    parser.add_argument("--title", help="Override book title")

    args = parser.parse_args(argv)

    # Validate credentials
    if args.cookie and (args.email or args.password):
        parser.error("--cookie cannot be used together with --email/--password")

    if bool(args.email) != bool(args.password):
        parser.error("--email and --password must be provided together")

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer")

    return args
