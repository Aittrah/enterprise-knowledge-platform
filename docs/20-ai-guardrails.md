# Milestone 20 — AI Guardrails

**Module:** `backend/app/guardrails/` · **Tests:** `backend/tests/test_guardrails.py` (17; suite 253)

## The security layer

```
question ──> screen_input (injection + jailbreak patterns, weighted score)
                blocked? -> polite refusal, agent_id="guardrail", audited
answer  ──> screen_output: groundedness · citation verification · PII masking
                report attached to every ChatOut as `guardrail`
```

| Guardrail | Mechanism |
|---|---|
| **Prompt injection** | weighted pattern families: instruction override ("ignore previous instructions", "reveal the system prompt"), `<system>` tag smuggling, "new instructions:" |
| **Jailbreak** | persona attacks (DAN, developer/unrestricted mode), "without restrictions", hypothetical-bypass phrasing |
| **Smuggling** | base64/rot13 markers and long encoded blobs (weighted, not auto-block) |
| **PII** | email, phone, credit card (**Luhn-validated** so 16-digit order numbers don't false-positive), CNIC/SSN, IBAN — detected and masked in answers (`s***@acme.com`, `[credit_card:…1111]`) |
| **Citation verification** | `[n]` must resolve to a retrieved source (M15 contract); invented citations invalidate trust |
| **Groundedness** | sentence-level support scoring of the answer against the exact retrieved chunks; unsupported claim-sentences are listed verbatim in the report |

`OutputReport.trustworthy` is true only when every claim-sentence is supported **and** no citation was invented — the UI's confidence seal upgrades to this signal (Module 21).

Benign phrasing is protected by tests ("summarize the *previous* quarter", "can you *ignore* case sensitivity") — single weak signals score below the block threshold.

Heuristics are deliberate for this milestone: deterministic, offline, auditable (every verdict records matched snippets). A classifier/LLM-judge slots in behind the same verdict shapes.
