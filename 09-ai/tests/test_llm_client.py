import pytest
from llm_client import CLASSIFY_INVOICE_TOOL, LLMSuggestion, MockLLMClient


def test_mock_client_returns_the_response_keyed_by_invoice_id_in_the_prompt():
    suggestion = LLMSuggestion(
        vendor_identified="Test Vendor", suggested_account_code="ACC-001",
        suggested_entity_code="ENT-001", confidence=0.9, reasoning="test",
    )
    client = MockLLMClient({"INV-0001": suggestion})
    result = client.classify_invoice("Invoice INV-0001 (AP). Vendor name...")
    assert result is suggestion


def test_mock_client_raises_for_an_invoice_it_has_no_canned_response_for():
    client = MockLLMClient({"INV-0001": LLMSuggestion("V", "A", "E", 0.9, "r")})
    with pytest.raises(KeyError):
        client.classify_invoice("Invoice INV-9999 (AP). ...")


def test_classify_invoice_tool_schema_is_strict_and_complete():
    assert CLASSIFY_INVOICE_TOOL["strict"] is True
    schema = CLASSIFY_INVOICE_TOOL["input_schema"]
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    assert required == {"vendor_identified", "suggested_account_code", "suggested_entity_code", "confidence", "reasoning"}
