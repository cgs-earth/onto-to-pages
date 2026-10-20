from pathlib import Path

from onto_to_pages.config import Config, load_config


def test_cli_flags_override_file_values(tmp_path):
    config_file = tmp_path / "onto-to-pages.toml"
    config_file.write_text(
        'input = "./ontologies"\noutput = "./dist"\ntheme = "light"\n'
    )

    cfg = load_config(
        config_path=config_file,
        input_path=Path("override.ttl"),
        output_path=None,
        base_uri=None,
        site_title=None,
        theme=None,
    )

    assert cfg.input == Path("override.ttl")
    assert cfg.output == Path("./dist")  # kept from file
    assert cfg.theme == "light"  # kept from file


def test_defaults_without_any_config():
    cfg = load_config(
        config_path=None,
        input_path=None,
        output_path=None,
        base_uri=None,
        site_title=None,
        theme=None,
    )
    assert cfg == Config()
