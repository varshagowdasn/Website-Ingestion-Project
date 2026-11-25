# Website Ingestion & Dynamic Content Extraction

FastAPI application that synchronizes an S3-compatible website, renders five pages with Playwright Chromium, extracts visible text (including an opt-in modal), and stores metadata/content in async SQLAlchemy tables.

## Run locally

Requirements: Python 3.12+, Docker Desktop, AWS CLI.

```bash
cp .env.example .env
docker compose up -d localstack
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
aws --endpoint-url=http://localhost:4566 s3 mb s3://website-assets
aws --endpoint-url=http://localhost:4566 s3 sync sample_site/ s3://website-assets/website/
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and call `POST /ingestion/run`. Inspect `/files`, `/pages`, and `/pages/{id}`. Rendered files are served under `/site/`.

## Docker

Build/run the API with `docker compose up --build` after creating `.env`. Upload the sample site from the host using the AWS CLI command above. If LocalStack is still starting, retry the ingestion call after it becomes healthy.

## API

- `POST /ingestion/run`: scan S3, download changed files, detect deletions, and reprocess affected pages.
- `GET /files`: S3 metadata and operation.
- `GET /pages`: extracted page records.
- `GET /pages/{page_id}`: extracted text and hash.
- `POST /pages/{page_id}/reprocess`: manually re-render one page.
- `GET /docs`: Swagger/OpenAPI UI.

## Architecture and decisions

`app/s3.py` provides an async aioboto3 client. `app/logic.py` performs paginated S3 listing, ETag comparison, local synchronization, deletion detection, dependency mapping, and selective reprocessing. `app/render.py` uses Playwright because JavaScript-created content cannot reliably be extracted from raw HTML. It clicks elements marked `data-open-modal` or `data-extract-click`, scrolls the document and scrollable elements, and extracts rendered body text.

### Idempotency
The S3 key is unique in SQL. An unchanged ETag skips download and extraction. A SHA-256 of downloaded bytes is retained as an additional content fingerprint. ETags are treated as opaque S3 change tokens (multipart ETags are not necessarily MD5).

### Deletion strategy
A persisted application-side inventory is compared with a complete, paginated listing of the configured prefix. Previously present keys absent from the complete listing are marked deleted. This requires successful full-list permission; never infer deletion from a failed or partial listing. S3 event notifications or S3 Inventory are better at scale.

### Dependency-aware processing
The dependency table maps each page to referenced assets. HTML changes trigger that page. Changed CSS/JS/images trigger pages referencing those keys. HTML parsing covers common `src`, `href`, and `poster` attributes; CSS references cover basic `url()` and `@import`. Runtime-created dependencies and complex CSS/bundler behavior need browser network instrumentation for full coverage.

### 24-hour window
Newly discovered keys are ingested even if old. Existing changed keys are processed only when S3 LastModified is within the configured lookback. This satisfies the assignment's 24-hour window, but an outage longer than 24 hours can miss old updates. A production implementation should use durable event notifications or version checkpoints.

### Database
`ingested_files` stores key, ETag/version, timestamp, size, operation, presence, and byte hash. `extracted_pages` stores page path, title, text, extraction time, and content hash. `page_dependencies` stores page-to-asset edges. Tables are created at startup; use Alembic migrations in production.

## Tests
`pytest -q`. The included test checks the health endpoint. Extend integration coverage with LocalStack for create/update/delete/repeated scans and a CSS-only change affecting only dependent pages.

## Demo sequence
1. Upload the sample website.
2. Start the API and call ingestion.
3. Verify five extracted pages and modal copy in page content.
4. Call ingestion again; unchanged files should be skipped.
5. Change CSS, sync it to S3, and rerun ingestion; dependent pages should be reprocessed.
6. Delete an S3 asset and rerun ingestion; it should be marked deleted.
