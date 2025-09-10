"""startup.py - MeasureKit System Initialization."""

import configparser
import re
from pathlib import Path
from importlib import resources

import measurekit.constants as constants_module
import measurekit.dimensions as dimensions_module
import measurekit.units as units_module
from measurekit.config import config
from measurekit.measurement.api import Q_
from measurekit.measurement.conversions import register_prefix, register_unit
from measurekit.measurement.dimensions import (
    _PREFIX_BLOCKLIST,
    Dimension,
    block_prefixes_for_dimension_symbol,
    register_dimension,
)
from measurekit.measurement.units import CompoundUnit, get_unit


def initialize_system():
    """Inicializa el sistema MeasureKit cargando configuraciones y registrando entidades."""
    print("--- MeasureKit System Initializing ---")

    # Limpia cualquier configuración previa (útil para recargas o pruebas)
    config.clear()

    # Carga y registra todas las entidades desde los archivos .conf
    _load_all_configurations()
    _initialize_prefix_system()
    _initialize_dimension_system()
    _initialize_unit_system()
    _initialize_constant_system()

    print("--- Initialization Complete ---")


def _get_config_paths() -> list[Path]:
    """Construye una lista ordenada de rutas de archivos de configuración para cargar."""
    paths_to_load = []
    # This is the correct way to find the config dir INSIDE the package
    lib_package_dir = Path(__file__).resolve().parent
    lib_config_dir = lib_package_dir / "config"
    user_config_dir = Path.home() / ".config" / "measurekit"

    print(f"Searching for library configurations in: {lib_config_dir}")
    print(f"Searching for user configurations in: {user_config_dir}")

    lib_master_conf = lib_config_dir / "measurekit.conf"
    if lib_master_conf.exists():
        paths_to_load.append(lib_master_conf)

    user_master_conf = user_config_dir / "measurekit.conf"
    if user_master_conf.exists():
        print(f"Found user master config: {user_master_conf}")
        paths_to_load.append(user_master_conf)

    systems_to_load_by_default = {"international.conf", "imperial.conf"}
    lib_systems_dir = lib_config_dir / "systems"
    if lib_systems_dir.is_dir():
        for system_file in sorted(list(systems_to_load_by_default)):
            if (lib_systems_dir / system_file).exists():
                paths_to_load.append(lib_systems_dir / system_file)

    user_systems_dir = user_config_dir / "systems"
    if user_systems_dir.is_dir():
        print("Found user systems directory. Loading custom systems...")
        for user_system_conf in sorted(user_systems_dir.glob("*.conf")):
            paths_to_load.append(user_system_conf)

    return paths_to_load


def _load_all_configurations():
    """
    Reads all configuration files from the library package and the user's
    home directory and merges them into the global `config` object.
    """
    parser = configparser.ConfigParser()
    paths_to_load = []

    # --- Part 1: Find LIBRARY configurations using importlib.resources ---
    # This is the robust way to find data files inside your package.
    # It works for tests and for installed packages (even in zip files).
    try:
        # 'resources.files()' returns a path-like object to a package's contents.
        # We point it to our 'measurekit.config' sub-package.
        lib_config_dir = resources.files("measurekit.config")

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
    # --- End Part 1 ---

    # --- Part 2: Find USER configurations (this logic remains the same) ---
    user_config_dir = Path.home() / ".config" / "measurekit"
    print(f"Searching for user configurations in: {user_config_dir}")

    user_master_conf = user_config_dir / "measurekit.conf"
    if user_master_conf.exists():
        print(f"Found user master config: {user_master_conf}")
        paths_to_load.append(user_master_conf)

    user_systems_dir = user_config_dir / "systems"
    if user_systems_dir.is_dir():
        print("Found user systems directory. Loading custom systems...")
        for user_system_conf in sorted(user_systems_dir.glob("*.conf")):
            paths_to_load.append(user_system_conf)
    # --- End Part 2 ---

    # --- Part 3: Load the discovered files (this logic remains the same) ---
    if not paths_to_load:
        print(
            "\n[WARNING] No configuration files found. The library will have no units defined."
        )
        return

    print("\nLoading configuration files in order of precedence:")
    for path in paths_to_load:
        print(f"  -> {path}")

    # For `resources` paths, we may need to convert them to strings to be safe
    str_paths = [str(p) for p in paths_to_load]
    parser.read(str_paths, encoding="utf-8")

    # Populate the config object...
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


# En tu archivo: measurekit.startup.py


def _initialize_prefix_system():
    """Registra los prefijos cargados en el sistema de medición."""
    if not config.prefix_definitions:
        return
    print("\nInitializing prefixes...")
    for name, value_str in config.prefix_definitions.items():
        try:
            symbol, factor_str = [p.strip() for p in value_str.split(",")]
            factor = float(factor_str)

            # Usamos una función de registro que guarde toda la información
            # Esto es un cambio clave. Asumimos que register_prefix puede guardar
            # el nombre y el factor.
            register_prefix(symbol=symbol, factor=factor, name=name)

            print(
                f"  Registered Prefix: {name.capitalize()} (Symbol: {symbol}, Factor: {factor})"
            )
        except Exception as e:
            print(f"  [ERROR] Could not load prefix '{name}'. Reason: {e}")


# ... (El resto de las funciones _initialize_dimension_system, _initialize_unit_system, etc.,
#      que ya tenías, están correctas y no necesitan cambios)
def _initialize_dimension_system():
    if not config.dimension_definitions:
        return
    print("\nInitializing dimensions...")

    base_symbols = []
    for name, value_str in config.dimension_definitions.items():
        parts = [p.strip() for p in value_str.split(",")]
        symbol = parts[0]
        base_symbols.append(symbol)

        # Si se especifica "noprefix", se añade a la lista de bloqueo
        if len(parts) > 1 and parts[1] == "noprefix":
            block_prefixes_for_dimension_symbol(symbol)
            print(f"  -> Prefixes disabled for dimension {name} ({symbol})")

    Dimension.set_base_dimensions(base_symbols)
    loaded_dimensions = []
    for name, value_str in config.dimension_definitions.items():
        symbol = value_str.split(",")[0].strip()
        dim_instance = Dimension({symbol: 1})
        register_dimension(dim_instance, name.capitalize())
        setattr(dimensions_module, name.upper(), dim_instance)
        loaded_dimensions.append(name.upper())
        print(f"  Registered Dimension: {name.capitalize()} -> {symbol}")

    _generate_stub(
        dimensions_module,
        loaded_dimensions,
        "Dimension",
        "from measurekit.measurement.dimensions import Dimension",
    )


def _initialize_unit_system():
    """
    Inicializa el sistema de unidades, registrando las unidades base y
    generando automáticamente las unidades con prefijos.
    """
    if not config.unit_definitions:
        return
    print("\nInitializing units...")
    loaded_units = []

    # Obtenemos un diccionario de prefijos desde el objeto de configuración
    # para tener acceso a sus símbolos, nombres y factores.
    # Asumimos que register_prefix los ha almacenado en un lugar accesible,
    # por ejemplo, en el propio módulo de conversions.
    from measurekit.measurement.conversions import get_all_prefixes

    prefixes = (
        get_all_prefixes()
    )  # Ej: {'k': {'name': 'kilo', 'factor': 1000}, ...}

    for key, value_str in config.unit_definitions.items():
        try:
            # --- PARSEO DE LA LÍNEA DE UNIDAD (lógica existente) ---
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

            # --- 1. REGISTRAR LA UNIDAD BASE ---
            register_unit(
                symbol, dimension, factor, key, *all_aliases, recipe=recipe
            )
            unit_instance = get_unit(symbol)
            setattr(units_module, key, unit_instance)
            loaded_units.append(key)
            print(f"  Registered Base Unit: {key} (Symbol: {symbol})")

            # --- 2. NUEVA LÓGICA: GENERAR Y REGISTRAR UNIDADES CON PREFIJOS ---
            # Comprobamos si la dimensión de esta unidad tiene los prefijos bloqueados.
            # `dimension.exponents.copy().popitem()` es una forma de obtener el símbolo de la dimensión base.
            dim_symbol = next(iter(dimension.exponents), None)
            if dim_symbol in _PREFIX_BLOCKLIST:
                continue  # Saltamos a la siguiente unidad si los prefijos están bloqueados

            # Iteramos sobre todos los prefijos que hemos cargado
            for prefix_symbol, prefix_data in prefixes.items():
                prefix_name = prefix_data["name"]
                prefix_factor = prefix_data["factor"]

                # Creamos el nuevo nombre, símbolo y factor para la unidad prefijada
                new_unit_key = f"{prefix_name}{key}"  # ej. "kilometer"
                new_unit_symbol = f"{prefix_symbol}{symbol}"  # ej. "km"
                new_unit_factor = prefix_factor * factor

                # La nueva receta es la unidad base original
                new_recipe = unit_instance

                # Los nuevos alias son combinaciones de prefijos y alias originales
                new_aliases = [f"{prefix_symbol}{alias}" for alias in aliases]
                all_new_aliases = [new_unit_key] + new_aliases

                # Registramos la nueva unidad prefijada en el sistema
                register_unit(
                    new_unit_symbol,
                    dimension,  # La dimensión no cambia
                    new_unit_factor,
                    new_unit_key,
                    *all_new_aliases,
                    recipe=new_recipe,
                )

                # La añadimos al módulo `units` para que sea accesible (ej. units.kilometer)
                new_unit_instance = get_unit(new_unit_symbol)
                setattr(units_module, new_unit_key, new_unit_instance)
                loaded_units.append(new_unit_key)
                # Usamos una impresión menos prominente para no saturar la consola
                # print(f"    -> Registered Prefixed Unit: {new_unit_key} (Symbol: {new_unit_symbol})")

        except Exception as e:
            print(
                f"  [ERROR] Could not load unit '{key}' or its prefixes. Reason: {e}"
            )

    _generate_stub(
        units_module,
        loaded_units,
        "CompoundUnit",
        "from measurekit.measurement.units import CompoundUnit",
    )


def _initialize_constant_system():
    if not config.constant_definitions:
        return
    print("\nInitializing constants...")
    # ... (resto de la función sin cambios)
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
            print(f"  Registered Constant: {name} = {constant_quantity}")
            setattr(constants_module, name, constant_quantity)
            loaded_constants.append(name)
        except Exception as e:
            print(f"  [ERROR] Could not load constant '{name}'. Reason: {e}")
    _generate_stub(
        constants_module,
        loaded_constants,
        "Quantity",
        "from measurekit.measurement.quantity import Quantity",
    )


def _generate_stub(
    module, names: list[str], class_name: str, import_line: str
):
    # ... (resto de la función sin cambios)
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
            print(f"Updating autocompletion file: {stub_path}")
            stub_path.write_text(new_content, encoding="utf-8")
    except Exception as e:
        print(
            f"[WARNING] Could not write .pyi stub file for {module.__name__}. Reason: {e}"
        )
