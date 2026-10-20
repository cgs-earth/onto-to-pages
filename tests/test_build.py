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
