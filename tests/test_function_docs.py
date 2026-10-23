# SPDX-License-Identifier: Apache-2.0

import runpy
import shutil

import mkdocs_gen_files
from tests.helpers import EXTENSIONS_DIR, REPO_ROOT, SITE_EXAMPLES_DIR


def test_table_function_catalog_documents_return_types(tmp_path, monkeypatch):
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
    runpy.run_path(str(script))

    catalog = (generated_docs / "extensions" / "functions_table.md").read_text()
    assert "Table Functions" in catalog
    assert "generate_series" in catalog
    assert "-> `struct<i64>`" in catalog
    assert (
        "unnest(`input1: list<any1>`, `input2: list<any2>`): -> `struct<any1?, any2?>`"
    ) in catalog

    producer_resolved = (
        generated_docs / "extensions" / "producer_resolved_table_function.md"
    ).read_text()
    assert (
        "parse_records(`payload: string`, `schema: string`): -> "
        "`output schema determined by the producer`"
    ) in producer_resolved
