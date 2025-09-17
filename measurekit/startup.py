"""startup.py - MeasureKit System Initialization."""

import configparser
import re
from importlib import resources
from pathlib import Path

import measurekit.constants as constants_module
import measurekit.dimensions as dimensions_module
import measurekit.units as units_module
from measurekit.config import config
from measurekit.measurement.api import Q_
from measurekit.measurement.conversions import (
    get_all_prefixes,
    register_prefix,
    register_unit,
)
from measurekit.measurement.dimensions import (
    _PREFIX_BLOCKLIST,
    Dimension,
    block_prefixes_for_dimension_symbol,
    register_dimension,
)
from measurekit.measurement.units import CompoundUnit, get_unit


def initialize_system(verbose: bool = False):
    """
    Initializes the MeasureKit system by loading configurations and registering entities.

    Args:
        verbose (bool): If True, prints detailed information about the
                        initialization process.
    """
    if verbose:
        print("--- MeasureKit System Initializing (Verbose Mode) ---")

    # Clear any previous configuration (useful for reloads or tests)
    config.clear()

    # Load and register all entities from .conf files
    _load_all_configurations(verbose)
    _initialize_prefix_system(verbose)
    _initialize_dimension_system(verbose)
    _initialize_unit_system(verbose)
    _initialize_constant_system(verbose)

    if verbose:
        print("\n--- Initialization Complete ---")


def _load_all_configurations(verbose: bool):
    """
    Reads all configuration files from the library package and the user's
    home directory and merges them into the global `config` object.
    """
    if verbose:
        print("\n--- Phase 1: Loading Configuration Files ---")

    parser = configparser.ConfigParser()
    paths_to_load = []

    # --- Part 1: Find LIBRARY configurations ---
    try:
        lib_config_dir = resources.files("measurekit.config")
        if verbose:
            print(f"Searching for library configurations in: {lib_config_dir}")

        lib_master_conf = lib_config_dir / "measurekit.conf"
        if lib_master_conf.is_file():
            paths_to_load.append(lib_master_conf)

        systems_to_load_by_default = {"international.conf", "imperial.conf"}
        lib_systems_dir = lib_config_dir / "systems"
        if lib_systems_dir.is_dir():
            for system_file in sorted(list(systems_to_load_by_default)):
                if (lib_systems_dir / system_file).is_file():
                    paths_to_load.append(lib_systems_dir / system_file)

    except (ModuleNotFoundError, FileNotFoundError):
        print(
            "[WARNING] Could not locate the built-in library configuration files."
        )

    # --- Part 2: Find USER configurations ---
    user_config_dir = Path.home() / ".config" / "measurekit"
    if verbose:
        print(f"Searching for user configurations in: {user_config_dir}")

    user_master_conf = user_config_dir / "measurekit.conf"
    if user_master_conf.exists():
        if verbose:
            print(f"Found user master config: {user_master_conf}")
        paths_to_load.append(user_master_conf)

    user_systems_dir = user_config_dir / "systems"
    if user_systems_dir.is_dir():
        if verbose:
            print("Found user systems directory. Loading custom systems...")
        for user_system_conf in sorted(user_systems_dir.glob("*.conf")):
            paths_to_load.append(user_system_conf)

    # --- Part 3: Load the discovered files ---
    if not paths_to_load:
        print(
            "\n[WARNING] No configuration files found. The library will have no units defined."
        )
        return

    if verbose:
        print("\nLoading configuration files in order of precedence:")
        for path in paths_to_load:
            print(f"  -> {path}")

    str_paths = [str(p) for p in paths_to_load]
    parser.read(str_paths, encoding="utf-8")

    # Populate the config object
    if "Settings" in parser:
        config.settings.update(parser.items("Settings"))
    if "Prefixes" in parser:
        config.prefix_definitions.update(parser.items("Prefixes"))
    if "Dimensions" in parser:
        config.dimension_definitions.update(parser.items("Dimensions"))
    if "Units" in parser:
        config.unit_definitions.update(parser.items("Units"))
    if "Constants" in parser:
        config.constant_definitions.update(parser.items("Constants"))

    if verbose:
        print("\nConfiguration loading summary:")
        print(
            f"  - Loaded {len(config.prefix_definitions)} prefix definitions."
        )
        print(
            f"  - Loaded {len(config.dimension_definitions)} dimension definitions."
        )
        print(
            f"  - Loaded {len(config.unit_definitions)} base unit definitions."
        )
        print(
            f"  - Loaded {len(config.constant_definitions)} constant definitions."
        )


def _initialize_prefix_system(verbose: bool):
    """Registers the loaded prefixes into the measurement system."""
    if not config.prefix_definitions:
        return
    if verbose:
        print("\n--- Phase 2: Initializing Prefixes ---")

    count = 0
    for name, value_str in config.prefix_definitions.items():
        try:
            symbol, factor_str = [p.strip() for p in value_str.split(",")]
            factor = float(factor_str)
            register_prefix(symbol=symbol, factor=factor, name=name)
            if verbose:
                print(
                    f"  Registered Prefix: {name.capitalize():<10} (Symbol: {symbol:<3}, Factor: {factor})"
                )
            count += 1
        except Exception as e:
            print(f"  [ERROR] Could not load prefix '{name}'. Reason: {e}")

    if verbose:
        print(f"\nSuccessfully registered {count} prefixes.")


def _initialize_dimension_system(verbose: bool):
    """Registers the loaded dimensions into the measurement system."""
    if not config.dimension_definitions:
        return
    if verbose:
        print("\n--- Phase 3: Initializing Dimensions ---")

    base_symbols = []
    for name, value_str in config.dimension_definitions.items():
        parts = [p.strip() for p in value_str.split(",")]
        symbol = parts[0]
        base_symbols.append(symbol)

        if len(parts) > 1 and parts[1] == "noprefix":
            block_prefixes_for_dimension_symbol(symbol)
            if verbose:
                print(
                    f"  -> Prefixes disabled for dimension {name} ({symbol})"
                )

    Dimension.set_base_dimensions(base_symbols)
    if verbose:
        print(f"Set base dimension symbols: {base_symbols}")

    loaded_dimensions = []
    for name, value_str in config.dimension_definitions.items():
        symbol = value_str.split(",")[0].strip()
        dim_instance = Dimension({symbol: 1})
        register_dimension(dim_instance, name.capitalize())
        setattr(dimensions_module, name.upper(), dim_instance)
        loaded_dimensions.append(name.upper())
        if verbose:
            print(
                f"  Registered Dimension: {name.capitalize():<15} -> {dim_instance}"
            )

    if verbose:
        print(
            f"\nSuccessfully registered {len(loaded_dimensions)} dimensions."
        )

    _generate_stub(
        dimensions_module,
        loaded_dimensions,
        "Dimension",
        "from measurekit.measurement.dimensions import Dimension",
        verbose,
    )


def _initialize_unit_system(verbose: bool):
    """Initializes the unit system, registering base units and generating prefixed units."""
    if not config.unit_definitions:
        return
    if verbose:
        print("\n--- Phase 4: Initializing Units ---")

    loaded_units = []
    base_unit_count = 0
    prefixed_unit_count = 0
    prefixes = get_all_prefixes()

    for key, value_str in config.unit_definitions.items():
        try:
            # --- PARSE THE UNIT DEFINITION LINE ---
            aliases = []
            main_part = value_str
            if "[" in value_str:
                main_part, alias_part = value_str.split("[", 1)
                aliases = [
                    a.strip() for a in alias_part.strip()[:-1].split(",")
                ]

            parts = [p.strip() for p in main_part.split(",") if p.strip()]
            factor_str, dim_str = parts[:2]
            recipe_str = parts[2] if len(parts) > 2 else None

            factor = float(factor_str)
            dimension = Dimension.from_string(dim_str)
            recipe = get_unit(recipe_str) if recipe_str else None
            symbol = aliases[0] if aliases else key
            all_aliases = [key] + aliases

            if verbose:
                print(f"\nParsing unit '{key}':")
                print(
                    f"  - Factor: {factor}, Dimension: {dimension}, Aliases: {all_aliases}"
                )

            # --- 1. REGISTER THE BASE UNIT ---
            register_unit(
                symbol, dimension, factor, key, *all_aliases, recipe=recipe
            )
            unit_instance = get_unit(symbol)
            setattr(units_module, key, unit_instance)
            loaded_units.append(key)
            base_unit_count += 1
            if verbose:
                print(f"  + Registered Base Unit: {key} (Symbol: {symbol})")

            # --- 2. GENERATE AND REGISTER PREFIXED UNITS ---
            dim_symbol = next(iter(dimension.exponents), None)
            if dim_symbol in _PREFIX_BLOCKLIST:
                if verbose:
                    print(
                        "  - Prefixes are disabled for this dimension. Skipping generation."
                    )
                continue

            for prefix_symbol, prefix_data in prefixes.items():
                prefix_name = prefix_data["name"]
                prefix_factor = prefix_data["factor"]

                new_unit_key = f"{prefix_name}{key}"
                new_unit_symbol = f"{prefix_symbol}{symbol}"
                new_unit_factor = prefix_factor * factor
                new_recipe = unit_instance
                new_aliases = [f"{prefix_symbol}{alias}" for alias in aliases]
                all_new_aliases = [new_unit_key] + new_aliases

                register_unit(
                    new_unit_symbol,
                    dimension,
                    new_unit_factor,
                    new_unit_key,
                    *all_new_aliases,
                    recipe=new_recipe,
                )

                new_unit_instance = get_unit(new_unit_symbol)
                setattr(units_module, new_unit_key, new_unit_instance)
                loaded_units.append(new_unit_key)
                prefixed_unit_count += 1
                if verbose:
                    print(
                        f"    -> Registered Prefixed Unit: {new_unit_key} (Symbol: {new_unit_symbol})"
                    )

        except Exception as e:
            print(
                f"  [ERROR] Could not load unit '{key}' or its prefixes. Reason: {e}"
            )

    if verbose:
        total = base_unit_count + prefixed_unit_count
        print(
            f"\nSuccessfully registered {base_unit_count} base units and {prefixed_unit_count} prefixed units (Total: {total})."
        )

    _generate_stub(
        units_module,
        loaded_units,
        "CompoundUnit",
        "from measurekit.measurement.units import CompoundUnit",
        verbose,
    )


def _initialize_constant_system(verbose: bool):
    """Registers the loaded constants into the measurement system."""
    if not config.constant_definitions:
        return
    if verbose:
        print("\n--- Phase 5: Initializing Constants ---")

    loaded_constants = []
    for name, value_str in config.constant_definitions.items():
        try:
            match = re.match(r"^\s*([\d\.\-eE]+)\s+(.*)", value_str)
            if not match:
                raise ValueError("Constant must have a value and a unit.")

            value_str_part, unit_str = match.groups()
            value = float(value_str_part)
            unit = (
                get_unit(unit_str.strip())
                if unit_str.strip() != "1"
                else CompoundUnit({})
            )
            constant_quantity = Q_(value, unit)
            if verbose:
                print(f"  Registered Constant: {name} = {constant_quantity}")
            setattr(constants_module, name, constant_quantity)
            loaded_constants.append(name)
        except Exception as e:
            print(f"  [ERROR] Could not load constant '{name}'. Reason: {e}")

    if verbose:
        print(f"\nSuccessfully registered {len(loaded_constants)} constants.")

    _generate_stub(
        constants_module,
        loaded_constants,
        "Quantity",
        "from measurekit.measurement.quantity import Quantity",
        verbose,
    )


def _generate_stub(
    module, names: list[str], class_name: str, import_line: str, verbose: bool
):
    """Generates a .pyi stub file for type hinting and autocompletion."""
    try:
        stub_path = Path(module.__file__).with_suffix(".pyi")
        header = [
            "# This file is autogenerated by MeasureKit. DO NOT EDIT MANUALLY.",
            "",
            import_line,
            "",
        ]
        body = [f"{name}: {class_name}" for name in sorted(names)]
        new_content = "\n".join(header + body) + "\n"

        needs_write = (
            not stub_path.exists()
            or stub_path.read_text(encoding="utf-8") != new_content
        )

        if needs_write:
            if verbose:
                print(f"Updating autocompletion file: {stub_path}")
            stub_path.write_text(new_content, encoding="utf-8")

    except Exception as e:
        print(
            f"[WARNING] Could not write .pyi stub file for {module.__name__}. Reason: {e}"
        )
