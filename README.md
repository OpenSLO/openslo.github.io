# OpenSLO website

This repository builds the OpenSLO website with MkDocs Material.
The development environment uses Python 3.13, the packages in `requirements.txt`,
and Ruff.

## Development

Run `make serve` to preview the website locally.
Run `make build` to write the website to `site/`.
Run `make check` to lint Python and test schema generation through MkDocs.

Pull requests run these checks and a strict website build in GitHub Actions.
Pushes to `main` publish the checked website to the `gh-pages` branch.
`docs/CNAME` preserves the `openslo.com` domain.

## Specification

Fix specification prose and examples in `OpenSLO/OpenSLO`'s `README.md` first.
Then run `make generate/specification SPEC_PATH=/path/to/OpenSLO` to update this
website's copy. The default path is `../OpenSLO`.
The importer adds website references and preserves separate links to the v2 draft.
It also identifies the SDK's stricter requirement for a v1 time window.

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

Run `make check/schema-source` to compare the manifest against the SDK's serialized
fields and govy validation plans. This check requires Go 1.26 or newer.
It checks rules, conditions, examples, values, and opaque value components against
the SDK revision pinned in `tools/schema-check/go.mod`.
Update that pin when importing a manifest from a different SDK revision.
CI runs this comparison before publication.
The same check validates complete YAML examples from the specification and
authored schema pages.

The MkDocs hook in `main.py` generates pages and navigation for every version and
object in the manifest.
`schema.py` and `templates/` render descriptions, values, examples, and validation
rules.
Builds use the checked-in manifest and require no Go toolchain or SDK checkout.

The SDK generator uses govydoc v0.1.1 to register durations as opaque strings.
Their `componentPlans` retain validation for the unit and numeric value.
The website displays these rules inside the duration panel and keeps their
conditions, values, and examples separate from the parent property's rules.
Components do not create child property headings or affect the parent's required
badge.

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

The generator also converts govydoc's `pkg.go.dev` symbol links to website links.
Object names use their generated pages, and shared types use `_types` targets.
Each version can add `_symbols` entries for fields, constants, and other types.
For example, `"SLOObjective.Operator": "slo.md#spec-objectives-items-op"` links
the Go field to its schema property.
Symbol names refer to the version's SDK package.
Use `package/import/path#Symbol` for symbols from another package.
Targets are relative to the version's object directory, as in `_types`.
These entries override inferred targets and do not collapse property definitions.
Links without a website target keep their original URLs.
Code examples remain unchanged.

Do not edit generated HTML under `site/`.
