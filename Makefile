.PHONY: sync test lint check dashboard console-install console-check console-demo

sync:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

check: lint test

dashboard:
	uv run python -m controlplane.cli dashboard

console-install:
	cd console && pnpm install

console-check:
	cd console && pnpm typecheck && pnpm test && pnpm build

# Seeds a throwaway queue and serves the built console on http://127.0.0.1:8765 (token: $$CONSOLE_TOKEN)
console-demo:
	rm -f escalations.db && uv run python -m scripts.seed_console_demo --db escalations.db
	uv run python -m controlplane.console_api --db escalations.db
