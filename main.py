"""
MkDocs Macros for generating OpenSLO API documentation from api.json
"""

import json
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


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
            for alt_path in [Path(__file__).parent.parent / "api.json", Path("api.json")]:
                if alt_path.exists():
                    api_file = alt_path
                    break
        
        with open(api_file, 'r') as f:
            json_data = json.load(f)
            for version, objects in json_data.items():
                for object_kind, object_docs in objects.items():
                    json_data[version][object_kind] = ObjectSchema.model_validate(object_docs)
            
            # Cache the result
            _api_schema_cache = json_data
            return _api_schema_cache
    
    def get_template():
        """Get the cached Jinja2 template"""
        nonlocal _template_cache
        
        # Return cached version if available
        if _template_cache is not None:
            return _template_cache
        
        # Set up Jinja2 environment and cache the template
        template_dir = Path(__file__).parent / "templates"
        jinja_env = Environment(loader=FileSystemLoader(template_dir))
        _template_cache = jinja_env.get_template("properties.md.j2")
        return _template_cache
    
    def format_type_info(type_info):
        """Format type information for display"""
        if type_info.get("kind") == "string":
            return "`string`"
        elif type_info.get("kind") == "map":
            return f"`map[string][]string`" if "Label" in type_info.get("name", "") else "`map[string]string`"
        elif type_info.get("kind") == "slice":
            return "`[]string`"
        elif type_info.get("kind") == "struct":
            return f"`{type_info.get('name', 'object')}`"
        else:
            return f"`{type_info.get('name', 'unknown')}`"
    
    def process_property_rules(property_data):
        """Process validation rules for a property from the API schema"""
        property_rules = property_data.get("rules", [])
        
        if not property_rules:
            return ""
        
        # Create table format for all rules
        table_rows = []
        table_rows.append("| Rules | Details | Examples |")
        table_rows.append("| ----- | ------- | -------- |")
        
        for rule in property_rules:
            description = rule.get("description", "")
            details = rule.get("details", "")
            examples = rule.get("examples", [])
            
            if description:
                # Escape regex patterns for markdown
                escaped_description = description.replace("'", "`").replace("^", "\\^").replace("$", "\\$")
                
                # Format details
                details_cell = details if details else ""
                
                # Format examples
                examples_cell = ""
                if examples:
                    examples_cell = "<br>".join(examples)
                
                table_rows.append(f"| {escaped_description} | {details_cell} | {examples_cell} |")
        
        return "\n".join(table_rows)
    
    def process_property_examples(property_data):
        """Get examples for specific properties"""
        path = property_data["path"]
        
        # Check if examples are already in rules
        property_rules = property_data.get("rules", [])
        if property_rules:  # Only iterate if rules exist
            for rule in property_rules:
                if rule.get("examples"):
                    return None  # Examples handled in rules
        
        # Special case examples that aren't in rules
        if path == "$.metadata.annotations":
            return """```yaml
annotations:
  openslo.com/service-folder: ./my/directory
```"""
        
        return None
    
    def transform_properties_for_template(properties):
        """Transform raw property data into template-friendly format"""
        template_properties = []
        seen_names = set()
        
        for prop in properties:
            path = prop["path"]
            
            # Skip root path, internal paths, and wildcard paths
            if (path == "$" or 
                path.endswith(".~") or 
                "[*]" in path or
                ("*" in path and not path.endswith("*"))):
                continue
            
            # Generate clean property name
            name = path.replace("$.", "").replace("$", "root")
            name = name.replace(".*", "").replace("*", "")
            
            if not name or name in seen_names:
                continue
                
            seen_names.add(name)
            
            # Only include properties that have actual content (not just structural)
            type_info = prop["typeInfo"]
            if type_info.get("kind") == "struct" and not prop.get("typeDoc") and not prop.get("rules"):
                # This is likely a structural property (like metadata, spec) - include it but without type display
                template_properties.append({
                    "name": name,
                    "type_display": "",
                    "is_optional": False,
                    "description": prop.get("typeDoc", ""),
                    "rules_table": "",
                    "examples": None
                })
            else:
                # This is a concrete property with actual type information
                template_properties.append({
                    "name": name,
                    "type_display": format_type_info(type_info),
                    "is_optional": prop.get("isOptional", False),
                    "description": prop.get("typeDoc", ""),
                    "rules_table": process_property_rules(prop),
                    "examples": process_property_examples(prop)
                })
        
        return template_properties
    
    @env.macro
    def generate_object_properties(version: str, object_name: str):
        """Generate the Properties section for Service API documentation"""
        try:
            api_docs = load_api_schema()
            
            # Now we have type-safe access
            object_schema = api_docs.get(version, {}).get(object_name, None)
            
            if object_schema is None:
                return f"<!-- Error: Could not find {object_name} in version {version} -->"
            
            properties = object_schema.properties
            
            # Transform properties for template - now with full type safety
            template_properties = transform_properties_for_template([prop.model_dump() for prop in properties])
            
            # Get cached template
            template = get_template()
            
            # Render template
            return template.render(properties=template_properties)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"<!-- Error generating properties: {str(e)} -->"
