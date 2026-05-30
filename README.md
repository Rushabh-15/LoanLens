# LoanLens

## Overview

LoanLens is an AI-assisted loan application analysis system that automates document review while keeping lending decisions auditable and deterministic. The system uses a Large Language Model (LLM) to extract applicant information from loan application PDFs, but all lending calculations and approval decisions are performed by tested Python business rules. Applications containing uncertain or low-confidence extracted data are automatically routed for human review. This architecture combines the flexibility of AI-powered document understanding with the reliability and transparency required for lending workflows.

---

## Architecture

```text
PDF upload → pdf_extractor → llm_extractor → confidence check → rules_engine → decision → DB → JSON
 (bytes)      (text)          (fields +        (has_low_         (EMI/FOIR/    (eligible/  (persist)
                               confidence)      confidence)       flags)        decline/
                                                                                review)
```

### Layer Responsibilities

* **Routes** orchestrate requests, map errors, and return API responses.
* **Services** contain application logic such as PDF extraction, LLM extraction, risk analysis, and decision routing.
* **Rules Engine** performs deterministic EMI, FOIR, and risk calculations.
* **Decision Router** applies deterministic business rules to determine eligibility, decline, or human review outcomes.
* **Database Layer** persists applications and decisions for auditability and retrieval.

The key design principle is that the LLM reads documents, while deterministic Python code makes decisions.

---

## Setup

### 1. Create and activate a virtual environment

**macOS / Linux**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows**

```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

Notes:

* `CLAUDE_MODEL` has a working default value.
* `DATABASE_URL` defaults to SQLite.
* No database setup is required for local development.

### 4. Start the application

```bash
uvicorn app.main:app --reload
```

### 5. Open Swagger UI

```text
http://127.0.0.1:8000/docs
```

### 6. Run the test suite (optional)

```bash
pytest -q
```

---

## API Endpoints

### POST /api/v1/applications/analyze

Upload a loan application PDF and run the complete pipeline: extraction, confidence assessment, risk analysis, decisioning, and persistence.

### POST /api/v1/applications/analyze-fields

Submit applicant data directly as JSON and receive a lending decision without PDF processing.

### GET /api/v1/applications/{id}

Retrieve a previously stored loan application and decision by ID.

### GET /api/v1/review-queue

List applications that require manual review due to low-confidence extraction or workflow routing.

### GET /health

Health-check endpoint used to verify service availability.

---

## Demo

1. Start the API.
2. Open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

3. Use the `POST /api/v1/applications/analyze` endpoint.
4. Upload:

```text
sample_data/sample_application.pdf
```

5. Execute the request and inspect the returned extraction results, risk metrics, and lending decision.

## Design Decisions

### Why split LLM extraction from the rules engine?

LoanLens separates document understanding from decision-making. The LLM is responsible for reading unstructured loan application documents and extracting structured fields, while deterministic Python code performs all affordability calculations and lending decisions. This separation improves auditability, reproducibility, and safety in a regulated domain because the final decision never depends on a model's reasoning. It also makes the decisioning layer fully unit-testable, as the rules engine and decision router operate entirely on structured values and have no dependency on FastAPI, databases, or the LLM SDK.

The architectural seam is explicit: `extract_fields()` produces structured applicant data, `analyze_applicant()` computes risk metrics, and `route_decision()` determines the final outcome.

---

### Why use per-field confidence instead of simply trusting the LLM?

Structured Outputs guarantee that the response matches a valid schema, but they do not guarantee that the extracted values are correct. For example, a model may return a valid monthly income field while still misreading the document. To address this, every extracted field carries its own confidence assessment using typed field wrappers and a confidence enum.

The confidence values are treated as routing signals rather than calibrated probabilities. The system uses `has_low_confidence()` to detect uncertain extractions and route them for human review. This approach acknowledges uncertainty explicitly instead of assuming that schema-valid output is always trustworthy.

---

### Why route applications to human review instead of auto-deciding everything?

The system follows a conservative precedence rule: any low-confidence critical field results in a `NEEDS_REVIEW` outcome, regardless of whether the current data would otherwise produce an approval or decline. A lending decision built on uncertain information is difficult to defend and audit, especially in regulated environments.

This design prioritizes correctness over automation. Human reviewers resolve uncertainty before a final decision is made. In a production system, some decline conditions could potentially bypass review if they are provably independent of the low-confidence field, but LoanLens intentionally adopts a fail-safe posture.

---

### Why use FOIR and EMI as the primary affordability checks?

FOIR (Fixed Obligation to Income Ratio) and EMI (Equated Monthly Installment) are widely used affordability measures in consumer lending. Together they provide a simple, explainable way to evaluate whether an applicant can reasonably service a proposed loan.

The important design decision is that the thresholds themselves are business policy, not engineering policy. Values such as `FOIR_THRESHOLD`, `MINIMUM_MONTHLY_INCOME`, `LOAN_INCOME_MULTIPLE`, and the assumed interest rate are implemented as named configuration constants so they can be adjusted by risk teams without requiring architectural changes. Engineering owns the mechanism; risk teams own the policy.

---

### What are the primary failure modes and how does the system handle them?

The first failure mode is LLM unavailability. If the extraction API fails, the extraction layer acts as a fault boundary. Rather than raising an exception that causes a server error, the system returns a low-confidence extraction result and logs the failure. The application is then routed to human review. This converts an infrastructure failure into a recoverable workflow outcome.

The second failure mode is incorrect or uncertain extraction. Low-confidence values are treated differently from missing values. A low-confidence field may still contain a usable value, allowing the system to calculate real EMI and FOIR metrics while routing the case for review. A genuinely missing critical field is represented as `None`, causing the system to short-circuit affordability calculations and return a `MISSING_CRITICAL_FIELD` reason. Both situations are recorded accurately in the audit trail.

The third failure mode is document quality. Scanned or image-only PDFs that contain no extractable text trigger a `NoExtractableTextError` and return a 422 response. A production implementation would extend this path with OCR processing.

The fourth failure mode is invalid uploads. The API validates both content type and PDF magic bytes (`%PDF`) before processing. Files that fail validation are rejected with a client error rather than entering the extraction pipeline.

The final failure mode is prompt injection within uploaded documents. Because the LLM is only responsible for extraction and never makes lending decisions, document instructions cannot influence the rules engine. Additionally, the extraction prompt explicitly treats document content as data to be read rather than instructions to be followed.

---

### What would change for production deployment and scaling?

The API layer is stateless and can be scaled horizontally behind a load balancer. The primary bottleneck is the LLM extraction step, which introduces latency, cost, and rate-limit constraints. In production, extraction would be moved to an asynchronous worker queue, with the API returning a job identifier and notifying clients when processing is complete.

The rules engine and decision router are pure functions and therefore scale independently without additional architectural complexity. SQLite would be replaced by PostgreSQL through a configuration change to `DATABASE_URL`, leveraging SQLAlchemy's database abstraction. Monetary calculations would migrate from floating-point arithmetic to `Decimal` for precision.

Additional production improvements would include OCR support for scanned documents, idempotency keys for safe retries, structured audit logging, centralized secret management with rotation, encryption of sensitive applicant data at rest, and careful review of LLM-provider retention policies such as zero-data-retention configurations.
