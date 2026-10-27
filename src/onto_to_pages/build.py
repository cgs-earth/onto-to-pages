"""Orchestrates a full build: find sources, parse, extract, render, write."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from .config import Config
from .model import OntologyDoc, build_ontology_doc
from .rdf_formats import DOWNLOAD_FORMATS, find_source_files, guess_rdf_format
from .render import render_index_page, render_ontology_page, static_files


@dataclass
class BuildResult:
    doc: OntologyDoc
    output_dir: Path
    source_file: Path


def _parse_graph(path: Path) -> Graph:
    fmt = guess_rdf_format(path)
    graph = Graph()
    graph.parse(path, format=fmt)
    if len(graph) == 0:
        # A loose extension match (.json in particular is ambiguous: plain
        # package.json/tsconfig.json etc. parse "successfully" as JSON-LD
        # with zero triples rather than raising) should not produce a blank
        # ontology page.
        raise ValueError(f"no RDF triples found in {path} (not an RDF/JSON-LD document?)")
    return graph


def _write_downloads(
    graph: Graph,
    out_dir: Path,
    basename: str,
    *,
    sibling_dir: Path | None = None,
) -> list[tuple[str, str]]:
    """Serialize ``graph`` into every download format; returns (label, href) pairs.

    If ``sibling_dir`` is given, each serialization is also copied there so
    that ``<term>.ttl`` resolves next to ``<term>/`` for content-negotiating
    redirects (e.g. w3id.org) that target the sibling path.
    """
    downloads = []
    for ext, fmt in DOWNLOAD_FORMATS.items():
        dest = out_dir / f"{basename}.{ext}"
        graph.serialize(destination=dest, format=fmt, encoding="utf-8")
        if sibling_dir is not None:
            sibling_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dest, sibling_dir / dest.name)
        downloads.append((ext, dest.name))
    return downloads


def _embeddable_jsonld(graph: Graph) -> str:
    """JSON-LD for ``graph``, made safe to drop inside a ``<script>`` element.

    Escaping ``<`` as ``\\u003c`` keeps literals like ``</script>`` or
    ``<!--`` from terminating the element early, and is still valid JSON.
    """
    return graph.serialize(format="json-ld").replace("<", "\\u003c")


def _write_static_assets(output_root: Path) -> None:
    static_dir = output_root / "_static"
    static_dir.mkdir(parents=True, exist_ok=True)
    for name, contents in static_files():
        dest = static_dir / name
        if isinstance(contents, bytes):
            dest.write_bytes(contents)
        else:
            dest.write_text(contents)


def _render_one(
    source: Path,
    out_dir: Path,
    cfg: Config,
    *,
    static_prefix: str,
    back_href: str | None = None,
    write_siblings: bool = False,
) -> BuildResult:
    graph = _parse_graph(source)
    doc = build_ontology_doc(graph, base_uri=cfg.base_uri, fallback_title=source.stem)
    doc.source_files = [source.name]

    out_dir.mkdir(parents=True, exist_ok=True)
    downloads = _write_downloads(
        graph,
        out_dir,
        source.stem,
        sibling_dir=out_dir.parent if write_siblings else None,
    )

    html = render_ontology_page(
        doc,
        downloads=downloads,
        jsonld=_embeddable_jsonld(graph),
        theme=cfg.theme,
        site_title=cfg.site_title,
        static_prefix=static_prefix,
        show_logo=cfg.show_logo,
        back_href=back_href,
    )
    (out_dir / "index.html").write_text(html)
    return BuildResult(doc=doc, output_dir=out_dir, source_file=source)


def run_build(cfg: Config) -> list[BuildResult]:
    cfg.output.mkdir(parents=True, exist_ok=True)
    extensions = set(cfg.extensions) if cfg.extensions else None

    if cfg.input.is_file():
        result = _render_one(cfg.input, cfg.output, cfg, static_prefix="")
        _write_static_assets(cfg.output)
        return [result]

    if not cfg.input.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {cfg.input}")

    sources = find_source_files(cfg.input, extensions)
    if not sources:
        raise FileNotFoundError(f"No RDF source files found under {cfg.input}")

    results: list[BuildResult] = []
    for source in sources:
        rel = source.relative_to(cfg.input).with_suffix("")
        out_dir = cfg.output / rel
        depth = len(rel.parts)
        static_prefix = "../" * depth
        back_href = f"{static_prefix}index.html" if len(sources) > 1 else None
        try:
            results.append(
                _render_one(
                    source,
                    out_dir,
                    cfg,
                    static_prefix=static_prefix,
                    back_href=back_href,
                    write_siblings=True,
                )
            )
        except Exception as err:  # one bad file should not sink the whole build
            print(f"WARNING: skipping {source} ({err})")

    entries = [
        (r.doc, str(r.output_dir.relative_to(cfg.output) / "index.html"))
        for r in results
    ]
    index_html = render_index_page(
        entries,
        theme=cfg.theme,
        site_title=cfg.site_title or "Ontology Documentation",
        show_logo=cfg.show_logo,
    )
    (cfg.output / "index.html").write_text(index_html)
    _write_static_assets(cfg.output)

    return results
