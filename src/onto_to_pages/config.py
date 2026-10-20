"""Configuration for a build: CLI flags merged over an optional TOML file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_FILENAMES = ("onto-to-pages.toml", ".onto-to-pages.toml")


@dataclass
class Config:
    input: Path = Path(".")
    output: Path = Path("./dist")
    base_uri: str | None = None
    site_title: str | None = None
    theme: str = "auto"  # "auto" | "light" | "dark"
    extensions: list[str] = field(default_factory=list)
    show_logo: bool = True

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        data = tomllib.loads(path.read_text())
        return cls(
            input=Path(data.get("input", ".")),
            output=Path(data.get("output", "./dist")),
            base_uri=data.get("base_uri"),
            site_title=data.get("site_title"),
            theme=data.get("theme", "auto"),
            extensions=list(data.get("extensions", [])),
            show_logo=bool(data.get("show_logo", True)),
        )


def find_default_config(start: Path) -> Path | None:
    for name in DEFAULT_CONFIG_FILENAMES:
        candidate = start / name
        if candidate.is_file():
            return candidate
    return None


def load_config(
    *,
    config_path: Path | None,
    input_path: Path | None,
    output_path: Path | None,
    base_uri: str | None,
    site_title: str | None,
    theme: str | None,
    show_logo: bool | None = None,
) -> Config:
    """Build the effective :class:`Config` for a run.

    Precedence: explicit CLI flags > values from a config file > defaults.
    """
    file_path = config_path or find_default_config(Path.cwd())
    cfg = Config.from_file(file_path) if file_path else Config()

    if input_path is not None:
        cfg.input = input_path
    if output_path is not None:
        cfg.output = output_path
    if base_uri is not None:
        cfg.base_uri = base_uri
    if site_title is not None:
        cfg.site_title = site_title
    if theme is not None:
        cfg.theme = theme
    if show_logo is not None:
        cfg.show_logo = show_logo

    return cfg
