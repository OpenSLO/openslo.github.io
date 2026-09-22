from mkdocs.structure.files import File

from schema import SchemaDocumentation, SchemaLinksExtension


def define_env(env):
    schema = SchemaDocumentation()
    env.macro(schema.object_description, "generate_object_description")
    env.macro(schema.object_properties, "generate_object_properties")
    env.macro(schema.version_overview, "generate_version_overview")
    env.macro(schema.version_links, "generate_version_links")


def on_files(files, config):
    schema = SchemaDocumentation()
    config.markdown_extensions = [
        extension
        for extension in config.markdown_extensions
        if not isinstance(extension, SchemaLinksExtension)
    ] + [SchemaLinksExtension(schema)]
    navigation = ["schema.md"]
    for version, objects in schema.api.items():
        slug = schema.version_slug(version)
        overview = f"schema/{slug}.md"
        if files.get_file_from_path(overview) is None:
            files.append(
                File.generated(
                    config,
                    overview,
                    content=f'{{{{ generate_version_overview("{version}") }}}}\n',
                )
            )
        object_navigation = [{"Overview": overview}]
        for kind in objects:
            path = f"schema/{slug}/{kind.lower()}.md"
            if files.get_file_from_path(path) is None:
                files.append(
                    File.generated(
                        config,
                        path,
                        content=(
                            f"# {kind}\n\n"
                            f'{{{{ generate_object_description("{version}", "{kind}") }}}}\n\n'
                            "## Properties\n\n"
                            f'{{{{ generate_object_properties("{version}", "{kind}") }}}}\n'
                        ),
                    )
                )
            object_navigation.append({kind: path})
        navigation.append({slug: object_navigation})

    for section in config.nav:
        if isinstance(section, dict) and "Schema" in section:
            section["Schema"] = navigation
            break
    else:
        raise ValueError("The MkDocs navigation must contain a Schema section")
    return files


def on_page_markdown(markdown, page, config, files):
    for extension in config.markdown_extensions:
        if isinstance(extension, SchemaLinksExtension):
            extension.source_path = page.file.src_uri
