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

## 4. Use Decimal for money inside the rules engine

**Date:** 2026-11-08 | **Status:** Accepted

The rules engine accepts and returns `Decimal` only. `_require_decimal()` raises
`TypeError` for any other type, so a float cannot reach money arithmetic
unnoticed. The flag checks validate types too, because comparing a `Decimal`
with a float does not raise on its own.

- **Conversion:** `analysis.to_decimal()` converts through `str`, so an extracted
  `0.1` becomes `Decimal("0.1")`, not `0.1000000000000000055…`.
- **Rounding:** EMI is rounded to the paisa with `ROUND_HALF_UP`; Python's
  default is half-even. ₹1,00,000.05 over 2 months at 0% gives ₹50,000.03.
- **FOIR is not rounded.** It uses the rounded EMI, the amount the borrower
  pays, and is compared with the limit unrounded, so rounding cannot move a
  case across the limit.
- **Paisa residue:** ₹1,00,000 at 0% over 3 months gives ₹33,333.33 a month,
  one paisa short in total. A repayment schedule would add the residue to the
  last instalment. LoanLens estimates affordability and does not build
  schedules, so it ignores the residue.
- **Boundary:** the API and database still carry floats; routes convert with
  `float()` after rounding. Pydantic v2 serialises `Decimal` as a JSON string,
  which would break the UI's numeric check, and SQLite has no decimal type.
  Production would store `Numeric(14, 2)` on PostgreSQL and send amounts as
  strings or integer paisa.

## 5. Threshold limits are inclusive

**Date:** 2026-11-08 | **Status:** Accepted

A value exactly on a limit passes: a FOIR of exactly 0.50, an income of
exactly ₹15,000 and a request of exactly 20 times income are not flagged.
Lender policies are usually written as "FOIR up to 50%", "minimum income
₹15,000" and "up to 20 times income", which read as inclusive. Tests check
each limit at the boundary and one step beyond it. Decimal arithmetic makes the
boundary exact; with floats, a FOIR that should be 0.50 can come out as
0.5000000001.

## 6. Lending policy is a parameter, not module constants

**Date:** 2026-11-08 | **Status:** Accepted

The limits and the default annual rate live in a frozen `LendingPolicy`
dataclass. `evaluate_risk_flags()` requires the policy as a keyword argument,
so the engine never falls back to a policy on its own; `analyze_applicant()`
passes `DEFAULT_POLICY` unless the caller supplies another. The dataclass is
frozen so a policy cannot change during a request. Policies are still defined
in code; loading them from configuration and storing the policy version with
each decision is future work.

## 7. B1 rules engine rewrite: behaviour differences

**Date:** 2026-11-08 | **Status:** Accepted

The module was rewritten from an empty file, tests first. Running the old test
file against the new module fails all 12 tests: 5 on the new Decimal type
check and 7 on the new `evaluate_risk_flags` signature.

| Area | Before | After |
| --- | --- | --- |
| EMI | Unrounded float (19928.585887710702) | `Decimal`, half-up to the paisa (19928.59) |
| FOIR input | Unrounded EMI | Rounded EMI; FOIR itself unrounded |
| Float inputs | Accepted | `TypeError` in the engine; `analysis` converts through `str` |
| Thresholds | Module constants `FOIR_THRESHOLD`, `MINIMUM_MONTHLY_INCOME`, `LOAN_INCOME_MULTIPLE` | `LendingPolicy` fields; constants removed |
| Default rate | `12.0` in `analysis.py`, read via `.get("annual_interest_rate")`, a key no schema provides | `policy.default_annual_rate` |
| `evaluate_risk_flags` | Five arguments, including `existing_emis` and `tenure_months` | Keyword-only `foir`, `monthly_income`, `requested_amount`, `policy` |
| Missing or non-positive guard | Returned `MISSING_CRITICAL_FIELD`, labelling zero income as missing | Removed: unreachable because `validate_inputs()` runs first and labels it `INVALID_VALUE` |
| Zero income in `calculate_foir` | `ValueError` | `ValueError` for Decimal; a float raises `TypeError` first |
| Limit operators | `>`, `<`, `>`, untested | Unchanged; tested at each boundary and documented |
| Review-path placeholders | `0.0` | `Decimal("0")`; the API still returns `0.0` |
| API and database | float | Still float, converted in the routes |