# SPDX-License-Identifier: Apache-2.0

import pytest
from jsonschema import Draft202012Validator
from tests.helpers import EXTENSIONS_DIR, REPO_ROOT, load_extension
from tests.type.test_type_grammar import parse_type_expression


@pytest.fixture
def table_functions():
    return load_extension(EXTENSIONS_DIR / "functions_table.yaml")


def test_table_function_definitions_match_schema(table_functions):
    schema = load_extension(REPO_ROOT / "text" / "simple_extensions_schema.yaml")
    Draft202012Validator(schema).validate(table_functions)


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
        assert len(impl["return"]["names"]) == argument_count
        assert impl["return"]["struct"]["types"] == [
            f"{parameter}?" if argument_count > 1 else parameter
            for parameter in parameters
        ]
        for arg in impl["args"]:
            parse_type_expression(arg["value"])
        for field_type in impl["return"]["struct"]["types"]:
            parse_type_expression(field_type)
