# substack-to-epub

Convert a Substack publication or single post to an EPUB file. Works with free and paid content — pass credentials to access subscriber-only posts.

## Installation

### With uv (recommended)

```bash
uv tool install git+https://github.com/git-into-it/substack-to-epub
```

Or run without installing:

```bash
uvx git+https://github.com/git-into-it/substack-to-epub <url>
```

## Usage

```
substack-to-epub <url> [options]
```

### Basic examples

Fetch an entire publication (all posts):

```bash
substack-to-epub https://example.substack.com
```

Fetch the most recent 10 posts:

```bash
substack-to-epub https://example.substack.com --limit 10
```

Fetch a single post:

```bash
substack-to-epub https://example.substack.com/p/some-post-slug
```

Specify the output file and book title:

```bash
substack-to-epub https://example.substack.com --output my-book.epub --title "My Book"
```

### Accessing paid content

Authenticate with email and password:

```bash
substack-to-epub https://example.substack.com --email you@example.com --password yourpassword
```

Or pass a `substack.sid` session cookie directly if you are already logged in through your browser:

```bash
substack-to-epub https://example.substack.com --cookie 's%3Ayour-cookie-value...'
```

#### How to find your substack.sid cookie

**Chrome or Edge**

1. Go to [substack.com](https://substack.com) and make sure you are logged in.
2. Open DevTools: `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (Mac).
3. Click the **Application** tab.
4. In the left sidebar, expand **Cookies** and click `https://substack.com`.
5. Find the row named `substack.sid` and copy the value from the **Value** column.

**Firefox**

1. Go to [substack.com](https://substack.com) and make sure you are logged in.
2. Open DevTools: `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (Mac).
3. Click the **Storage** tab.
4. In the left sidebar, expand **Cookies** and click `https://substack.com`.
5. Find the row named `substack.sid` and copy the value from the **Value** column.

**Safari**

1. Go to [substack.com](https://substack.com) and make sure you are logged in.
2. Enable the Develop menu if needed: **Safari → Settings → Advanced → Show features for web developers**.
3. Open DevTools: `Cmd+Option+I`, then click the **Storage** tab.
4. In the left sidebar, expand **Cookies** and click `https://substack.com`.
5. Find the row named `substack.sid` and copy the value.

The cookie value starts with `s%3A` (a URL-encoded `s:`). Copy the full value including that prefix.

### All options

| Option | Description |
|---|---|
| `url` | Publication root or single post URL (required) |
| `--email EMAIL` | Substack login email |
| `--password PASSWORD` | Substack login password |
| `--cookie COOKIE` | `substack.sid` cookie value (alternative to email/password) |
| `--output FILE`, `-o FILE` | Output filename (default: derived from publication name) |
| `--limit N` | Maximum number of posts to include (default: all) |
| `--title TITLE` | Override the book title |

## Development

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/stevec/substack-to-epub
cd substack-to-epub
uv sync
uv run substack-to-epub --help
```

Run tests:

```bash
uv run pytest tests/ -v
```
