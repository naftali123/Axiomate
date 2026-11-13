"""The one place that calls the model.

`make_client` returns a function from request text to a reply record, the
shape `interpret` expects. The request holds the instructions and filing text
only. The API key is read from the environment by the SDK and never written.

Two kinds of failure are kept apart. A failure of one reply (the model
declined, ran out of room, or returned something that does not parse) is
`reply_failed`: the run counts it and goes on. A failure of the service
(no key, no network, a refused request, rate limit after retries) is `model_unavailable`: the run
stops, so an outage is never recorded as a finished run.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from axiomate.errors import AxiomateError
from axiomate.interpret.prompt import INSTRUCTIONS, MODEL
from axiomate.interpret.reply import Reply

MAX_TOKENS = 16000
EFFORT = "high"


def make_client(model: Optional[str] = None, *, sdk: Any = None) -> Callable[[str], dict[str, Any]]:
    """A client for `interpret`. `sdk` is an `anthropic.Anthropic` instance; one is created when not given."""
    try:
        import anthropic
    except ImportError:
        raise AxiomateError("model_unavailable", "the anthropic package is not installed (pip install axiomate[model])", None) from None
    model = model or MODEL
    try:
        sdk = sdk or anthropic.Anthropic()
    except anthropic.AnthropicError as error:
        raise AxiomateError("model_unavailable", f"the model service could not be used: {error}", None) from None
    system = [{"type": "text", "text": INSTRUCTIONS, "cache_control": {"type": "ephemeral"}}]

    def call(request: str) -> dict[str, Any]:
        try:
            response = sdk.messages.parse(
                model=model, max_tokens=MAX_TOKENS, system=system, output_config={"effort": EFFORT},
                messages=[{"role": "user", "content": request}], output_format=Reply)
        except anthropic.APIStatusError as error:
            raise AxiomateError("model_unavailable", f"the model service answered {error.status_code}: {error.message}", None) from None
        except anthropic.AnthropicError as error:
            raise AxiomateError("model_unavailable", f"the model service could not be used: {error}", None) from None
        except ValueError as error:  # the reply text does not fit the reply shape
            raise AxiomateError("reply_failed", f"the reply could not be parsed: {error}", None) from None
        if response.stop_reason != "end_turn" or response.parsed_output is None:
            raise AxiomateError("reply_failed", f"the model stopped with {response.stop_reason} and no usable reply", None)
        usage = response.usage
        read = getattr(usage, "cache_read_input_tokens", None) or 0
        written = getattr(usage, "cache_creation_input_tokens", None) or 0
        return {
            "reply": response.parsed_output.model_dump(mode="json"), "served_model": response.model,
            "input_tokens": usage.input_tokens + read + written, "output_tokens": usage.output_tokens,
            "cache_read_input_tokens": read, "cache_creation_input_tokens": written,
        }

    return call
