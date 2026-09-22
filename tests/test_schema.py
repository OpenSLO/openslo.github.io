from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urljoin, urlsplit

import markdown


ROOT = Path(__file__).resolve().parents[1]
SDK_DOCS = "https://pkg.go.dev/github.com/OpenSLO/go-sdk/pkg/openslo"
SYMBOL_EXAMPLE = f"[AlertPolicy]({SDK_DOCS}/v1#AlertPolicy)"
MULTILINE_EXAMPLE = (
    "line1\nline2\n\nline4\n  nested: true\n**literal**\n```text\nfence\n```"
)


def normalize(text):
    return " ".join(text.split())


class HTMLDocument(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.links = []
        self.tags = Counter()
        self.text = []
        self.sections = {}
        self.section = None
        self.heading = None
        self.in_summary = False
        self.details_depth = 0
        self.code_block = None
        self.code_blocks = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags[tag] += 1
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
            if self.section is not None:
                self.section["links"].append(attrs["href"])
        if tag in {"h1", "h2", "h3", "h4"}:
            self.section = {"text": [], "summary": [], "tables": 0, "links": []}
            self.heading = []
        if tag == "details":
            self.details_depth += 1
        if tag == "table" and self.section is not None and self.details_depth:
            self.section["tables"] += 1
        if tag == "summary":
            self.in_summary = True
        if tag == "pre":
            self.code_block = []
        if tag == "br":
            self.handle_data(" ")

    def handle_endtag(self, tag):
        if tag == "article":
            self.section = None
        if tag in {"h1", "h2", "h3", "h4"} and self.heading is not None:
            title = normalize("".join(self.heading)).removesuffix("¶")
            self.sections[title] = self.section
            self.heading = None
        if tag == "summary":
            self.in_summary = False
        if tag == "details":
            self.details_depth -= 1
        if tag == "pre" and self.code_block is not None:
            self.code_blocks.append("".join(self.code_block))
            self.code_block = None
        if tag in {"p", "td", "th", "li"}:
            self.handle_data(" ")

    def handle_data(self, data):
        self.text.append(data)
        if self.code_block is not None:
            self.code_block.append(data)
        if self.section is not None:
            self.section["text"].append(data)
            if self.in_summary:
                self.section["summary"].append(data)
        if self.heading is not None:
            self.heading.append(data)


def prose_text(value):
    return normalize("".join(HTMLDocument(markdown.markdown(value)).text))


def copy_project(destination):
    for name in (
        "main.py",
        "schema.py",
        "api.json",
        "property-links.json",
        "mkdocs.yml",
    ):
        shutil.copy2(ROOT / name, destination / name)
    for name in ("templates", "docs"):
        shutil.copytree(ROOT / name, destination / name)


def run_command(project, *arguments):
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60,
    )


class SchemaBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="openslo-schema-test-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.project = Path(cls.temporary.name)
        copy_project(cls.project)
        cls.api = json.loads((cls.project / "api.json").read_text())
        cls.api["openslo/v1"]["Probe"] = {
            "name": "Probe",
            "properties": [
                {
                    "path": "$",
                    "typeInfo": {"name": "Probe", "kind": "struct"},
                    "typeDoc": f"Probe exercises schema documentation. See {SYMBOL_EXAMPLE}.",
                    "rules": [{"description": "check the whole object"}],
                },
                {
                    "path": "$.mode",
                    "typeInfo": {"name": "string", "kind": "string"},
                    "fieldDoc": (
                        "First paragraph.\n\nSecond paragraph.\n\n- First item\n- Second item\n\n"
                        f"See [v2 SLO]({SDK_DOCS}/v2alpha#SLO), "
                        "[Duration](https://pkg.go.dev/time#Duration), "
                        f"and [Unknown]({SDK_DOCS}/v1#Unknown)."
                    ),
                    "typeDoc": (
                        "The mode type. See [Metadata][metadata].\n\n"
                        f"[metadata]: {SDK_DOCS}/v1#Metadata"
                    ),
                    "deprecatedDoc": (
                        f"Use the [replacement mode]({SDK_DOCS}/v1#SLOObjective.Operator)."
                    ),
                    "isHidden": True,
                    "values": ["true", "0", "<low|high>"],
                    "examples": [
                        "<script>alert(1)</script>",
                        '{"active":true}',
                        MULTILINE_EXAMPLE,
                        SYMBOL_EXAMPLE,
                    ],
                    "rules": [
                        {
                            "description": "property is required",
                            "errorCode": "required",
                            "conditions": ["'enabled' is true", "'count' > 0"],
                        },
                        {
                            "description": "match '^(good|bad)$'",
                            "details": "See https://example.com/rules?a=1&b=2.",
                            "examples": [
                                "'good' | 'bad'",
                                "<img src=x onerror=alert(1)>",
                            ],
                        },
                    ],
                },
                {
                    "path": "$.items",
                    "typeInfo": {"name": "[]string", "kind": "[]string"},
                },
                {
                    "path": "$.items[*]",
                    "typeInfo": {"name": "string", "kind": "string"},
                },
                {
                    "path": "$.itemsRef",
                    "typeInfo": {"name": "string", "kind": "string"},
                },
            ],
        }
        metadata = next(
            prop
            for prop in cls.api["openslo/v1"]["Service"]["properties"]
            if prop["path"] == "$.metadata"
        )
        metadata["fieldDoc"] = (
            metadata.get("fieldDoc", "") + f"\n\nSee {SYMBOL_EXAMPLE}."
        )
        (cls.project / "api.json").write_text(json.dumps(cls.api))
        links_file = cls.project / "property-links.json"
        links = json.loads(links_file.read_text())
        links["openslo/v1"]["Probe"] = {
            "items": {
                "link": "service.md#properties",
                "template": "See the [configured definition]({{ link }}).",
            }
        }
        links_file.write_text(json.dumps(links))
        source = cls.project / "docs/schema/v1/service.md"
        shutil.copy2(source, source.with_name("repeated.md"))
        result = run_command(cls.project, "-m", "mkdocs", "build")
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.build_log = result.stdout + result.stderr
        cls.site = cls.project / "site"
        links_file.write_text("{}")
        result = run_command(
            cls.project, "-m", "mkdocs", "build", "--site-dir", "expanded-site"
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.expanded_site = cls.project / "expanded-site"
        links_file.write_text(json.dumps(links))

    def page(self, path):
        return HTMLDocument((self.site / path).read_text())

    def test_no_references_expands_every_manifest_property(self):
        for version, objects in self.api.items():
            slug = version.rsplit("/", 1)[1]
            for kind, schema in objects.items():
                with self.subTest(version=version, kind=kind):
                    page = HTMLDocument(
                        (
                            self.expanded_site
                            / f"schema/{slug}/{kind.lower()}/index.html"
                        ).read_text()
                    )
                    for prop in schema["properties"]:
                        if prop["path"] == "$":
                            self.assertIn(
                                prose_text(prop["typeDoc"]),
                                normalize("".join(page.text)),
                            )
                            continue
                        section = page.sections[prop["path"][2:]]
                        content = normalize("".join(section["text"]))
                        for key in ("fieldDoc", "typeDoc", "deprecatedDoc"):
                            if prop.get(key):
                                self.assertIn(prose_text(prop[key]), content)
                        for value in prop.get("values", []) + prop.get("examples", []):
                            self.assertIn(normalize(value), content)
                        for rule in prop.get("rules", []):
                            for value in [
                                rule["description"],
                                rule.get("details", ""),
                                *rule.get("conditions", []),
                                *rule.get("examples", []),
                            ]:
                                self.assertIn(
                                    normalize(value).replace("'", ""),
                                    content.replace("'", ""),
                                )

    def test_all_objects_are_in_navigation_and_schema_links_resolve(self):
        index = self.page("schema/index.html")
        for version, objects in self.api.items():
            slug = version.rsplit("/", 1)[1]
            for kind in objects:
                self.assertIn(f"{slug}/{kind.lower()}/", index.links)
        pages = {
            path.resolve(): HTMLDocument(path.read_text())
            for path in (self.site / "schema").rglob("*.html")
        }
        targets = dict(pages)
        for path, page in pages.items():
            self.assertEqual(len(page.ids), len(set(page.ids)), path)
            for link in page.links:
                self.assertFalse(
                    link.startswith(SDK_DOCS) and link != f"{SDK_DOCS}/v1#Unknown",
                    f"{path}: {link}",
                )
                parts = urlsplit(link)
                if parts.scheme or parts.netloc or parts.path.startswith("/"):
                    continue
                target = (
                    (path.parent / unquote(parts.path)).resolve()
                    if parts.path
                    else path
                )
                if target.is_dir():
                    target /= "index.html"
                self.assertTrue(target.exists(), f"{path}: {link}")
                if parts.fragment:
                    if target not in targets:
                        targets[target] = HTMLDocument(target.read_text())
                    self.assertIn(
                        unquote(parts.fragment),
                        targets[target].ids,
                        f"{path}: {link}",
                    )

    def test_sdk_symbol_links_use_website_pages_and_preserve_code_examples(self):
        probe = self.page("schema/v1/probe/index.html")
        self.assertIn("../alertpolicy/", probe.sections["Probe"]["links"])
        links = probe.sections["mode"]["links"]
        self.assertIn("../../v2alpha/slo/", links)
        self.assertIn("../#metadata", links)
        self.assertIn("../slo/#spec-objectives-items-op", links)
        self.assertIn("https://pkg.go.dev/time#Duration", links)
        self.assertIn(f"{SDK_DOCS}/v1#Unknown", links)
        self.assertIn(SYMBOL_EXAMPLE + "\n", probe.code_blocks)
        for version in ("v1alpha", "v1", "v2alpha"):
            with self.subTest(version=version):
                service = self.page(f"schema/{version}/service/index.html")
                self.assertIn("../#objects", service.sections["kind"]["links"])
        overview = self.page("schema/v1/index.html")
        self.assertIn("alertpolicy/", overview.sections["metadata"]["links"])
        condition = self.page("schema/v2alpha/alertcondition/index.html")
        self.assertIn(
            "../alertpolicy/#spec-alertwhenbreaching",
            condition.sections["AlertCondition"]["links"],
        )

    def test_conditional_requiredness_tables_and_literals(self):
        page = self.page("schema/v1/alertcondition/index.html")
        self.assertEqual(
            normalize("".join(page.sections["spec.condition.op"]["summary"])),
            "string conditionally required",
        )
        self.assertEqual(
            normalize("".join(page.sections["spec.severity"]["summary"])),
            "string required",
        )
        self.assertEqual(
            normalize(
                "".join(
                    self.page("schema/v1/index.html").sections["metadata.labels.*"][
                        "summary"
                    ]
                )
            ),
            "[]string",
        )
        probe = self.page("schema/v1/probe/index.html")
        self.assertIn("Object validation", probe.sections)
        self.assertEqual(probe.tags["table"], 2)
        self.assertEqual(probe.tags["td"], 9)
        self.assertEqual(probe.sections["mode"]["tables"], 1)
        self.assertIn(MULTILINE_EXAMPLE + "\n", probe.code_blocks)
        overview = self.page("schema/v1/index.html")
        self.assertIn("metadata-labels-keys", overview.ids)
        self.assertIn("metadata-labels-values", overview.ids)
        self.assertIn("metadata-labels-values-items", overview.ids)
        mode = normalize("".join(probe.sections["mode"]["text"]))
        self.assertIn("enabled is true and count > 0", mode)
        self.assertIn("<script>alert(1)</script>", mode)
        self.assertIn("https://example.com/rules?a=1&b=2", probe.links)
        html = (self.site / "schema/v1/probe/index.html").read_text()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("<img src=x onerror=alert(1)>", html)
        self.assertNotIn("&lt;td&gt;", html)
        self.assertNotIn("WARNING -  Doc file 'schema/", self.build_log)

    def test_metadata_is_defined_only_in_version_overviews(self):
        for version, objects in self.api.items():
            slug = version.rsplit("/", 1)[1]
            overview = self.page(f"schema/{slug}/index.html")
            self.assertIn("metadata.name", overview.sections)
            for kind, schema in objects.items():
                with self.subTest(version=version, kind=kind):
                    page = self.page(f"schema/{slug}/{kind.lower()}/index.html")
                    self.assertFalse(any("metadata." in name for name in page.sections))
                    for prop in schema["properties"]:
                        path = prop["path"][2:]
                        if (
                            prop["typeInfo"]["name"] != "Metadata"
                            or path not in page.sections
                        ):
                            continue
                        section = page.sections[path]
                        self.assertIn("../#metadata", section["links"])
                        self.assertIn(
                            "reference", normalize("".join(section["summary"]))
                        )
                        self.assertNotIn(
                            prose_text(prop["typeDoc"]),
                            normalize("".join(section["text"])),
                        )

    def test_inline_objects_reference_their_canonical_definitions(self):
        for version, field in (("v1", "indicator"), ("v2alpha", "sli")):
            slo = self.page(f"schema/{version}/slo/index.html")
            for path in (f"spec.{field}", f"spec.objectives[*].{field}"):
                self.assertIn("../sli/#properties", slo.sections[path]["links"])
                self.assertFalse(
                    any(name.startswith(path + ".") for name in slo.sections)
                )
                self.assertIn(
                    "inline form omits", normalize("".join(slo.sections[path]["text"]))
                )
                self.assertIn(path + "Ref", slo.sections)
            self.assertIn("spec.alertPolicies[*].alertPolicyRef", slo.sections)
            self.assertIn(
                "../alertpolicy/#spec",
                slo.sections["spec.alertPolicies[*].spec"]["links"],
            )
            policy = self.page(f"schema/{version}/alertpolicy/index.html")
            self.assertIn("spec.conditions[*].conditionRef", policy.sections)
            self.assertIn(
                "../alertcondition/#spec",
                policy.sections["spec.conditions[*].spec"]["links"],
            )
            self.assertNotIn("spec.conditions[*].spec.severity", policy.sections)
            self.assertIn("spec.notificationTargets[*].targetRef", policy.sections)
            self.assertIn(
                "../alertnotificationtarget/#spec",
                policy.sections["spec.notificationTargets[*].spec"]["links"],
            )
            self.assertNotIn(
                "reference", normalize("".join(policy.sections["spec"]["summary"]))
            )
            sli = self.page(f"schema/{version}/sli/index.html")
            self.assertIn("spec.ratioMetric", sli.sections)
        sli = self.page("schema/v2alpha/sli/index.html")
        self.assertIn(
            "../datasource/#spec",
            sli.sections["spec.thresholdMetric.dataSourceSpec"]["links"],
        )
        self.assertNotIn("spec.thresholdMetric.dataSourceSpec.type", sli.sections)
        self.assertIn(
            "spec.type", self.page("schema/v2alpha/datasource/index.html").sections
        )

    def test_reference_details_and_collection_boundaries_are_preserved(self):
        slo = self.page("schema/v1/slo/index.html")
        properties = self.api["openslo/v1"]["SLO"]["properties"]
        for path in ("$.spec.indicator", "$.spec.objectives[*].indicator"):
            prop = next(prop for prop in properties if prop["path"] == path)
            text = normalize("".join(slo.sections[path[2:]]["text"]))
            self.assertIn(prose_text(prop["fieldDoc"]), text)
            text = text.replace("'", "")
            for rule in prop["rules"]:
                self.assertIn(rule["description"].replace("'", ""), text)
                for condition in rule.get("conditions", []):
                    self.assertIn(condition.replace("'", ""), text)
        probe = self.page("schema/v1/probe/index.html")
        self.assertIn("../service/#properties", probe.sections["items"]["links"])
        self.assertNotIn("items[*]", probe.sections)
        self.assertIn("itemsRef", probe.sections)

    def test_repeated_render_preserves_rules_and_links(self):
        original = self.page("schema/v1/service/index.html")
        repeated = self.page("schema/v1/repeated/index.html")
        for kind, page in (("service", original), ("repeated", repeated)):
            for section in page.sections.values():
                section["links"] = [
                    link
                    if link.startswith("#")
                    else urljoin(f"/schema/v1/{kind}/", link)
                    for link in section["links"]
                ]
        self.assertEqual(original.sections, repeated.sections)


class SchemaFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="openslo-schema-failure-")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        copy_project(self.project)

    def test_unknown_object_stops_the_build(self):
        (self.project / "docs/schema/v1/service.md").write_text(
            '{{ generate_object_properties("openslo/v1", "Missing") }}'
        )
        result = run_command(self.project, "-m", "mkdocs", "build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown schema object: openslo/v1/Missing", result.stderr)

    def test_invalid_manifest_stops_the_build(self):
        (self.project / "api.json").write_text("{}")
        result = run_command(self.project, "-m", "mkdocs", "build")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("The schema manifest contains no versions", result.stderr)

    def test_import_validates_before_replacing_the_manifest(self):
        destination = self.project / "api.json"
        previous = destination.read_bytes()
        source = self.project / "manifest.json"
        source.write_text("{}")
        result = run_command(self.project, "schema.py", str(source))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("The schema manifest contains no versions", result.stderr)
        self.assertEqual(destination.read_bytes(), previous)
        source.write_bytes(previous + b"\n")
        result = run_command(self.project, "schema.py", str(source))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(destination.read_bytes(), source.read_bytes())
