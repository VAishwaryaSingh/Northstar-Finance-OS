# Prompts — AI Accounting Assistant (Phase 12)

## The prompt template

Built by `build_prompt()` in `accounting_agent.py`:

```text
Invoice {invoice_id} ({invoice_type}).
Vendor name as received: {vendor_name_raw}
Amount: {amount} {currency}
Account currently on the invoice: {account_code}
Reason this needed review: {review_reason}
Valid account codes: {known_accounts}
Valid entity codes: {known_entities}
Suggest the correct account and entity, with your confidence and reasoning.
Only use the account/entity codes listed above -- never invent one.
```

## Why it's built this way

- **Every valid answer is listed explicitly** (`Valid account codes`, `Valid entity codes`). This is the main defence against hallucination at the prompting layer — the model is never in a position where it *needs* to invent a code, because the full option set is right there. (The second, harder defence is `validate_suggestion()` in `accounting_agent.py`, which checks the actual output against the same list regardless of what the prompt said — a prompt instruction alone is advisory, not a control.)
- **No chain-of-thought is requested.** This is a low-stakes structured classification call (identify a vendor and an account), not a reasoning task — a `reasoning` field in the structured output is enough evidence for a human reviewer, and asking for step-by-step thinking would just add cost and latency for no real benefit here.
- **Only real invoice data goes in.** Nothing in the prompt is synthetic filler or a leading assumption about the answer — see AGENTS.md's no-hallucinated-data principle applied to the prompt side, not just the output side.

## Structured output: tool use, not free-text parsing

`llm_client.py`'s `CLASSIFY_INVOICE_TOOL` uses Anthropic's strict tool-use mode (`strict: true` + `additionalProperties: false` + `required`), with `tool_choice` forcing the model to call it. This guarantees `tool_use.input` is already schema-valid — no regex-parsing a JSON blob out of free text, no risk of the model wrapping its answer in explanatory prose that breaks a naive parser. See `AnthropicLLMClient.classify_invoice()`.

## Model choice

`claude-haiku-4-5` — this is a bounded, structured classification task (pick from a known list, score confidence, give a one-line reason), not open-ended reasoning, so the cheapest current model is the right one. At Haiku 4.5's pricing (~$1/$5 per million input/output tokens) a single invoice classification call — a few hundred input tokens, under 200 output tokens — costs a small fraction of a cent; a handful of test invoices costs well under a cent in total.

## What the prompt is deliberately *not* asked to do

It never asks the model to decide whether something should be auto-posted, approved, or bypassed — that decision is `process_invoice()`'s job in `accounting_agent.py`, made after the model responds, using Phase 11's deterministic rules plus the confidence/approval/hallucination checks. The model only ever answers "what do you think this is," never "should this go through."
