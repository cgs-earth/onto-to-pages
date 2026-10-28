# onto-to-pages

Generate a static documentation site for an RDF vocabulary/ontology, built on
[rdflib](https://rdflib.readthedocs.io/) — no pyLODE. Run it locally to write
HTML to disk, or drop it into a GitHub Actions workflow to publish straight to
GitHub Pages.

The generated docs pull from whatever documentation annotations are present
on a term: `rdfs:label`/`rdfs:comment`, SKOS `prefLabel`/`definition`, and
Dublin Core title/description, in that order. Classes, object properties,
datatype properties, annotation properties, plain `rdf:Property` terms, and
named individuals each get their own section, with a short info icon (`i`)
explaining what the section means. Pages ship with a light/dark theme (CGS
palette) that respects the visitor's OS preference and can be toggled
manually.

## Install

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Run locally

```bash
# a single ontology file
uv run onto-to-pages path/to/vocab.ttl -o dist

# a directory of ontology files (scanned recursively for .ttl/.rdf/.owl/.jsonld/...)
uv run onto-to-pages ./ontologies -o dist --title "My Vocabularies"
```

Open `dist/index.html` in a browser. Supported input formats: Turtle, RDF/XML,
N3, N-Triples, JSON-LD, and TriG (whatever rdflib can parse, guessed from the
file extension).

Each generated page gets `.ttl`/`.xml`/`.json`/`.nt` buttons that open the serialization in the browser (with a separate download link),
serialized from the parsed graph regardless of the input format.

### Configuration file

Flags can also come from a TOML file, so a build is reproducible without a
long command line. See [`onto-to-pages.example.toml`](onto-to-pages.example.toml):

```bash
cp onto-to-pages.example.toml onto-to-pages.toml
uv run onto-to-pages   # picks up ./onto-to-pages.toml automatically
# or: uv run onto-to-pages -c path/to/config.toml
```

CLI flags always take precedence over the config file.

### CLI reference

```
onto-to-pages [input] [-o OUTPUT] [-c CONFIG] [--base-uri URI]
              [--title TITLE] [--theme {auto,light,dark}]
              [--logo | --no-logo]
```

The CGS logo shown in the sidebar is on by default; pass `--no-logo` (or set
`show_logo = false` in the config file) to turn it off.

## Use in CI (GitHub Pages)

This repo is itself a composite GitHub Action. A consumer repo's workflow can
call it directly:

```yaml
- name: Build ontology docs
  uses: cgs-earth/onto-to-pages@v0
  with:
    input_dir: ./ontologies
    output_dir: ./dist
    theme: auto
```

With `deploy: true` (the default), the action also uploads and deploys the
output to GitHub Pages. Set `deploy: false` if another step in the workflow
(e.g. a static site generator) needs to fold the generated docs into a larger
Pages build first — see [`pages.yml`](pages.yml) for an example that builds
the ontology docs into an Astro site's `public/` directory before Astro runs.

## Development

```bash
uv sync --group dev
uv run pytest
```

- `src/onto_to_pages/model.py` — walks an `rdflib.Graph` into plain dataclasses
  (`OntologyDoc`, `Entity`, ...) that know nothing about RDF/Jinja.
- `src/onto_to_pages/render.py` / `templates/` — Jinja2 templates that render
  those dataclasses to HTML.
- `src/onto_to_pages/build.py` — orchestrates parsing, rendering, and writing
  files to the output directory for both single-file and directory inputs.
