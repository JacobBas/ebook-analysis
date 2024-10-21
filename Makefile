format:
	uv run isort .
	uv run ruff format .

run:
	uv run main.py