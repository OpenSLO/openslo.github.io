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
    childrenPaths: Optional[List[str]] = None


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

    def process_property_rules(rules: Optional[List[Rule]]) -> Optional[List[Rule]]:
        """Process validation rules for a property from the API schema"""

        if not rules:
            return rules

        for rule in rules:
            if rule.description:
                # Replace single-quoted content with HTML code tags using regex.
                # This handles patterns like 'value' -> <code>value</code>.
                rule.description = re.sub(r"'([^']*)'", r"<code>\1</code>", rule.description)
                
                # Escape regex patterns for markdown.
                rule.description = (
                    rule.description.replace("^", "\\^")
                    .replace("$", "\\$")
                )

        return rules

    def transform_properties_for_template(properties: List[Property]):
        """Transform raw property data into template-friendly format"""

        filtered_properties = []
        for prop in properties:
            if prop.path == "$":
                continue
            prop.path = prop.path.replace("$.", "").replace("*", "\\*")
            prop.rules = process_property_rules(prop.rules)
            filtered_properties.append(prop)

        return filtered_properties

    @env.macro
    def generate_object_properties(version: str, object_name: str):
        """Generate the Properties section for Service API documentation"""

        try:
            api_docs = load_api_schema()

            object_schema = api_docs.get(version, {}).get(object_name, None)

            if object_schema is None:
                return (
                    f"<!-- Error: Could not find {object_name} in version {version} -->"
                )

            properties = object_schema.properties
            properties = transform_properties_for_template(properties)
            template = get_template()
            return template.render(properties=properties)

        except Exception as e:
            import traceback

            traceback.print_exc()
            return f"<!-- Error generating properties: {str(e)} -->"
