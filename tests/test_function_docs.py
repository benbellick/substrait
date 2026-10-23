# SPDX-License-Identifier: Apache-2.0

import runpy
import shutil

import mkdocs_gen_files
import pytest
import yaml
from tests.helpers import EXTENSIONS_DIR, REPO_ROOT, SITE_EXAMPLES_DIR


@pytest.fixture
def function_docs_workspace(tmp_path, monkeypatch):
    script_path = "site/docs/extensions/generate_function_docs.py"
    script = tmp_path / script_path
    script.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / script_path, script)

    extensions = tmp_path / "extensions"
    extensions.mkdir()
    for source in [
        EXTENSIONS_DIR / "functions_table.yaml",
        SITE_EXAMPLES_DIR / "extensions" / "producer_resolved_table_function.yaml",
    ]:
        shutil.copyfile(source, extensions / source.name)

    generated_docs = tmp_path / "generated"

    def open_generated_doc(path, mode):
        output = generated_docs / path
        output.parent.mkdir(parents=True, exist_ok=True)
        return output.open(mode)

    monkeypatch.setitem(mkdocs_gen_files.__dict__, "open", open_generated_doc)
    return script, extensions, generated_docs


def test_table_function_catalog_documents_return_types(function_docs_workspace):
    script, _extensions, generated_docs = function_docs_workspace
    runpy.run_path(str(script))

    catalog = (generated_docs / "extensions" / "functions_table.md").read_text()
    assert "Table Functions" in catalog
    assert "generate_series" in catalog
    assert "-> `struct<i64>`" in catalog

    producer_resolved = (
        generated_docs / "extensions" / "producer_resolved_table_function.md"
    ).read_text()
    assert (
        "parse_records(`payload: string`, `schema: string`): -> "
        "`output schema determined by the producer`"
    ) in producer_resolved


@pytest.mark.parametrize("section", ["scalar_functions", "table_functions"])
@pytest.mark.parametrize("argument_name", [None, "t"])
def test_function_catalog_documents_type_arguments(
    function_docs_workspace, section, argument_name
):
    script, extensions, generated_docs = function_docs_workspace
    type_argument = {"type": "any1"}
    if argument_name is not None:
        type_argument["name"] = argument_name
    extension = {
        "urn": "extension:org.example:typed_functions",
        section: [
            {
                "name": "typed_call",
                "impls": [
                    {
                        "args": [{"name": "value", "value": "any1"}, type_argument],
                        "return": "struct<any1>",
                    }
                ],
            }
        ],
    }
    (extensions / "typed_functions.yaml").write_text(yaml.safe_dump(extension))
    runpy.run_path(str(script))

    catalog = (generated_docs / "extensions" / "typed_functions.md").read_text()
    type_label = "<type> any1"
    if argument_name is not None:
        type_label = f"{argument_name}: {type_label}"
    assert f"typed_call(`value: any1`, `{type_label}`): -> `struct<any1>`" in catalog
