# SPDX-License-Identifier: Apache-2.0

import pytest
import yaml
from jsonschema import Draft202012Validator
from tests.coverage.extensions import validate_nullability_markers
from tests.helpers import EXTENSIONS_DIR, REPO_ROOT, load_extension


@pytest.fixture
def table_functions():
    return load_extension(EXTENSIONS_DIR / "functions_table.yaml")


def test_table_function_schema_supports_optional_properties(table_functions):
    schema = load_extension(REPO_ROOT / "text" / "simple_extensions_schema.yaml")
    function = table_functions["table_functions"][0]
    function["metadata"] = {"engine": "example"}
    function["deprecated"] = {"since": "0.1.0"}
    implementation = function["impls"][0]
    implementation["description"] = "The producer resolves the output schema."
    implementation["deprecated"] = {"since": "0.1.0"}
    implementation["options"] = {"on_error": {"values": ["ERROR", "EMPTY"]}}
    del implementation["return"]
    Draft202012Validator(schema).validate(table_functions)


@pytest.mark.parametrize(
    "argument_type, expected_error_count",
    [("list?<i64>", 2), ("list<i64?>", 0)],
)
def test_table_function_declarations_use_declared_output_validation(
    tmp_path, argument_type, expected_error_count
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
    assert len(errors) == expected_error_count
    assert all("DECLARED_OUTPUT" in error for error in errors)
