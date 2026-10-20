"""Jinja2 rendering of OntologyDoc objects into static HTML."""

from __future__ import annotations

from importlib import resources

from jinja2 import Environment, PackageLoader, select_autoescape

from .model import OntologyDoc


def _environment() -> Environment:
    env = Environment(
        loader=PackageLoader("onto_to_pages", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


_ENV = _environment()


def render_ontology_page(
    doc: OntologyDoc,
    *,
    downloads: list[tuple[str, str]],
    theme: str,
    site_title: str | None,
    static_prefix: str = "",
    show_logo: bool = True,
    back_href: str | None = None,
) -> str:
    template = _ENV.get_template("ontology.html")
    return template.render(
        doc=doc,
        downloads=downloads,
        theme=theme,
        site_title=site_title,
        static_prefix=static_prefix,
        show_logo=show_logo,
        back_href=back_href,
    )


def render_index_page(
    entries: list[tuple[OntologyDoc, str]],
    *,
    theme: str,
    site_title: str,
    show_logo: bool = True,
) -> str:
    template = _ENV.get_template("index.html")
    return template.render(
        entries=entries,
        theme=theme,
        site_title=site_title,
        static_prefix="",
        show_logo=show_logo,
    )


# Extensions written as bytes rather than decoded text (images, fonts, ...).
_BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}


def static_files() -> list[tuple[str, bytes | str]]:
    """Return (name, contents) for every file under static/, text or bytes as appropriate."""
    out = []
    static_dir = resources.files("onto_to_pages").joinpath("static")
    for item in static_dir.iterdir():
        if not item.is_file():
            continue
        if item.suffix.lower() in _BINARY_EXTENSIONS:
            out.append((item.name, item.read_bytes()))
        else:
            out.append((item.name, item.read_text()))
    return out
