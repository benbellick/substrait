# SPDX-License-Identifier: Apache-2.0

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError
from tests.coverage.extensions import validate_nullability_markers
from tests.helpers import EXTENSIONS_DIR, REPO_ROOT, load_extension


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


def test_table_function_implementation_description_matches_schema(
    table_functions, simple_extensions_schema
):
    table_functions["table_functions"][0]["impls"][0]["description"] = (
        "Generates a series of 64-bit integers."
    )
    Draft202012Validator(simple_extensions_schema).validate(table_functions)


@pytest.mark.parametrize("nullability", ["MIRROR", "DECLARED_OUTPUT", "DISCRETE"])
def test_table_function_rejects_nullability_setting(
    table_functions, simple_extensions_schema, nullability
):
    table_functions["table_functions"][0]["impls"][0]["nullability"] = nullability
    with pytest.raises(ValidationError):
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


@pytest.mark.parametrize("level", ["function", "implementation"])
def test_table_function_deprecation_matches_schema(
    table_functions, simple_extensions_schema, level
):
    function = table_functions["table_functions"][0]
    target = function if level == "function" else function["impls"][0]
    target["deprecated"] = {
        "since": "0.1.0",
        "reason": "Use a replacement function.",
        "metadata": {"replacement": "new_series"},
    }
    Draft202012Validator(simple_extensions_schema).validate(table_functions)


@pytest.mark.parametrize("level", ["function", "implementation"])
def test_table_function_deprecation_requires_version(
    table_functions, simple_extensions_schema, level
):
    function = table_functions["table_functions"][0]
    target = function if level == "function" else function["impls"][0]
    target["deprecated"] = {"reason": "Use a replacement function."}
    with pytest.raises(ValidationError):
        Draft202012Validator(simple_extensions_schema).validate(table_functions)


def test_table_function_metadata_matches_schema(
    table_functions, simple_extensions_schema
):
    table_functions["table_functions"][0]["metadata"] = {
        "engine": {"name": "generate_series"}
    }
    Draft202012Validator(simple_extensions_schema).validate(table_functions)


@pytest.mark.parametrize(
    "argument_type, has_errors",
    [("i64?", True), ("list?<i64>", True), ("list<i64?>", False)],
)
def test_table_function_declarations_use_declared_output_validation(
    tmp_path, argument_type, has_errors
):
    extension = {
        "urn": "extension:org.example:table_functions",
        "table_functions": [
            {
                "name": "generate",
                "impls": [
                    {
                        "args": [{"name": "input", "value": argument_type}],
                        "return": "struct<i64?>",
                    },
                    {"args": [{"name": "input", "value": argument_type}]},
                ],
            }
        ],
    }
    (tmp_path / "functions_table.yaml").write_text(yaml.safe_dump(extension))
    errors = validate_nullability_markers(tmp_path)
    if has_errors:
        assert len(errors) == 2
        assert all("DECLARED_OUTPUT" in error for error in errors)
    else:
        assert errors == []


def test_generate_series_requires_explicit_step(table_functions):
    generate_series = next(
        function
        for function in table_functions["table_functions"]
        if function["name"] == "generate_series"
    )
    assert [
        [(arg["name"], arg["value"]) for arg in impl["args"]]
        for impl in generate_series["impls"]
    ] == [
        [("start", "i64"), ("stop", "i64"), ("step", "i64")],
        [("start", "i32"), ("stop", "i32"), ("step", "i32")],
    ]


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
        fields = [
            f"{parameter}?" if argument_count > 1 else parameter
            for parameter in parameters
        ]
        assert impl["return"] == f"struct<{', '.join(fields)}>"
