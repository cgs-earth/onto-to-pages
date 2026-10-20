from pathlib import Path

from onto_to_pages.config import Config
from onto_to_pages.build import run_build

FIXTURE = Path(__file__).parent / "fixtures" / "example.ttl"


def test_single_file_build_writes_expected_files(tmp_path):
    cfg = Config(input=FIXTURE, output=tmp_path / "dist")
    results = run_build(cfg)

    assert len(results) == 1
    out_dir = results[0].output_dir
    assert (out_dir / "index.html").is_file()
    assert (out_dir / "example.ttl").is_file()
    assert (out_dir / "example.xml").is_file()
    assert (out_dir / "example.json").is_file()
    assert (out_dir / "_static" / "style.css").is_file()

    html = (out_dir / "index.html").read_text()
    assert "Example Vocabulary" in html
    assert "Dog" in html
    assert "domesticated canine" in html


def test_directory_build_produces_top_level_index(tmp_path):
    input_dir = tmp_path / "ontologies"
    input_dir.mkdir()
    (input_dir / "example.ttl").write_text(FIXTURE.read_text())

    cfg = Config(input=input_dir, output=tmp_path / "dist")
    results = run_build(cfg)

    assert len(results) == 1
    assert (cfg.output / "index.html").is_file()
    assert (cfg.output / "example" / "index.html").is_file()

    top_level_html = (cfg.output / "index.html").read_text()
    assert "Example Vocabulary" in top_level_html


def test_non_rdf_json_files_are_skipped_not_listed_as_ontologies(tmp_path):
    # Regression test: a directory scan used to treat every "*.json" file as
    # a JSON-LD ontology candidate. rdflib's json-ld parser doesn't raise on
    # plain (non-RDF) JSON, it just yields zero triples, so things like
    # package.json/tsconfig.json were silently listed as blank "ontologies".
    input_dir = tmp_path / "repo"
    input_dir.mkdir()
    (input_dir / "example.ttl").write_text(FIXTURE.read_text())
    (input_dir / "package.json").write_text('{"name": "not-an-ontology", "version": "1.0.0"}')
    (input_dir / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}')

    node_modules = input_dir / "node_modules" / "some-dep"
    node_modules.mkdir(parents=True)
    (node_modules / "data.ttl").write_text("@prefix ex: <https://example.org/dep#> .\nex:Thing a ex:NotReal .\n")

    cfg = Config(input=input_dir, output=tmp_path / "dist")
    results = run_build(cfg)

    assert len(results) == 1
    assert results[0].source_file.name == "example.ttl"
