# Complete Webpage Cleaning Flowchart

```mermaid
flowchart TD
    A([Program starts]) --> B{Executed as main program?}

    B -- No --> B1[Expose functions and CleanedPage class<br/>for import by another module]
    B1 --> Z([Module ready])

    B -- Yes --> C[Call clean_webpage with target URL]

    subgraph CLEAN["clean_webpage(url)"]
        C --> D[Call fetch_html url]
        D --> E[Receive final URL and raw HTML]
        E --> F[Create BeautifulSoup document tree<br/>using lxml parser]

        F --> G{Does the page have<br/>a non-empty title?}
        G -- Yes --> H[Read soup.title.string]
        H --> I[Call clean_inline_text]
        I --> J[Store normalized title]
        G -- No --> K[Store empty title]

        J --> L[Call get_meta_content]
        K --> L

        L --> M[Check meta description selectors in order]
        M --> M1["meta name=description"]
        M1 --> M2{Valid content found?}
        M2 -- Yes --> M7[Normalize and store description]
        M2 -- No --> M3["meta property=og:description"]
        M3 --> M4{Valid content found?}
        M4 -- Yes --> M7
        M4 -- No --> M5["meta name=twitter:description"]
        M5 --> M6{Valid content found?}
        M6 -- Yes --> M7
        M6 -- No --> M8[Store empty description]

        M7 --> N{Does the HTML element<br/>have a lang attribute?}
        M8 --> N
        N -- Yes --> O[Normalize and store language]
        N -- No --> P[Store empty language]

        O --> Q[Call remove_unwanted_elements]
        P --> Q
        Q --> R[Call select_content_root]
        R --> S[Call extract_links<br/>before modifying content structure]
        S --> T[Call preserve_readable_structure]
        T --> U[Create CleanedPage object]
        U --> V[Return structured result]
    end

    V --> W[Print final URL]
    W --> X[Print title, description, and language]
    X --> Y[Print cleaned text]
    Y --> Y1[Print number of extracted links]
    Y1 --> ZZ([Program ends])
```

# HTTP Fetching Flow

```mermaid
flowchart TD
    A([fetch_html starts]) --> B[Call validate_public_url]

    subgraph VALIDATE["validate_public_url(url)"]
        B --> C[Parse URL using urlparse]
        C --> D{Scheme is HTTP or HTTPS?}

        D -- No --> E[Raise ValueError:<br/>unsupported URL scheme]
        D -- Yes --> F{Hostname exists?}

        F -- No --> G[Raise ValueError:<br/>hostname required]
        F -- Yes --> H{Hostname is explicitly blocked?}

        H -- Yes --> I[Raise ValueError:<br/>local or metadata endpoint]
        H -- No --> J[URL passes basic validation]
    end

    J --> K{Was an HTTP session supplied?}
    K -- Yes --> L[Use supplied session]
    K -- No --> M[Call create_http_session]

    subgraph SESSION["create_http_session()"]
        M --> N[Create Retry policy]
        N --> N1[Maximum 3 retries]
        N1 --> N2[Retry connection, read, and status failures]
        N2 --> N3[Use exponential backoff]
        N3 --> N4[Retry status codes<br/>429, 500, 502, 503, 504]
        N4 --> N5[Retry GET requests only]
        N5 --> O[Create requests Session]
        O --> P[Add User-Agent and Accept headers]
        P --> Q[Mount retry-enabled adapters<br/>for HTTP and HTTPS]
        Q --> R[Return configured session]
    end

    L --> S[Send streaming GET request]
    R --> S

    S --> S1[Apply connection timeout]
    S1 --> S2[Apply response timeout]
    S2 --> S3[Allow redirects]
    S3 --> T{Request succeeds?}

    T -- No --> U[requests raises network,<br/>timeout, or HTTP exception]
    T -- Yes --> V[Call response.raise_for_status]

    V --> W{HTTP status successful?}
    W -- No --> X[Raise HTTPError]
    W -- Yes --> Y[Read Content-Type header]

    Y --> Z{Content type is HTML<br/>or XHTML?}
    Z -- No --> AA[Raise ValueError:<br/>unsupported content type]
    Z -- Yes --> AB[Read declared Content-Length]

    AB --> AC{Declared size exceeds<br/>maximum byte limit?}
    AC -- Yes --> AD[Raise ValueError:<br/>response too large]
    AC -- No --> AE[Initialize empty byte chunks<br/>and downloaded-size counter]

    AE --> AF{More response chunks?}
    AF -- Yes --> AG[Read next 64 KB chunk]
    AG --> AH[Add chunk length to counter]
    AH --> AI{Downloaded size exceeds<br/>maximum byte limit?}

    AI -- Yes --> AJ[Raise ValueError:<br/>response too large]
    AI -- No --> AK[Append chunk to list]
    AK --> AF

    AF -- No --> AL[Join all byte chunks]
    AL --> AM{Response encoding available?}

    AM -- Yes --> AN[Use response encoding]
    AM -- No --> AO{Apparent encoding available?}

    AO -- Yes --> AP[Use apparent encoding]
    AO -- No --> AQ[Use UTF-8]

    AN --> AR[Decode bytes<br/>replace invalid characters]
    AP --> AR
    AQ --> AR

    AR --> AS[Return final redirected URL<br/>and decoded HTML]
    AS --> AT([fetch_html ends])

    E --> ERR([Processing stops with exception])
    G --> ERR
    I --> ERR
    U --> ERR
    X --> ERR
    AA --> ERR
    AD --> ERR
    AJ --> ERR
```

# HTML Metadata Extraction Flow

```mermaid
flowchart TD
    A([get_meta_content starts]) --> B[Receive BeautifulSoup tree<br/>and ordered selectors]
    B --> C{More selectors?}

    C -- No --> D[Return empty string]
    C -- Yes --> E[Select first matching element]
    E --> F{Element exists?}

    F -- No --> C
    F -- Yes --> G[Read content attribute]
    G --> H{Content is a non-empty string?}

    H -- No --> C
    H -- Yes --> I[Call clean_inline_text]
    I --> J[Replace repeated horizontal<br/>whitespace with one space]
    J --> K[Remove leading and trailing spaces]
    K --> L[Return normalized metadata]
    L --> M([get_meta_content ends])
    D --> M
```

# Unwanted Element Removal Flow

```mermaid
flowchart TD
    A([remove_unwanted_elements starts]) --> B[Find all explicitly unwanted tags]

    B --> C["Unwanted tags:<br/>script, style, noscript, iframe, svg,<br/>canvas, template, form, button, input,<br/>select, textarea, nav, footer, aside"]

    C --> D{More unwanted tags found?}
    D -- Yes --> E[Remove element and all descendants<br/>using decompose]
    E --> D
    D -- No --> F[Find all HTML comments]

    F --> G{More comments found?}
    G -- Yes --> H[Remove comment using extract]
    H --> G
    G -- No --> I[Create stable list of all remaining elements]

    I --> J{More elements?}
    J -- No --> K([Removal complete])

    J -- Yes --> L[Read element class names]
    L --> M[Read element ID]
    M --> N[Read ARIA role]
    N --> O[Combine class, ID, and role text]

    O --> P{Combined attributes match<br/>unwanted-name pattern?}

    P -- Yes --> Q["Match examples:<br/>ad, banner, cookie, consent,<br/>footer, header, menu, modal, nav,<br/>newsletter, popup, promo, related,<br/>sidebar, share, social, sponsor"]
    Q --> R[Remove element and descendants]
    R --> J

    P -- No --> J
```

# Main Content Selection Flow

```mermaid
flowchart TD
    A([select_content_root starts]) --> B[Prepare selectors in priority order]

    B --> C["1. main<br/>2. article<br/>3. role=main<br/>4. .article-content<br/>5. .post-content<br/>6. .entry-content<br/>7. #content"]

    C --> D{More selectors?}
    D -- Yes --> E[Search for first matching element]
    E --> F{Matching Tag found?}

    F -- Yes --> G[Return matched content root]
    F -- No --> D

    D -- No --> H{Body element exists?}
    H -- Yes --> I[Return body as content root]
    H -- No --> J[Return entire soup tree]

    G --> K([Content root selected])
    I --> K
    J --> K
```

# Link Extraction Flow

```mermaid
flowchart TD
    A([extract_links starts]) --> B[Create empty links list]
    B --> C[Create empty seen-URLs set]
    C --> D[Find anchor tags containing href]

    D --> E{More anchors?}
    E -- No --> F[Return unique links list]
    E -- Yes --> G[Read href attribute]

    G --> H{href is a string?}
    H -- No --> E
    H -- Yes --> I[Trim href whitespace]

    I --> J[Resolve relative URL against final page URL]
    J --> K[Parse absolute URL]
    K --> L{Scheme is HTTP or HTTPS?}

    L -- No --> E
    L -- Yes --> M[Remove URL fragment]

    M --> N{URL already in seen set?}
    N -- Yes --> E
    N -- No --> O[Add URL to seen set]

    O --> P[Extract visible anchor text]
    P --> Q[Normalize anchor text whitespace]
    Q --> R[Create link record:<br/>text and normalized URL]
    R --> S[Append record to links list]
    S --> E

    F --> T([extract_links ends])
```

# Readable Text Conversion Flow

```mermaid
flowchart TD
    A([preserve_readable_structure starts]) --> B[Find all list-item elements]

    B --> C{More list items?}
    C -- Yes --> D[Insert newline and dash before item]
    D --> E[Append newline after item]
    E --> C

    C -- No --> F[Find structural elements]

    F --> G["Structural elements:<br/>h1-h6, p, div, section, br, tr"]

    G --> H{More structural elements?}
    H -- Yes --> I[Insert newline before element]
    I --> J[Append newline after element]
    J --> H

    H -- No --> K[Extract visible text from root]
    K --> L[Use spaces between adjacent text nodes]
    L --> M[Remove leading and trailing text-node spaces]
    M --> N[Convert CRLF and CR line endings to LF]
    N --> O[Collapse repeated horizontal whitespace]
    O --> P[Remove spaces around line breaks]
    P --> Q[Collapse 3 or more newlines<br/>into 2 newlines]
    Q --> R[Trim outer whitespace]
    R --> S[Return cleaned text]
    S --> T([Text conversion ends])
```

# Structured Output Flow

```mermaid
flowchart LR
    A[Downloaded webpage] --> B[Final redirected URL]
    A --> C[Raw HTML]

    C --> D[Metadata extraction]
    D --> D1[Title]
    D --> D2[Description]
    D --> D3[Language]

    C --> E[DOM cleaning]
    E --> F[Content-root selection]
    F --> G[Readable text extraction]
    F --> H[Unique link extraction]

    B --> I[CleanedPage]
    D1 --> I
    D2 --> I
    D3 --> I
    G --> I
    H --> I

    I --> J["CleanedPage<br/>url: str<br/>title: str<br/>description: str<br/>language: str<br/>text: str<br/>links: list"]
```

# End-to-End Data Transformation

```text
Input URL
   |
   v
Basic URL validation
   |
   v
Retry-enabled HTTP session
   |
   v
Streaming HTML download
   |
   +-- Reject HTTP errors
   +-- Reject non-HTML responses
   +-- Reject oversized responses
   |
   v
Decode response bytes
   |
   v
Parse HTML into BeautifulSoup DOM
   |
   +-- Extract title
   +-- Extract description
   +-- Extract language
   |
   v
Remove unwanted content
   |
   +-- Scripts and styles
   +-- Forms and controls
   +-- Navigation and footers
   +-- Advertisements and popups
   +-- Cookie and consent elements
   +-- HTML comments
   |
   v
Select main content container
   |
   +-- <main>
   +-- <article>
   +-- role="main"
   +-- Common article-content classes
   +-- <body> fallback
   |
   +----------------------+
   |                      |
   v                      v
Extract links         Convert DOM to text
   |                      |
   +-- Resolve URLs        +-- Preserve headings
   +-- Remove fragments   +-- Preserve paragraphs
   +-- Remove duplicates  +-- Preserve list markers
   +-- Keep HTTP(S) only  +-- Normalize whitespace
   |                      |
   +-----------+----------+
               |
               v
        Create CleanedPage
               |
               v
     Cleaned text ready for:
       chunking -> embeddings
       -> CockroachDB storage
       -> RAG retrieval
```

# Failure Paths

| Stage | Failure condition | Result |
|---|---|---|
| URL validation | Scheme is not HTTP or HTTPS | `ValueError` |
| URL validation | Hostname is missing | `ValueError` |
| URL validation | Explicitly blocked hostname | `ValueError` |
| HTTP connection | DNS, connection, or timeout failure | `requests` exception after retries |
| HTTP response | 4xx or unrecoverable 5xx status | `HTTPError` |
| Content validation | Response is not HTML/XHTML | `ValueError` |
| Size validation | Declared response exceeds limit | `ValueError` |
| Streaming validation | Actual downloaded data exceeds limit | `ValueError` |
| Parsing | Malformed HTML | `lxml` attempts recovery |
| Metadata | Metadata is absent | Empty string |
| Main-content selection | No semantic content container | Falls back to `<body>` or complete DOM |
| Links | Invalid, duplicate, or non-HTTP link | Link is skipped |

# RAG Pipeline Extension

```mermaid
flowchart TD
    A[CleanedPage result] --> B{Cleaned text empty?}

    B -- Yes --> C[Mark ingestion as failed<br/>or unsupported]
    B -- No --> D[Attach source metadata]

    D --> E[Token-aware text chunking]
    E --> F[Add chunk overlap]
    F --> G[Assign chunk index]
    G --> H[Attach URL, title, language,<br/>section, and ingestion timestamp]
    H --> I[Generate content checksum]

    I --> J{Chunk already stored?}
    J -- Yes --> K[Skip duplicate chunk]
    J -- No --> L[Send chunk to Bedrock<br/>embedding model]

    L --> M[Receive embedding vector]
    M --> N[Validate vector dimension]
    N --> O[Store document metadata,<br/>chunk text, and vector<br/>in CockroachDB]

    O --> P[Create vector index]
    P --> Q[Document ready for retrieval]

    Q --> R[Receive user question]
    R --> S[Generate query embedding]
    S --> T[Search CockroachDB vectors]
    T --> U[Retrieve top-k chunks]
    U --> V[Rerank and deduplicate]
    V --> W[Fit chunks into context budget]
    W --> X[Send grounded prompt<br/>to Amazon Bedrock]
    X --> Y[Generate answer with citations]
    Y --> Z([Return final RAG response])
```
