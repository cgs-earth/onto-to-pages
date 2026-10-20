"""Mapping between file extensions and the RDF serializations rdflib understands."""

from __future__ import annotations

from pathlib import Path

# Extensions we look for when scanning a directory for ontology source files.
SOURCE_EXTENSIONS = {
    ".ttl": "turtle",
    ".n3": "n3",
    ".nt": "nt",
    ".owl": "xml",
    ".rdf": "xml",
    ".xml": "xml",
    ".jsonld": "json-ld",
    ".json": "json-ld",
    ".trig": "trig",
}

# Formats offered as "download this vocabulary as..." buttons on the rendered
# page, keyed by the file extension written to the output directory.
DOWNLOAD_FORMATS = {
    "ttl": "turtle",
    "xml": "pretty-xml",
    "json": "json-ld",
    "nt": "nt",
}


def guess_rdf_format(path: Path) -> str | None:
    """Best-effort guess of the rdflib parser format for a given file path."""
    return SOURCE_EXTENSIONS.get(path.suffix.lower())


def find_source_files(root: Path, extensions: set[str] | None = None) -> list[Path]:
    """Recursively find candidate RDF source files under ``root``."""
    exts = extensions or set(SOURCE_EXTENSIONS)
    return sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts
    )
