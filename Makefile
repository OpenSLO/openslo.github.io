## Serve the MkDocs website.
serve:
	mkdocs serve

## Run checks.
check: check/python

## Run Python checks.
check/python:
	ruff check .

## Format files.
format: format/python

## Format Python files.
format/python:
	ruff format .