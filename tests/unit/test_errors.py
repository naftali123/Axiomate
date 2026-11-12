from axiomate.errors import AxiomateError


def test_error_carries_code_field_and_message():
    error = AxiomateError("span_mismatch", "quote does not match the stored text", field="quote")
    assert error.code == "span_mismatch"
    assert error.field == "quote"
    assert str(error) == "quote does not match the stored text"
    assert error.to_dict() == {
        "error": "span_mismatch",
        "field": "quote",
        "message": "quote does not match the stored text",
    }


def test_field_is_optional():
    assert AxiomateError("not_found", "no such document").to_dict()["field"] is None
