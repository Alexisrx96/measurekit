import configparser
import pathlib
import pprint
import sys

# Ensure we can import measurekit from the project root
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))


def compile_units(config_path, output_dir):
    conf_path = pathlib.Path(config_path)
    out_path = pathlib.Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Reading configuration from: {conf_path}")
    parser = configparser.ConfigParser()
    parser.optionxform = str  # Preserve case sensitivity
    try:
        parser.read(str(conf_path), encoding="utf-8")
    except Exception as e:
        print(f"Failed to read config file: {e}")
        sys.exit(1)

    index_map = {}  # unit_name -> scope_name

    # 1. Parse Prefixes
    prefixes = {}
    if "Prefixes" in parser:
        for name, value in parser["Prefixes"].items():
            # Format: quetta = Q, 1e30
            parts = [p.strip() for p in value.split(",")]
            symbol = parts[0]
            prefixes[name] = symbol

    # 2. Parse Units and Expand Prefixes
    # We will put all units from measurekit.conf into a 'core' scope
    scope_name = "core"

    unit_definitions = []

    if "Units" in parser:
        print("Processing [Units] section...")
        for key, value_str in parser["Units"].items():
            # Parse line: meter = 1.0, L, [m, meter, metro, metros]
            # or: inch = 0.0254, L, noprefix, [in, inch]

            # Remove inline comments from value_str for safety, though [ ] handling below does it too
            # Be careful not to remove # if it's part of a string but here it's config.

            aliases = []
            main_part = value_str
            if "[" in value_str:
                main_part, alias_block = value_str.split("[", 1)
                # Parse up to the closing bracket
                if "]" in alias_block:
                    alias_content = alias_block.split("]")[0]
                    aliases = [a.strip() for a in alias_content.split(",")]
                else:
                    # Malformed? Fallback
                    aliases = [a.strip() for a in alias_block.split(",")]
            else:
                main_part = main_part.split("#")[
                    0
                ]  # Strip comment if no [ ] block

            # Parse attributes
            attrs = [p.strip() for p in main_part.split(",") if p.strip()]

            # Check for 'noprefix' flag
            allow_prefixes = True
            if "noprefix" in attrs:
                allow_prefixes = False

            # The key is usually the primary name, but aliases[0] is often the symbol
            # We want to register all names: key and aliases
            all_names = sorted(list(set([key] + aliases)))

            import keyword

            for name in all_names:
                # Python variable names must be valid identifiers.
                # Skip things like ' (arcminute) or " (arcsecond) or numbers if they start with digit
                if not name.isidentifier():
                    continue

                # Also skip Python keywords like 'in', 'as', etc.
                if keyword.iskeyword(name):
                    print(f"Skipping keyword alias: {name}")
                    continue

                unit_definitions.append(name)
                index_map[name] = scope_name

                # Generate prefixed versions if allowed
                # But only if it's not blocked (noprefix)
                # Also skip if it seems to be an alias that shouldn't have prefixes?
                # MeasureKit logic applies prefixes to all aliases usually unless restricted.
                if allow_prefixes:
                    # Skip if this unit name is in prefixes blocklist? (Not implemented here, but simplistic check)
                    # Also skip if it seems to be an alias that shouldn't have prefixes?
                    # MeasureKit logic applies prefixes to all aliases usually unless restricted.

                    for prefix_name in prefixes:
                        prefixed_name = prefix_name + name
                        unit_definitions.append(prefixed_name)
                        index_map[prefixed_name] = scope_name

    # 3. Generate Core Module
    lines = [
        "# GENERATED CODE - DO NOT EDIT",
        "from measurekit.domain.measurement.units import CompoundUnit",
        "",
        "# This module defines the static unit objects for the 'core' scope.",
        "# These are simple CompoundUnit wrappers. The UnitSystem handles the physics.",
        "",
    ]

    # De-duplicate names
    unique_units = sorted(list(set(unit_definitions)))

    for unit_name in unique_units:
        # We generate: meter = CompoundUnit({'meter': 1})
        # This assumes the unit name used in the CompoundUnit matches the key in the UnitSystem
        # which it should.
        lines.append(f'{unit_name} = CompoundUnit({{"{unit_name}": 1}})')

    lines.append("")

    scope_file = out_path / f"{scope_name}.py"
    with open(scope_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {scope_file} with {len(unique_units)} units.")

    # 4. Write Index File
    index_lines = [
        "# GENERATED CODE - DO NOT EDIT",
        f"UNIT_INDEX = {pprint.pformat(index_map)}",
        "",
    ]
    index_file = out_path / "_index.py"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    # 5. Generate __init__.py with Lazy Loading
    init_file = out_path / "__init__.py"

    init_content = [
        '"""Lazy-loading unit package."""',
        "from __future__ import annotations",
        "import typing",
        "",
        "if typing.TYPE_CHECKING:",
        "    from measurekit.domain.measurement.units import CompoundUnit",
        "",
        "try:",
        "    from ._index import UNIT_INDEX",
        "except ImportError:",
        "    UNIT_INDEX = {}",
        "",
        "def __getattr__(name: str) -> CompoundUnit:",
        "    if name in UNIT_INDEX:",
        "        scope = UNIT_INDEX[name]",
        '        module = __import__(f"measurekit.units.{scope}", fromlist=[name])',
        "        return getattr(module, name)",
        '    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")',
        "",
        "def __dir__() -> list[str]:",
        "    return sorted(list(globals().keys()) + list(UNIT_INDEX.keys()))",
        "",
    ]

    with open(init_file, "w", encoding="utf-8") as f:
        f.write("\n".join(init_content))

    print("Compilation complete.")


if __name__ == "__main__":
    # Point to the measurekit.conf file
    # We assume CWD is project root d:\measurekit
    conf_file = "measurekit/infrastructure/config/measurekit.conf"
    compile_units(conf_file, "measurekit/units")
