from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Comment, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class CleanedPage:
    """Structured result returned by the webpage cleaner."""

    url: str
    title: str
    description: str
    language: str
    text: str
    links: list[dict[str, str]]


# Elements that usually contain navigation, scripts, styling, or other
# content that should not be included in a RAG document.
UNWANTED_TAGS = {
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "template",
    "form",
    "button",
    "input",
    "select",
    "textarea",
    "nav",
    "footer",
    "aside",
}

# Common class and ID names used for advertisements, cookie prompts,
# popups, navigation, and other page chrome.
UNWANTED_ATTRIBUTE_PATTERN = re.compile(
    r"""
    (^|[-_\s])
    (
        ad|ads|advert|advertisement|banner|
        breadcrumb|cookie|consent|
        footer|header|menu|modal|nav|navigation|
        newsletter|popup|promo|related|sidebar|
        share|social|sponsor
    )
    ([-_\s]|$)
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)

# Remove repeated horizontal whitespace while preserving line boundaries.
HORIZONTAL_WHITESPACE_PATTERN = re.compile(r"[ \t\f\v]+")
EXCESSIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")


def create_http_session() -> requests.Session:
    """Create an HTTP session with bounded retry behavior."""

    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; RAGDocumentCleaner/1.0; "
                "+https://example.com/bot)"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_policy))
    session.mount("http://", HTTPAdapter(max_retries=retry_policy))
    return session


def validate_public_url(url: str) -> None:
    """
    Perform basic URL validation.

    Production systems must additionally resolve the hostname and block
    private, loopback, link-local, and cloud metadata IP addresses to
    prevent server-side request forgery.
    """

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname:
        raise ValueError("The URL must contain a hostname.")

    blocked_hostnames = {"localhost", "metadata.google.internal"}

    if parsed.hostname.lower() in blocked_hostnames:
        raise ValueError("Local and metadata endpoints are not allowed.")


def fetch_html(
    url: str,
    session: requests.Session | None = None,
    timeout_seconds: float = 15.0,
    max_bytes: int = 5_000_000,
) -> tuple[str, str]:
    """
    Download an HTML page.

    Returns:
        A tuple containing the final URL after redirects and the HTML text.
    """

    validate_public_url(url)
    session = session or create_http_session()

    # stream=True prevents requests from loading an unexpectedly large
    # response into memory before its size has been checked.
    with session.get(
        url,
        timeout=(5.0, timeout_seconds),
        allow_redirects=True,
        stream=True,
    ) as response:
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type or 'unknown'}")

        declared_size = int(response.headers.get("Content-Length", "0") or 0)
        if declared_size > max_bytes:
            raise ValueError(f"Response exceeds the {max_bytes}-byte limit.")

        chunks: list[bytes] = []
        downloaded_size = 0

        for chunk in response.iter_content(chunk_size=64 * 1024):
            downloaded_size += len(chunk)

            if downloaded_size > max_bytes:
                raise ValueError(f"Response exceeds the {max_bytes}-byte limit.")

            chunks.append(chunk)

        content = b"".join(chunks)

        # requests detects encoding from HTTP headers. apparent_encoding
        # provides a fallback when the server omits or misreports it.
        encoding = response.encoding or response.apparent_encoding or "utf-8"
        html = content.decode(encoding, errors="replace")

        return response.url, html


def get_meta_content(soup: BeautifulSoup, *selectors: str) -> str:
    """Return the first non-empty content attribute from several selectors."""

    for selector in selectors:
        element = soup.select_one(selector)

        if element:
            content = element.get("content")
            if isinstance(content, str) and content.strip():
                return clean_inline_text(content)

    return ""


def clean_inline_text(value: str) -> str:
    """Normalize text intended to remain on a single line."""

    return HORIZONTAL_WHITESPACE_PATTERN.sub(" ", value).strip()


def remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """Remove tags and containers that are unlikely to contain useful content."""

    for element in soup.find_all(UNWANTED_TAGS):
        element.decompose()

    # Remove HTML comments because they may contain irrelevant source code,
    # tracking configuration, or hidden instructions.
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    for element in list(soup.find_all(True)):
        if not isinstance(element, Tag):
            continue

        class_value = " ".join(element.get("class", []))
        id_value = element.get("id", "")
        role_value = element.get("role", "")
        attributes = f"{class_value} {id_value} {role_value}"

        if UNWANTED_ATTRIBUTE_PATTERN.search(attributes):
            element.decompose()


def select_content_root(soup: BeautifulSoup) -> Tag:
    """
    Select the most likely content container.

    Semantic HTML is preferred. The body is used as a final fallback.
    """

    selectors = (
        "main",
        "article",
        '[role="main"]',
        ".article-content",
        ".post-content",
        ".entry-content",
        "#content",
    )

    for selector in selectors:
        element = soup.select_one(selector)
        if isinstance(element, Tag):
            return element

    if soup.body:
        return soup.body

    return soup


def preserve_readable_structure(root: Tag) -> str:
    """
    Convert the selected HTML content into normalized plain text.

    Block elements receive line breaks so headings, paragraphs, and list
    items do not collapse into one continuous string.
    """

    # Add simple list markers before removing the HTML structure.
    for item in root.find_all("li"):
        item.insert_before("\n- ")
        item.append("\n")

    # Separate structural elements with line breaks.
    for element in root.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "section", "br", "tr"]
    ):
        element.insert_before("\n")
        element.append("\n")

    text = root.get_text(separator=" ", strip=True)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = HORIZONTAL_WHITESPACE_PATTERN.sub(" ", text)

    # Remove spaces surrounding line breaks.
    text = re.sub(r" *\n *", "\n", text)
    text = EXCESSIVE_NEWLINES_PATTERN.sub("\n\n", text)

    return text.strip()


def extract_links(root: Tag, base_url: str) -> list[dict[str, str]]:
    """Extract unique HTTP links and convert relative URLs to absolute URLs."""

    links: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for anchor in root.find_all("a", href=True):
        href = anchor.get("href")

        if not isinstance(href, str):
            continue

        absolute_url = urljoin(base_url, href.strip())
        parsed = urlparse(absolute_url)

        if parsed.scheme not in {"http", "https"}:
            continue

        # Fragments identify locations inside the same document and usually
        # do not need to be stored as separate RAG sources.
        normalized_url = parsed._replace(fragment="").geturl()

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)
        links.append(
            {
                "text": clean_inline_text(anchor.get_text(" ", strip=True)),
                "url": normalized_url,
            }
        )

    return links


def clean_webpage(url: str) -> CleanedPage:
    """Fetch, parse, and clean a webpage for indexing or text analysis."""

    final_url, html = fetch_html(url)

    # lxml is faster and generally more tolerant of malformed HTML than
    # Python's built-in html.parser.
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = clean_inline_text(soup.title.string)

    description = get_meta_content(
        soup,
        'meta[name="description"]',
        'meta[property="og:description"]',
        'meta[name="twitter:description"]',
    )

    language = ""
    if soup.html:
        language_value = soup.html.get("lang")
        if isinstance(language_value, str):
            language = clean_inline_text(language_value)

    remove_unwanted_elements(soup)
    content_root = select_content_root(soup)

    # Extract links before converting the content tree into plain text.
    links = extract_links(content_root, final_url)
    text = preserve_readable_structure(content_root)

    return CleanedPage(
        url=final_url,
        title=title,
        description=description,
        language=language,
        text=text,
        links=links,
    )


if __name__ == "__main__":
    page = clean_webpage("https://example.com")

    print(f"URL: {page.url}")
    print(f"Title: {page.title}")
    print(f"Description: {page.description}")
    print(f"Language: {page.language}")
    print("\nCleaned text:\n")
    print(page.text)
    print(f"\nExtracted links: {len(page.links)}")
