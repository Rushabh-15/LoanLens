# Engineering decisions

## 1. Use Claude Haiku 5.5 for extraction

**Date:** 2026-10-14 | **Status:** Accepted

Use `claude-haiku-5-5` as the default model, configurable through
`CLAUDE_MODEL`. LoanLens needs fast, affordable extraction into a structured
schema. The model extracts fields; Python validation and underwriting rules
determine the application decision. Evaluate extraction quality on our own
documents before relying on the model for a broader workload.

### Evaluation budget

Pricing checked on 2026-10-14: for prompts up to 100,000 tokens, standard
Claude API requests cost $0.10 per million input tokens and $0.50 per million
output tokens. These per-token rates are one tenth of Haiku 4.5's $1.00 input
and $5.00 output rates. Longer prompts use a different price tier.

Planning assumptions: one request per document, approximately 2,000 total
input tokens and 1,000 billed output tokens, including thinking. This
estimate assumes no retries, prompt caching, or Batch API discounts.

| Cost component | Calculation | Estimated cost (USD) |
| --- | --- | --- |
| Input per document | 2,000 / 1,000,000 x $0.10 | $0.0002 |
| Output per document | 1,000 / 1,000,000 x $0.50 | $0.0005 |
| Total per document | $0.0002 + $0.0005 | $0.0007 |
| One 40-document evaluation | 40 x $0.0007 | $0.028 (about 3 cents) |

Use $5 as the planned evaluation budget. Whether it covers all planned runs
depends on actual token usage and request counts. D1 will measure real usage,
including thinking and any retries, and replace this estimate. Check the
Console's usage page after the first full evaluation and revise the budget
if needed. Mocked pytest runs make no paid Claude requests.

Sources: [model and pricing](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
and [Haiku 4.5 pricing comparison](https://www.anthropic.com/claude-haiku-5-5).

## 2. Omit sampling parameters

**Date:** 2026-10-14 | **Status:** Accepted

Remove the unused `TEMPERATURE` setting and omit `temperature`, `top_p`, and
`top_k` from Claude requests.

Haiku 5.5 rejects a supplied `temperature` unless it is `1`. If `top_p` is
supplied, it must be `0.99`; `top_k` is not accepted at all. Sending both
`temperature` and `top_p` also fails. These unsupported combinations produce
HTTP 400 responses. Omitting all three follows Anthropic's migration guidance
and avoids exposing settings that do not provide useful tuning for this model.

Use clear prompts and structured outputs to specify the extraction format,
then validate the extracted values in Python. Sampling settings are not a
substitute for input validation or evaluation.

Source, checked on 2026-10-14:
[Haiku 5.5 migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide#remove-sampling-parameters).

## 3. Invalid extracted values require human review

**Date:** 2026-10-14 | **Status:** Accepted

Invalid extracted values produce `NEEDS_REVIEW` with an `INVALID_VALUE`
flag. They do not, by themselves, justify an automated decline.

The extraction may be wrong: a document value can be misread, omitted, or
returned incorrectly by the model. For example, an extracted age of 16 could
reflect either the document or an extraction error. Even high extraction
confidence does not establish that the value is correct. A person must check
the source document and confirm or correct the value before anyone is turned
down on that basis.

Validation runs before EMI or FOIR calculations. Missing critical values
similarly trigger `MISSING_CRITICAL_FIELD` and human review. The reason names
the affected fields so the reviewer knows what to check, for example:
"Invalid value for age; routed to human review."

Automated decline remains reserved for underwriting-rule failures on valid
inputs when no review condition is present. This choice can increase manual
review work, but avoids automatically declining an applicant because of
unreliable extracted data.
