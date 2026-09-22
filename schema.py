import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape
from pydantic import BaseModel, Field, TypeAdapter


ROOT = Path(__file__).resolve().parent


class Rule(BaseModel):
    description: str
    errorCode: str = ""
    details: str = ""
    examples: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)


class TypeInfo(BaseModel):
    name: str
    kind: str
    package: str = ""


class Property(BaseModel):
    path: str
    typeInfo: TypeInfo
    rules: list[Rule] = Field(default_factory=list)
    typeDoc: str = ""
    fieldDoc: str = ""
    deprecatedDoc: str = ""
    examples: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    childrenPaths: list[str] = Field(default_factory=list)
    isHidden: bool = False

    @property
    def display_path(self):
        return self.path.removeprefix("$.")

    @property
    def anchor(self):
        # Keep map keys, map values, and array elements distinct in fragment links.
        path = self.display_path.replace(".*~", "-keys").replace(".*", "-values")
        path = path.replace("[*]", "-items")
        return path.replace(".", "-").lower()

    @property
    def required(self):
        return any(
            rule.errorCode == "required" and not rule.conditions for rule in self.rules
        )

    @property
    def conditionally_required(self):
        return not self.required and any(
            rule.errorCode == "required" for rule in self.rules
        )


class ObjectSchema(BaseModel):
    name: str
    properties: list[Property]
    doc: str = ""


APIDocs = dict[str, dict[str, ObjectSchema]]


def load_api(path: Path) -> APIDocs:
    api = TypeAdapter(APIDocs).validate_json(path.read_text(encoding="utf-8"))
    if not api:
        raise ValueError("The schema manifest contains no versions")
    slugs = set()
    for version, objects in api.items():
        slug = SchemaDocumentation.version_slug(version)
        if slug in slugs:
            raise ValueError(f"Duplicate schema version path: {slug}")
        slugs.add(slug)
        if not objects:
            raise ValueError(f"The schema manifest contains no objects for {version}")
        for kind, schema in objects.items():
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", kind):
                raise ValueError(f"Invalid schema object kind: {kind}")
            paths = [prop.path for prop in schema.properties]
            if paths.count("$") != 1 or len(paths) != len(set(paths)):
                raise ValueError(
                    f"Invalid or duplicate property paths for {version}/{kind}"
                )
    return dict(
        sorted(api.items(), key=lambda item: SchemaDocumentation.version_slug(item[0]))
    )


def rule_text(value: str) -> Markup:
    """Escape rule text while retaining quoted literals and HTTP links."""
    pattern = r"(?<!\w)'([^'\n]+)'(?!\w)|(https?://[^\s<>]+)"
    parts = []
    offset = 0
    for match in re.finditer(pattern, value):
        parts.append(escape(value[offset : match.start()]))
        if match.group(1) is not None:
            parts.append(Markup("<code>{}</code>").format(match.group(1)))
        else:
            url = match.group(2).rstrip(".,)")
            parts.append(Markup('<a href="{}">{}</a>').format(url, url))
            parts.append(escape(match.group(2)[len(url) :]))
        offset = match.end()
    parts.append(escape(value[offset:]))
    return Markup("").join(parts)


def table_cell(value: str) -> Markup:
    # Markdown still parses punctuation inside inline HTML code elements.
    entities = {ord(char): f"&#{ord(char)};" for char in "\\*_[]`|"}
    return Markup(str(escape(value)).translate(entities).replace("\n", "<br>"))


def code_block(value: str) -> str:
    fence = "`" * max(
        3, max((len(run) for run in re.findall(r"`+", value)), default=0) + 1
    )
    return f"{fence}text\n{value}\n{fence}"


class SchemaDocumentation:
    def __init__(self, api_path: Path = ROOT / "api.json"):
        self.api = load_api(api_path)
        self.links = json.loads(
            (ROOT / "property-links.json").read_text(encoding="utf-8")
        )
        self.templates = Environment(
            loader=FileSystemLoader(ROOT / "templates"),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.templates.filters["rule_text"] = rule_text
        self.templates.filters["table_cell"] = table_cell
        self.templates.filters["code_block"] = code_block

    @staticmethod
    def version_slug(version: str):
        if not re.fullmatch(r"openslo(?:\.com)?/v\d+(?:(?:alpha|beta)\d*)?", version):
            raise ValueError(f"Invalid schema API version: {version}")
        return version.rsplit("/", 1)[1]

    def object_schema(self, version: str, kind: str) -> ObjectSchema:
        try:
            return self.api[version][kind]
        except KeyError as error:
            raise ValueError(f"Unknown schema object: {version}/{kind}") from error

    def object_description(self, version: str, kind: str):
        schema = self.object_schema(version, kind)
        root = next(prop for prop in schema.properties if prop.path == "$")
        return root.typeDoc or schema.doc

    def render_properties(self, properties, links=None):
        return self.templates.get_template("properties.md.j2").render(
            properties=properties, links=links or {}
        )

    def object_properties(self, version: str, kind: str):
        schema = self.object_schema(version, kind)
        version_links = self.links.get(version, {})
        path_links = {**version_links.get("_common", {}), **version_links.get(kind, {})}
        type_links = version_links.get("_types", {})
        rendered_links = {}
        for prop in schema.properties:
            link = path_links.get(prop.display_path, type_links.get(prop.typeInfo.name))
            if not link:
                continue
            target = urlsplit(link["link"])
            # Expand the canonical definition on its own page.
            if target.path == f"{kind.lower()}.md" and target.fragment == prop.anchor:
                continue
            rendered_links[prop.path] = {
                "url": link["link"],
                "description": self.templates.from_string(link["template"]).render(
                    path=prop.display_path,
                    typeInfo=prop.typeInfo,
                    required=prop.required,
                    link=link["link"],
                ),
            }
        properties = [
            prop
            for prop in schema.properties
            if not any(
                prop.path.startswith(path + ".") or prop.path.startswith(path + "[")
                for path in rendered_links
            )
        ]
        return self.render_properties(properties, rendered_links)

    def metadata_properties(self, version: str):
        objects = self.api[version]
        schema = objects.get("Service", next(iter(objects.values())))
        properties = [
            prop
            for prop in schema.properties
            if prop.path == "$.metadata" or prop.path.startswith("$.metadata.")
        ]
        if not properties:
            raise ValueError(f"No metadata properties found for {version}")
        return self.render_properties(properties)

    def version_overview(self, version: str):
        return self.templates.get_template("version.md.j2").render(
            version=version,
            slug=self.version_slug(version),
            objects=self.api[version],
            metadata=self.metadata_properties(version),
        )

    def version_links(self):
        return "\n".join(
            f"- [`{version}`](schema/{self.version_slug(version)}.md)"
            for version in self.api
        )


def main():
    parser = argparse.ArgumentParser(description="Import an SDK schema manifest.")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    load_api(args.manifest)
    (ROOT / "api.json").write_bytes(args.manifest.read_bytes())


if __name__ == "__main__":
    main()
