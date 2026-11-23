import pytest

from app.services.templating import MissingVariables, extract_variables, render


def test_extract_variables_unique_in_order():
    assert extract_variables("{{b}} then {{a}} then {{b}}") == ["b", "a"]


def test_extract_allows_spaces_inside_braces():
    assert extract_variables("Hi {{ name }}") == ["name"]


def test_render_fills_values():
    out = render("Post on {{platform}} about {{product}}", {"platform": "Instagram", "product": "hoodies"})
    assert out == "Post on Instagram about hoodies"


def test_render_reports_all_missing():
    with pytest.raises(MissingVariables) as e:
        render("{{a}} {{b}} {{c}}", {"b": "x"})
    assert e.value.names == ["a", "c"]


def test_blank_value_counts_as_missing():
    with pytest.raises(MissingVariables):
        render("{{a}}", {"a": "   "})


def test_values_are_not_expanded_again():
    assert render("{{a}}", {"a": "{{b}}", "b": "oops"}) == "{{b}}"
