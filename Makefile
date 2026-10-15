.PHONY: sync test lint check dashboard

sync:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

check: lint test

dashboard:
	uv run python -m controlplane.cli dashboard
