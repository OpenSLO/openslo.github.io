# OpenSLO website

This repository builds the OpenSLO website with MkDocs Material.
The development environment uses Python 3.13, the packages in `requirements.txt`,
and Ruff.

## Development

Run `make serve` to preview the website locally.
Run `make build` to write the website to `site/`.
Run `make check` to lint Python and test schema generation through MkDocs.

## Schema reference

The schema reference comes from `api.json`.
The OpenSLO Go SDK combines [govy validation plans](https://github.com/nobl9/govy)
with source comments through [govydoc](https://github.com/nieomylnieja/govydoc).
Its `internal/cmd/objectdoc` generator writes `docs/manifest.json`.

To update the website from an SDK checkout:

1. In the SDK checkout, run `make generate/govydoc` with its required Go toolchain.
2. In this repository, run `make generate/schema SDK_PATH=/path/to/go-sdk`.
   The default SDK path is `../go-sdk`.
   This command validates the manifest before it replaces `api.json`.
3. Review the `api.json` diff, then run `make check` and `make build`.

The MkDocs hook in `main.py` generates pages and navigation for every version and
object in the manifest.
`schema.py` and `templates/` render descriptions, values, examples, and validation
rules.
Builds use the checked-in manifest and require no Go toolchain or SDK checkout.

An authored page under `docs/schema/<version>/<kind>.md` can add examples around
the schema macros.
Otherwise, MkDocs creates the page in memory during the build.
Object filenames use lowercase kind names, such as `alertcondition.md`.

`property-links.json` selects properties that reference a shared definition.
Each version can define:

- `_types`: references keyed by the SDK's `typeInfo.name`.
- `_common`: references keyed by an exact property path, for all object kinds.
- An object kind, such as `SLO`: references keyed by an exact property path.

Object-specific paths take precedence over common paths, then type references.
Each entry contains a `link` and a Jinja `template` for its reference text.
Links are relative to the object page and include the definition's anchor.
For example, v1 `Metadata` points to `../v1.md#metadata`.

Referenced properties have linked headings and a **reference** badge.
They keep their field descriptions and validation rules, but omit their type
descriptions and descendants. The linked page contains that definition.
The generator expands a definition when its reference points to its own heading.
This keeps standalone objects complete while their inline uses link to them.

Inline alert wrappers retain fields such as `conditionRef` and `targetRef`.
Their `spec` properties link to the standalone specifications.
Do not edit generated HTML under `site/`.
