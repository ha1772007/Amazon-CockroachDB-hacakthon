# Study Map: Agentic RAG with CockroachDB and Amazon Bedrock

## 1. Define the System Boundary

Target architecture:

```text
Documents / URLs / User Prompt
          |
          v
Ingestion and Web Search
          |
          v
Parsing -> Cleaning -> Chunking -> Metadata
          |
          v
Amazon Bedrock Embeddings
          |
          v
CockroachDB
  - document metadata
  - chunks
  - vector embeddings
  - conversations
  - citations
          |
          v
Agent Orchestrator
  - query classification
  - tool selection
  - retrieval
  - reranking
  - context construction
          |
          v
Amazon Bedrock LLM
          |
          v
Grounded answer with citations
```

Keep CockroachDB as the retrieval and application database. Do not use Bedrock Knowledge Bases as the main retrieval layer if demonstrating CockroachDB is a hackathon requirement.

## 2. Core RAG Concepts

Study these before implementation:

- Document ingestion pipelines
- Text normalization
- Semantic chunking
- Fixed-size and recursive chunking
- Chunk overlap
- Embedding models
- Vector similarity
- Cosine similarity
- Euclidean distance
- Inner-product similarity
- Top-k retrieval
- Metadata filtering
- Hybrid retrieval
- Full-text search
- Query rewriting
- Multi-query retrieval
- Hypothetical document embeddings, or HyDE
- Parent-document retrieval
- Context-window budgeting
- Lost-in-the-middle problems
- Reranking
- Citation generation
- Grounded generation
- Hallucination detection
- Retrieval evaluation
- Answer evaluation

Primary material:

- Lewis et al., “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks”
- Anthropic context-window and prompting documentation
- Amazon Bedrock prompt-engineering documentation
- CockroachDB vector search documentation

## 3. CockroachDB

### Required Topics

Study:

- CockroachDB Serverless deployment
- PostgreSQL wire compatibility
- Distributed SQL fundamentals
- Transactions and serializable isolation
- Connection pooling
- Schema migrations
- JSONB columns
- UUID primary keys
- Full-text search capabilities
- Vector data types
- Vector distance operators
- Vector indexes
- Approximate nearest-neighbor search
- Index tuning
- Query plans with `EXPLAIN`
- Regional and multi-region deployment
- Backup and restore
- CockroachDB Cloud observability

Confirm the exact vector syntax and index support against the CockroachDB version used by the hackathon environment.

### Suggested Schema

```sql
documents
- id UUID
- source_type STRING
- source_uri STRING
- title STRING
- checksum STRING
- metadata JSONB
- created_at TIMESTAMPTZ
- updated_at TIMESTAMPTZ

document_chunks
- id UUID
- document_id UUID
- chunk_index INT
- content STRING
- token_count INT
- metadata JSONB
- embedding VECTOR
- created_at TIMESTAMPTZ

conversations
- id UUID
- user_id UUID
- created_at TIMESTAMPTZ

messages
- id UUID
- conversation_id UUID
- role STRING
- content STRING
- model_id STRING
- usage JSONB
- created_at TIMESTAMPTZ

retrieval_events
- id UUID
- message_id UUID
- query STRING
- retrieved_chunk_ids UUID[]
- scores JSONB
- latency_ms INT
- created_at TIMESTAMPTZ
```

### Python Database Tools

Study:

- `psycopg` version 3
- SQLAlchemy 2.x
- Alembic
- CockroachDB SQLAlchemy adapter, if required
- Connection pool configuration
- Retry handling for transaction conflicts
- Parameterized SQL
- Bulk inserts
- Async database access

Recommended initial choice:

```text
SQLAlchemy 2.x + psycopg 3 + Alembic
```

Use raw SQL for vector retrieval when ORM support becomes restrictive.

## 4. Amazon Bedrock

### Bedrock Runtime

Study:

- Bedrock model access
- IAM permissions
- Model IDs
- Inference profiles
- Cross-region inference
- `boto3` Bedrock clients
- `bedrock-runtime`
- Converse API
- ConverseStream API
- Tool use
- Structured output
- Token usage
- Retry and throttling behavior
- Model-specific request parameters
- Streaming responses

Prefer the Bedrock Converse API over separate model-specific invocation formats where supported.

### Generation Models

Compare:

- Anthropic Claude models on Bedrock
- Amazon Nova models
- Meta Llama models
- Mistral models

Evaluate:

- Tool-calling reliability
- Context-window size
- Structured-output reliability
- Grounded-answer quality
- Latency
- Cost
- Regional availability

Use one primary generation model and one cheaper model for query rewriting or classification.

### Embedding Models

Study:

- Amazon Titan Text Embeddings
- Cohere Embed models available through Bedrock
- Embedding dimensions
- Input token limits
- Document-versus-query embedding modes
- Batch embedding
- Normalization
- Cost per request
- Regional availability

The CockroachDB vector column dimension must exactly match the chosen embedding model.

### Reranking

Study:

- Cohere Rerank through Bedrock, where available
- Bedrock-supported reranker models
- Cross-encoder reranking
- Top-k retrieval followed by top-n reranking

Recommended pipeline:

```text
Retrieve 20-40 chunks -> rerank -> send best 5-10 chunks to generation
```

### Bedrock Platform Services

Study:

- Bedrock Guardrails
- Prompt management
- Model evaluation
- Provisioned throughput
- Prompt caching where supported
- CloudWatch model invocation logging
- Bedrock Agents
- Bedrock Knowledge Bases

Treat Agents and Knowledge Bases as reference implementations. A custom orchestration layer provides clearer control and better demonstrates CockroachDB integration.

## 5. Agentic Architecture

“Agentic” must represent controlled tool selection, not repeated unrestricted LLM calls.

### Required Agent Components

Implement:

- Intent classifier
- Query planner
- Retrieval tool
- Web-search tool
- Document lookup tool
- Metadata-filter tool
- Query-rewrite tool
- Reranking step
- Answer-generation step
- Citation validator
- Refusal or insufficient-evidence path

### Suggested State Machine

```text
Receive query
    |
Classify query
    |
Decide whether retrieval, web search, or both are needed
    |
Rewrite or decompose query
    |
Execute tools with limits
    |
Rerank evidence
    |
Construct bounded context
    |
Generate answer
    |
Validate citations and grounding
    |
Return response
```

### Framework Choices

Evaluate:

- LangGraph
- LlamaIndex workflows
- LangChain
- PydanticAI
- Strands Agents SDK
- Custom Python state machine

Recommended choice:

```text
LangGraph or a small custom state machine
```

Use a custom state machine when the workflow has fewer than roughly ten nodes. This reduces framework complexity and makes the hackathon demonstration easier to explain.

### Tool Interface

Use typed input and output contracts:

```python
class SearchDocumentsInput(BaseModel):
    query: str
    top_k: int = 20
    document_ids: list[str] | None = None

class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    source_uri: str | None
```

Study:

- Pydantic v2
- JSON Schema
- Bedrock tool-use schemas
- Tool timeout handling
- Maximum tool-call counts
- Tool result validation
- Cyclic-agent prevention

## 6. Document Ingestion

### Supported Formats

Prioritize:

1. PDF
2. HTML and URLs
3. Markdown
4. Plain text
5. DOCX

Avoid broad format support during the hackathon.

### Python Libraries

Study:

- `pypdf` or `PyMuPDF`
- `python-docx`
- Beautiful Soup
- `trafilatura`
- `markdown`
- `unstructured`, only if complex format support is necessary
- Apache Tika, only if JVM deployment complexity is acceptable
- Amazon Textract for scanned documents and OCR

Recommended combination:

```text
PyMuPDF + trafilatura + python-docx
```

Use Textract for scanned PDFs. Ordinary PDF parsers do not provide reliable OCR.

### Ingestion Pipeline

Implement:

```text
Upload
-> calculate checksum
-> extract text
-> clean text
-> preserve headings and page numbers
-> chunk
-> count tokens
-> generate embeddings in batches
-> persist document and chunks
-> mark ingestion status
```

Store:

- Original source
- Document title
- Page number
- Section heading
- Chunk index
- Content checksum
- Ingestion version
- Embedding model ID
- Embedding dimension
- Chunking strategy version

Checksums prevent duplicate ingestion.

### Chunking

Study and test:

- Recursive character splitting
- Token-aware splitting
- Heading-aware splitting
- Semantic splitting
- Table preservation
- Code-block preservation

Practical initial values:

```text
Chunk size: 400-800 tokens
Overlap: 50-120 tokens
Retrieval top-k: 20-40
Final context chunks: 5-10
```

Use a tokenizer compatible with the selected generation model when available. Otherwise use `tiktoken` only as an approximation.

## 7. Web Search

### Search Provider Options

Evaluate:

- Tavily
- Brave Search API
- Bing Web Search
- Google Programmable Search
- SerpAPI
- Amazon Kendra Web Crawler, if applicable

Tavily provides direct LLM-oriented search results. Brave provides a conventional search API with greater control.

### Web Retrieval Pipeline

```text
Search query
-> search API
-> choose trusted results
-> download pages
-> extract main content
-> remove navigation and advertisements
-> rerank passages
-> pass evidence to model
```

Study:

- `httpx`
- `trafilatura`
- URL normalization
- Request timeouts
- Retry policies
- Redirect handling
- Robots.txt considerations
- Domain allowlists and denylists
- Publication-date extraction
- Source freshness
- Search result deduplication
- Protection against server-side request forgery

Do not allow unrestricted fetching of private IP ranges, cloud metadata endpoints, or local network addresses.

## 8. Context Optimization

Study:

- Query rewriting
- Query decomposition
- Multi-query retrieval
- Contextual compression
- Deduplication
- Maximum marginal relevance
- Reranking
- Token budgeting
- Source diversity
- Recency weighting
- Metadata filtering
- Prompt caching
- Conversation summarization
- Relevant-history retrieval

Recommended sequence:

```text
Original query
-> rewrite into retrieval query
-> retrieve candidates
-> apply metadata filters
-> deduplicate
-> rerank
-> enforce source diversity
-> fit chunks into token budget
-> generate answer
```

Do not send every retrieved chunk to the model. Retrieval volume and generation-context volume are separate parameters.

## 9. Prompt Design

Create separate prompts for:

- Intent classification
- Query rewriting
- Query decomposition
- Tool selection
- Answer generation
- Citation checking
- Grounding evaluation
- Conversation summarization

The answer prompt must define:

- Evidence boundaries
- Citation format
- Behavior when evidence is missing
- Treatment of conflicting sources
- Separation of retrieved content from instructions
- Required output schema

Example evidence format:

```text
[SOURCE 1]
document_id: ...
chunk_id: ...
title: ...
page: ...
content: ...

[SOURCE 2]
...
```

Require citations such as `[SOURCE 1]`. Validate that every returned citation refers to supplied evidence.

## 10. Prompt-Injection Defense

Retrieved documents and websites are untrusted input.

Study:

- Direct prompt injection
- Indirect prompt injection
- Tool-output injection
- Data exfiltration
- Instruction hierarchy
- Jailbreak resistance
- Malicious document ingestion
- Cross-user data leakage

Implement:

- Treat retrieved text as data, never as system instructions
- Delimit evidence explicitly
- Strip or flag instruction-like content
- Restrict tool permissions
- Use hard tool-call limits
- Validate all tool arguments
- Isolate tenant data in every database query
- Prevent arbitrary URL access
- Never place secrets in prompts
- Use Bedrock Guardrails as an additional layer
- Log injection detections without storing secrets

## 11. API and Backend

Recommended stack:

```text
Python 3.12
FastAPI
Pydantic v2
Uvicorn
SQLAlchemy 2.x
psycopg 3
Alembic
boto3
httpx
tenacity
structlog
Rich
```

Study:

- FastAPI dependency injection
- Async endpoints
- Streaming responses with Server-Sent Events
- Multipart file uploads
- Background jobs
- Request validation
- Exception handlers
- OpenAPI
- CORS
- Authentication middleware
- Rate limiting

Use synchronous execution consistently unless measurable concurrency requirements justify async database and HTTP code. Mixed sync and async code creates avoidable complexity.

## 12. Rich Python Library

Rich is suitable for a developer CLI and live demonstration, not the RAG engine.

Study:

- `Console`
- Tables
- Panels
- Progress bars
- Live displays
- Markdown rendering
- Syntax highlighting
- Tracebacks
- Logging handlers
- Prompts
- Status spinners

Useful CLI commands:

```text
rag ingest <file>
rag ingest-url <url>
rag query "<question>"
rag inspect-document <id>
rag evaluate <dataset>
rag benchmark
```

Pair Rich with:

- Typer for CLI commands
- Pydantic for configuration
- `python-dotenv` for local development only

## 13. Frontend

Fastest hackathon options:

- Streamlit
- Gradio
- React or Next.js

Recommended decision:

- Streamlit for maximum implementation speed
- React or Next.js for stronger product presentation

Required interface elements:

- File upload
- URL ingestion
- Ingestion status
- Chat interface
- Streaming answer
- Source citations
- Expandable source passages
- Search-mode selector
- Document filters
- Retrieval trace
- Error state
- Clear-conversation action

Do not expose raw chain-of-thought. Show tool activity, selected sources, retrieval scores, latency, and citations instead.

## 14. AWS Infrastructure

Study:

- AWS IAM
- AWS STS
- Bedrock permissions
- S3
- ECS Fargate or AWS Lambda
- Amazon ECR
- CloudWatch Logs
- CloudWatch Metrics
- AWS Secrets Manager
- AWS Systems Manager Parameter Store
- API Gateway
- Application Load Balancer
- VPC basics
- AWS WAF
- AWS CDK or Terraform

Recommended hackathon deployment:

```text
Frontend: Streamlit or Next.js
Backend: FastAPI container
Compute: ECS Fargate or App Runner
Documents: S3
Database: CockroachDB Cloud
Models: Amazon Bedrock
Secrets: AWS Secrets Manager
Logs: CloudWatch
```

Lambda can be problematic for long document-processing jobs, large dependencies, streaming, and execution-duration limits. Use ECS Fargate, App Runner, or a dedicated worker for ingestion.

## 15. Background Processing

Document extraction and embedding should not block normal API requests.

Evaluate:

- Celery with Redis
- Dramatiq
- Amazon SQS workers
- AWS Step Functions
- FastAPI background tasks for demo-scale workloads

Recommended production-shaped hackathon design:

```text
API -> SQS -> ingestion worker -> CockroachDB
```

Track ingestion states:

```text
pending
extracting
chunking
embedding
completed
failed
```

## 16. Configuration and Secrets

Use environment variables for:

```text
AWS_REGION
BEDROCK_MODEL_ID
BEDROCK_EMBEDDING_MODEL_ID
DATABASE_URL
S3_BUCKET
SEARCH_API_KEY
MAX_RETRIEVAL_RESULTS
MAX_AGENT_STEPS
```

Study:

- `pydantic-settings`
- AWS credential provider chain
- IAM roles for workloads
- Secrets Manager rotation
- `.env` exclusion from Git

Never commit:

- AWS access keys
- Database credentials
- Search API keys
- Real user documents
- Prompt logs containing confidential data

## 17. Observability

Track each request across retrieval and generation.

Recommended tools:

- Python `logging`
- `structlog`
- OpenTelemetry
- AWS X-Ray
- CloudWatch
- Langfuse
- Arize Phoenix
- LangSmith, if using LangChain or LangGraph

Capture:

- Request ID
- Conversation ID
- Model ID
- Prompt version
- Embedding model ID
- Retrieved chunk IDs
- Similarity scores
- Reranking scores
- Input and output token counts
- Retrieval latency
- Model latency
- Total latency
- Tool-call count
- Estimated cost
- Error category

Redact credentials, personal data, and confidential document content.

## 18. Evaluation

A RAG demonstration without evaluation cannot establish quality.

### Build a Test Dataset

Create 30-100 questions containing:

- Direct factual questions
- Multi-document questions
- Questions requiring web search
- Time-sensitive questions
- Questions with no answer
- Ambiguous questions
- Conflicting-source questions
- Prompt-injection documents
- Questions requiring metadata filters

### Retrieval Metrics

Study:

- Recall@k
- Precision@k
- Mean reciprocal rank
- Normalized discounted cumulative gain
- Hit rate
- Source diversity

### Generation Metrics

Measure:

- Faithfulness
- Answer relevance
- Citation correctness
- Citation completeness
- Context relevance
- Refusal correctness
- Tool-selection accuracy
- Latency
- Cost per request

### Evaluation Tools

Evaluate:

- RAGAS
- DeepEval
- TruLens
- Arize Phoenix
- Bedrock model evaluation
- Custom deterministic tests
- LLM-as-judge with calibrated human review

Do not rely exclusively on LLM-as-judge. Maintain manually verified expected sources for core questions.

## 19. Testing

Study and implement:

- `pytest`
- `pytest-asyncio`
- `testcontainers`
- `moto`, with awareness that Bedrock support may be incomplete
- `respx` for HTTP mocking
- `hypothesis` for property-based tests
- `ruff`
- `mypy` or `pyright`

Required test layers:

- Unit tests for chunking and context budgeting
- Unit tests for citation parsing
- Database integration tests
- Search-provider adapter tests
- Bedrock client contract tests
- End-to-end ingestion tests
- End-to-end query tests
- Prompt-injection tests
- Tenant-isolation tests
- Timeout and throttling tests

## 20. Reliability Controls

Implement:

- Request timeouts
- Exponential backoff
- Jitter
- Maximum retries
- Bedrock throttling handling
- Search API fallback
- Idempotent ingestion
- Checksum-based deduplication
- Transaction retries
- Maximum document size
- Maximum page count
- Maximum agent steps
- Per-tool timeout
- Circuit breakers for unstable dependencies
- Graceful insufficient-evidence responses

Use `tenacity` for bounded retries. Do not retry validation failures or permanent authorization errors.

## 21. Authentication and Data Isolation

Study:

- Amazon Cognito
- JWT validation
- OAuth 2.0 and OpenID Connect
- Tenant-aware schemas
- Object-level authorization
- Signed S3 URLs

Every document and chunk should carry a tenant or owner identifier when multiple users are supported.

Every retrieval query must enforce tenant filtering inside SQL. Filtering results after vector retrieval risks data leakage.

## 22. Cost Controls

Estimate and limit:

- Embedding calls
- Generation tokens
- Reranking calls
- Web searches
- S3 storage
- Database storage
- Worker runtime

Implement:

- Embedding cache by content checksum
- Query embedding cache
- Batched embedding requests
- Per-request token budget
- Maximum search calls
- Maximum agent steps
- Conversation summarization
- Smaller model for classification and rewriting
- Larger model only for final synthesis
- Request-level cost reporting

## 23. Repository Structure

```text
app/
  api/
    routes/
    dependencies.py
  agents/
    graph.py
    state.py
    tools.py
  bedrock/
    client.py
    embeddings.py
    generation.py
    reranking.py
  ingestion/
    loaders.py
    cleaning.py
    chunking.py
    pipeline.py
  retrieval/
    vector.py
    keyword.py
    hybrid.py
    context.py
  search/
    client.py
    extraction.py
  database/
    models.py
    queries.py
    session.py
  evaluation/
    datasets.py
    metrics.py
  security/
    url_validation.py
    injection.py
  cli/
    main.py
  settings.py
tests/
migrations/
infra/
```

## 24. Minimal Hackathon Scope

Build these features first:

1. PDF and URL ingestion
2. Bedrock embeddings
3. CockroachDB vector storage
4. Semantic retrieval with metadata
5. Web-search tool
6. Controlled agent routing
7. Bedrock answer generation
8. Verifiable citations
9. Rich CLI or simple web UI
10. Evaluation dashboard
11. AWS deployment
12. Architecture diagram and live trace

Exclude initially:

- Many document formats
- Autonomous long-running agents
- Voice input
- Multiple agent personas
- Fine-tuning
- Complex multi-agent collaboration
- Self-modifying prompts
- Broad plugin systems

## 25. Recommended Implementation Order

1. Provision CockroachDB Cloud.
2. Enable Bedrock model access.
3. Verify one Bedrock generation call.
4. Verify one Bedrock embedding call.
5. Create document and chunk tables.
6. Insert and retrieve a sample vector.
7. Build PDF and HTML extraction.
8. Add chunking and batch embeddings.
9. Implement vector retrieval.
10. Add metadata filtering.
11. Add reranking.
12. Generate answers with citations.
13. Add web search as a bounded tool.
14. Add agent routing.
15. Add ingestion background processing.
16. Add evaluation dataset and metrics.
17. Add observability.
18. Build the user interface.
19. Deploy to AWS.
20. Run security, latency, cost, and failure tests.

## 26. Critical Design Decisions

Record these before coding:

| Decision | Required Choice |
|---|---|
| Generation model | Exact Bedrock model and region |
| Embedding model | Exact model and vector dimension |
| Database version | CockroachDB version with required vector support |
| Retrieval strategy | Vector-only or hybrid |
| Reranker | Bedrock model or local alternative |
| Agent framework | LangGraph, Strands, or custom |
| Search provider | Tavily, Brave, Bing, or other |
| Document formats | Initial supported subset |
| Deployment | ECS, App Runner, or Lambda |
| UI | Streamlit, Gradio, or React |
| Authentication | None for demo or Cognito |
| Evaluation | Dataset size and metrics |
| Citation format | Stable source identifiers |
| Tenant isolation | Owner and tenant enforcement model |

## 27. Hackathon Demonstration Flow

Use a demonstration that proves each integration:

1. Upload a document.
2. Show extraction, chunk count, and embedding completion.
3. Show CockroachDB rows and vector retrieval.
4. Ask a question answered only by the document.
5. Display cited passages and retrieval scores.
6. Ask a current question requiring web search.
7. Show the agent selecting the web-search tool.
8. Ask a question requiring both document and web evidence.
9. Show bounded context sent to Bedrock.
10. Show latency, tokens, model, tool calls, and estimated cost.
11. Submit an unanswerable question.
12. Show an insufficient-evidence response instead of fabrication.
13. Submit a prompt-injection document.
14. Show that embedded instructions are treated as untrusted content.
