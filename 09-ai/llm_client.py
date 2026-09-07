"""LLM provider abstraction (Phase 12, PLAN.md §24).

Two implementations behind one interface, so the rest of accounting_agent.py
never knows or cares which one is running:

- MockLLMClient: a deterministic stand-in used for every test and the
  evaluation harness in this repo. It is clearly NOT a real model -- it's
  a lookup table of canned responses keyed by invoice_id, used to exercise
  the safety-policy logic (confidence handling, control checks, human
  review routing) without needing an API key or spending money on every
  test run. This project's no-real-data/no-overstated-capability rule
  applies here too: nothing in this codebase claims MockLLMClient's output
  reflects real model accuracy.
- AnthropicLLMClient: a real implementation using the Anthropic Messages
  API (Claude Haiku 4.5, chosen for cost -- this is a low-stakes structured
  classification call, not open-ended reasoning). Only used if
  ANTHROPIC_API_KEY is set; the `anthropic` import is deferred into the
  method that needs it so the rest of this module works without the
  package installed. Not exercised in this project's own test suite or
  evaluation run (no key was configured when this was built) -- it exists
  as the documented, correct integration point for a real run, per
  09-ai/README.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMSuggestion:
    """Raw model output, before any safety policy is applied."""
    vendor_identified: str
    suggested_account_code: str
    suggested_entity_code: str
    confidence: float
    reasoning: str


class LLMClient(Protocol):
    def classify_invoice(self, prompt: str) -> LLMSuggestion: ...


class MockLLMClient:
    """Deterministic stand-in for a real model, keyed by invoice_id embedded
    in the prompt. Raises if asked about an invoice_id it has no canned
    response for, rather than guessing -- a test fixture that silently
    falls back to a default would hide the exact scenario it's meant to
    exercise."""

    def __init__(self, responses: dict[str, LLMSuggestion]):
        self._responses = responses

    def classify_invoice(self, prompt: str) -> LLMSuggestion:
        for invoice_id, response in self._responses.items():
            if invoice_id in prompt:
                return response
        raise KeyError(f"MockLLMClient has no canned response for this prompt: {prompt[:100]}...")


CLASSIFY_INVOICE_TOOL = {
    "name": "classify_invoice",
    "description": (
        "Classify an invoice that a deterministic rule could not resolve on its own. "
        "Only use information present in the prompt -- never invent a vendor, account, "
        "or entity that wasn't given to you."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor_identified": {"type": "string", "description": "The vendor name as given in the prompt"},
            "suggested_account_code": {"type": "string", "description": "One of the account codes given in the prompt"},
            "suggested_entity_code": {"type": "string", "description": "One of the entity codes given in the prompt"},
            "confidence": {"type": "number", "description": "0.0-1.0, how confident this suggestion is"},
            "reasoning": {"type": "string", "description": "Brief, evidence-based explanation"},
        },
        "required": ["vendor_identified", "suggested_account_code", "suggested_entity_code", "confidence", "reasoning"],
        "additionalProperties": False,
    },
    "strict": True,
}


class AnthropicLLMClient:
    """Real provider. Requires the `anthropic` package and ANTHROPIC_API_KEY
    (or another credential source the SDK resolves automatically -- see
    09-ai/README.md). Uses forced, schema-strict tool use so the response is
    always exactly the shape classify_invoice expects -- no free-text
    parsing, no risk of the model returning prose instead of structured
    data."""

    def __init__(self, model: str = "claude-haiku-4-5"):
        import anthropic  # deferred: only needed if this class is actually used
        self._client = anthropic.Anthropic()
        self._model = model

    def classify_invoice(self, prompt: str) -> LLMSuggestion:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            tools=[CLASSIFY_INVOICE_TOOL],
            tool_choice={"type": "tool", "name": "classify_invoice"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "tool_use":
                data = block.input if isinstance(block.input, dict) else json.loads(block.input)
                return LLMSuggestion(**data)
        raise RuntimeError("model did not return a classify_invoice tool call")
