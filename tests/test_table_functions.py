# SPDX-License-Identifier: Apache-2.0

import pytest
import yaml
from tests.coverage.extensions import validate_nullability_markers
from tests.helpers import EXTENSIONS_DIR, load_extension


@pytest.fixture
def table_functions():
    return load_extension(EXTENSIONS_DIR / "functions_table.yaml")


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
