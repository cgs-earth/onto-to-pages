"""Command-line entry point for onto-to-pages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .build import run_build
from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onto-to-pages",
        description="Generate a static documentation site for an RDF vocabulary/ontology.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="A single RDF file, or a directory to scan for RDF files (default: config file or '.')",
    )
    parser.add_argument("-o", "--output", type=Path, help="Output directory (default: ./dist)")
    parser.add_argument("-c", "--config", type=Path, help="Path to a onto-to-pages.toml config file")
    parser.add_argument("--base-uri", help="Ontology IRI to prefer when a file defines more than one")
    parser.add_argument("--title", dest="site_title", help="Site title shown on the index page")
    parser.add_argument(
        "--theme",
        choices=["auto", "light", "dark"],
        help="Default color theme (visitors can still toggle it)",
    )
    parser.add_argument(
        "--extensions",
        help=(
            "Comma-separated file extensions to scan for when input is a directory "
            "(default: .ttl,.n3,.nt,.owl,.rdf,.xml,.jsonld,.json,.trig)"
        ),
    )
    logo_group = parser.add_mutually_exclusive_group()
    logo_group.add_argument(
        "--logo",
        dest="show_logo",
        action="store_true",
        default=None,
        help="Show the CGS logo in the sidebar (default)",
    )
    logo_group.add_argument(
        "--no-logo",
        dest="show_logo",
        action="store_false",
        help="Hide the CGS logo in the sidebar",
    )
    parser.add_argument("--version", action="version", version=f"onto-to-pages {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    extensions = None
    if args.extensions is not None:
        extensions = [e.strip() for e in args.extensions.split(",") if e.strip()]

    cfg = load_config(
        config_path=args.config,
        input_path=args.input,
        output_path=args.output,
        base_uri=args.base_uri,
        site_title=args.site_title,
        theme=args.theme,
        show_logo=args.show_logo,
        extensions=extensions,
    )

    try:
        results = run_build(cfg)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    for result in results:
        print(f"wrote {result.output_dir / 'index.html'}")
    print(f"done: {len(results)} ontology page(s) written to {cfg.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
