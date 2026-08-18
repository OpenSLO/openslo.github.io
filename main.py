"""
MkDocs Macros for generating OpenSLO API documentation from api.json
"""

import json
from pathlib import Path
import re
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from typing import List, Optional


class Rule(BaseModel):
    description: str
    errorCode: str
    details: Optional[str] = None
    examples: Optional[List[str]] = None


class TypeInfo(BaseModel):
    name: str
    kind: str
    package: Optional[str] = None


class Property(BaseModel):
    path: str
    typeInfo: TypeInfo
    rules: Optional[List[Rule]] = None
    typeDoc: Optional[str] = None
    isOptional: Optional[bool] = None
    required: Optional[bool] = None
    childrenPaths: Optional[List[str]] = None
    linkTo: Optional[str] = None


class ObjectSchema(BaseModel):
    properties: List[Property]


VersionDocs = dict[str, ObjectSchema]
APIDocs = dict[str, dict[str, VersionDocs]]


def define_env(env):
    """
    Define macros for MkDocs
    """

    # Cache for loaded data to avoid repeated loading
    _api_schema_cache = None
    _template_cache = None
    _property_links_cache = None

    def load_api_schema() -> APIDocs:
        """Load the api.json schema file"""
        nonlocal _api_schema_cache

        # Return cached version if available
        if _api_schema_cache is not None:
            return _api_schema_cache

        api_file = Path(__file__).parent / "api.json"
        if not api_file.exists():
            # Try alternative paths
            for alt_path in [
                Path(__file__).parent.parent / "api.json",
                Path("api.json"),
            ]:
                if alt_path.exists():
                    api_file = alt_path
                    break

        with open(api_file, "r") as f:
            json_data = json.load(f)
            for version, objects in json_data.items():
                for object_kind, object_docs in objects.items():
                    json_data[version][object_kind] = ObjectSchema.model_validate(
                        object_docs
                    )

            # Cache the result.
            _api_schema_cache = json_data
            return _api_schema_cache

    def get_template():
        """Get the cached Jinja2 template"""
        nonlocal _template_cache

        # Return cached version if available.
        if _template_cache is not None:
            return _template_cache

        # Set up Jinja2 environment and cache the template.
        template_dir = Path(__file__).parent / "templates"
        jinja_env = Environment(loader=FileSystemLoader(template_dir))
        _template_cache = jinja_env.get_template("properties.md.j2")
        return _template_cache

    def load_property_links() -> dict:
        """Load the property-links.json configuration"""
        nonlocal _property_links_cache

        # Return cached version if available
        if _property_links_cache is not None:
            return _property_links_cache

        links_file = Path(__file__).parent / "property-links.json"
        if not links_file.exists():
            _property_links_cache = {}
            return _property_links_cache

        with open(links_file, "r") as f:
            _property_links_cache = json.load(f)
            return _property_links_cache

    def should_link_property(
        version: str, object_name: str, property_path: str, links_config: dict
    ) -> Optional[dict]:
        """
        Check if a property should be linked instead of expanded.
        Returns the link config object (with 'link' and 'template' keys) if found, None otherwise.
        """
        version_config = links_config.get(version, {})

        # Check object-specific configuration first
        object_config = version_config.get(object_name, {})
        if property_path in object_config:
            return object_config[property_path]

        # Check common configuration
        common_config = version_config.get("_common", {})
        if property_path in common_config:
            return common_config[property_path]

        return None

    def filter_linked_properties(
        properties: List[Property], version: str, object_name: str, links_config: dict
    ):
        """
        Filter properties based on link configuration.
        For linked properties, replaces their typeDoc with a reference link and removes children.
        Returns modified properties list.
        """
        from jinja2 import Template

        properties_to_render = []
        paths_to_skip = set()

        # First pass: identify all linked properties and mark all their descendants to skip
        for prop in properties:
            link_config = should_link_property(version, object_name, prop.path, links_config)
            if link_config:
                # Mark all descendants to skip (any property that starts with this path + ".")
                for other_prop in properties:
                    if other_prop.path.startswith(prop.path + "."):
                        paths_to_skip.add(other_prop.path)

        # Second pass: build the output, modifying linked properties
        for prop in properties:
            # Skip children of linked properties
            if prop.path in paths_to_skip:
                continue

            # Check if this property should be linked
            link_config = should_link_property(version, object_name, prop.path, links_config)

            if link_config:
                # Determine required status
                is_required = False
                if hasattr(prop, "required"):
                    is_required = prop.required
                elif prop.rules:
                    is_required = any(rule.errorCode == "required" for rule in prop.rules)

                # Render the template with property context AND link
                template = Template(link_config['template'])
                rendered = template.render(
                    path=prop.path,
                    typeInfo=prop.typeInfo,
                    required=is_required,
                    link=link_config['link']  # Make link available in template
                )

                # Store the link URL for use in the header
                if link_config['link']:
                    prop.linkTo = link_config['link']

                # Append the link to existing typeDoc (if any)
                if prop.typeDoc:
                    prop.typeDoc = f"{prop.typeDoc}\n\n{rendered}"
                else:
                    prop.typeDoc = rendered

                # Keep validation rules intact (they will be rendered by the template)
                # Keep the property in the list
                properties_to_render.append(prop)
            else:
                # Regular property, include as-is
                properties_to_render.append(prop)

        return properties_to_render

    def process_property_rules(rules: Optional[List[Rule]]) -> Optional[List[Rule]]:
        """Process validation rules for a property from the API schema"""

        def process_string(s: str) -> str:
            """Process a string to escape regex patterns and convert URLs"""
            # Replace single-quoted content with HTML code tags using regex.
            # This handles patterns like 'value' -> <code>value</code>.
            s = re.sub(r"'([^']*)'", r"<code>\1</code>", s)
            # Convert URLs to HTML links.
            # This handles patterns like http://example.com -> <a href="http://example.com">http://example.com</a>.
            s = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', s)
            # Escape square brackets to prevent markdown link interpretation.
            s = s.replace("[", "&#91;").replace("]", "&#93;")
            # Escape regex patterns for markdown.
            return s.replace("^", "\\^").replace("$", "\\$")

        if not rules:
            return rules

        for rule in rules:
            rule.description = (
                process_string(rule.description) if rule.description else None
            )
            rule.details = process_string(rule.details) if rule.details else None

        return rules

    def transform_properties_for_template(properties: List[Property]):
        """Transform raw property data into template-friendly format"""

        filtered_properties = []
        key_properties = set()
        for prop in properties:
            if prop.path == "$":
                continue
            if prop.path.endswith(".~"):
                key_properties.add(prop.path[:-2])
            prop.path = prop.path.replace("$.", "")

            # Extract required status and filter out required/optional rules
            if prop.rules:
                prop.required = any(rule.errorCode == "required" for rule in prop.rules)
                prop.rules = [
                    rule
                    for rule in prop.rules
                    if rule.errorCode not in ["required", "optional"]
                ]
            else:
                prop.required = False

            prop.rules = process_property_rules(prop.rules)
            filtered_properties.append(prop)

        return filtered_properties

    @env.macro
    def generate_object_properties(version: str, object_name: str):
        """Generate the Properties section for Service API documentation"""

        try:
            api_docs = load_api_schema()
            links_config = load_property_links()

            object_schema = api_docs.get(version, {}).get(object_name, None)

            if object_schema is None:
                return (
                    f"<!-- Error: Could not find {object_name} in version {version} -->"
                )

            properties = object_schema.properties
            properties = transform_properties_for_template(properties)

            # Filter properties based on link configuration
            properties_to_render = filter_linked_properties(
                properties, version, object_name, links_config
            )

            template = get_template()
            return template.render(properties=properties_to_render)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return f"<!-- Error generating properties: {str(e)} -->"
