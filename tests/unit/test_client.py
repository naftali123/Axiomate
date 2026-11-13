"""The model client, against a stand-in for the SDK. No test calls the model."""
from types import SimpleNamespace

import pytest

anthropic = pytest.importorskip("anthropic")

from axiomate.errors import AxiomateError  # noqa: E402
from axiomate.interpret.client import make_client  # noqa: E402
from axiomate.interpret.prompt import INSTRUCTIONS, MODEL  # noqa: E402
from axiomate.interpret.reply import Reply  # noqa: E402


class Sdk:
    def __init__(self, answer):
        self.answer, self.requests = answer, []
        self.messages = SimpleNamespace(parse=self.parse)

    def parse(self, **request):
        self.requests.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def response(stop_reason="end_turn", parsed=Reply(candidates=[])):
    usage = SimpleNamespace(input_tokens=40, output_tokens=7, cache_read_input_tokens=1200, cache_creation_input_tokens=0)
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed, model="served-model", usage=usage)


def test_request_holds_only_instructions_and_text_and_the_record_has_the_counts():
    sdk = Sdk(response())
    record = make_client(sdk=sdk)("CONTEXT\n...\nSEGMENT\nRevenue was $1.")
    request = sdk.requests[0]
    assert request["model"] == MODEL and request["output_format"] is Reply
    assert request["system"] == [{"type": "text", "text": INSTRUCTIONS, "cache_control": {"type": "ephemeral"}}]
    assert request["messages"] == [{"role": "user", "content": "CONTEXT\n...\nSEGMENT\nRevenue was $1."}]
    assert record == {"reply": {"candidates": []}, "served_model": "served-model", "input_tokens": 1240,
                      "output_tokens": 7, "cache_read_input_tokens": 1200, "cache_creation_input_tokens": 0}


@pytest.mark.parametrize("answer", [response(stop_reason="refusal", parsed=None), response(stop_reason="max_tokens"),
                                    ValueError("not the reply shape")])
def test_a_reply_that_cannot_be_used_fails_alone(answer):
    with pytest.raises(AxiomateError) as raised:
        make_client(sdk=Sdk(answer))("text")
    assert raised.value.code == "reply_failed"


def test_a_service_failure_is_reported_as_unavailable():
    with pytest.raises(AxiomateError) as raised:
        make_client(sdk=Sdk(anthropic.APIConnectionError(request=None)))("text")
    assert raised.value.code == "model_unavailable"
