# SPDX-License-Identifier: Apache-2.0

import pytest
from jsonschema import Draft202012Validator, ValidationError
from tests.helpers import EXTENSIONS_DIR, REPO_ROOT, load_extension
from tests.type.test_type_grammar import parse_type_expression


@pytest.fixture
def table_functions():
    return load_extension(EXTENSIONS_DIR / "functions_table.yaml")


@pytest.fixture
def simple_extensions_schema():
    return load_extension(REPO_ROOT / "text" / "simple_extensions_schema.yaml")


def test_table_function_definitions_match_schema(
    table_functions, simple_extensions_schema
):
    Draft202012Validator(simple_extensions_schema).validate(table_functions)


def test_table_function_return_schema_may_be_omitted(
    table_functions, simple_extensions_schema
):
    del table_functions["table_functions"][0]["impls"][0]["return"]
    Draft202012Validator(simple_extensions_schema).validate(table_functions)


@pytest.mark.parametrize(
    "options",
    [
        {},
        {
            "on_error": {
                "values": ["ERROR", "NULL"],
                "description": "Behavior when an error occurs",
            },
            "rounding": {"values": ["FLOOR", "CEILING"]},
        },
    ],
)
def test_table_function_options_match_schema(
    table_functions, simple_extensions_schema, options
):
    table_functions["table_functions"][0]["impls"][0]["options"] = options
    Draft202012Validator(simple_extensions_schema).validate(table_functions)


@pytest.mark.parametrize(
    "options",
    [
        [],
        {"on_error": {}},
        {"on_error": {"values": "ERROR"}},
        {"on_error": {"values": [123]}},
        {"on_error": {"values": ["ERROR"], "unknown": True}},
    ],
)
def test_table_function_options_reject_invalid_definitions(
    table_functions, simple_extensions_schema, options
):
    table_functions["table_functions"][0]["impls"][0]["options"] = options
    with pytest.raises(ValidationError):
        Draft202012Validator(simple_extensions_schema).validate(table_functions)


def test_unnest_supports_one_through_four_lists(table_functions):
    unnest = next(
        function
        for function in table_functions["table_functions"]
        if function["name"] == "unnest"
    )
    assert [len(impl["args"]) for impl in unnest["impls"]] == [1, 2, 3, 4]

    for impl in unnest["impls"]:
        argument_count = len(impl["args"])
        parameters = [f"any{index}" for index in range(1, argument_count + 1)]
        assert "variadic" not in impl
        assert [arg["value"] for arg in impl["args"]] == [
            f"list<{parameter}>" for parameter in parameters
        ]
        assert impl["nullability"] == "DECLARED_OUTPUT"
        fields = [
            f"{parameter}?" if argument_count > 1 else parameter
            for parameter in parameters
        ]
        assert impl["return"] == f"struct<{', '.join(fields)}>"
        for arg in impl["args"]:
            parse_type_expression(arg["value"])
        parse_type_expression(impl["return"])
