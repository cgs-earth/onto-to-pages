.PHONY: build serve test clean

build:
	uv run onto-to-pages tests/fixtures -o dist --title "Example Vocabularies"

serve: build
	uv run python -m http.server 8000 --directory dist

test:
	uv run pytest

clean:
	rm -rf dist
