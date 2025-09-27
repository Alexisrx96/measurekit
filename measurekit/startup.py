from __future__ import annotations

import configparser
from importlib import resources
from typing import cast, Dict, Any

from measurekit.measurement.conversions import UnitDefinition
from measurekit.measurement.dimensions import (
    Dimension,
    block_prefixes_for_dimension_symbol,
)
from measurekit.measurement.units import CompoundUnit
from measurekit.system import UnitSystem


def _load_all_configurations_into(
    parser: configparser.ConfigParser, verbose: bool
):
    """Reads all configuration files and loads them into the given parser."""
    if verbose:
        print("\n--- Phase 1: Loading Configuration Files ---")

    config_files = [
        "measurekit.conf",
        "systems/international.conf",
        "systems/imperial.conf",
    ]
    paths_to_read = []

    try:
        lib_config_dir = resources.files("measurekit.config")
        for file_name in config_files:
            file_path = lib_config_dir / file_name
            if file_path.is_file():
                paths_to_read.append(str(file_path))
                if verbose:
                    print(f"  -> Found: {file_path}")
            elif verbose:
                print(f"  -> Not found: {file_path}")
    except ModuleNotFoundError:
        print(
            "[WARNING] Could not locate built-in library configuration files."
        )
        return

    if paths_to_read:
        parser.read(paths_to_read, encoding="utf-8")
    else:
        print("[WARNING] No configuration files were loaded.")


class UnitSystemBuilder:
    """A builder class for constructing a UnitSystem instance."""

    def __init__(self, name: str | None = None, verbose: bool = False):
        self._system = UnitSystem(name=name)
        self._verbose = verbose

    def add_settings(self, settings_data: dict[str, str]) -> UnitSystemBuilder:
        self._system.settings.update(settings_data)
        return self

    def add_prefixes(self, prefixes_data: dict[str, str]) -> UnitSystemBuilder:
        """Adds prefixes from a dictionary of prefix definitions."""
        if not prefixes_data:
            return self
        if self._verbose:
            print("\n--- Phase 2: Initializing Prefixes ---")
        for name, value_str in prefixes_data.items():
            symbol, factor_str = [p.strip() for p in value_str.split(",")]
            self._system.register_prefix(
                symbol=symbol, factor=float(factor_str), name=name
            )
        return self

    def add_dimensions(
        self, dimensions_data: dict[str, str]
    ) -> UnitSystemBuilder:
        """Adds dimensions from a dictionary of dimension definitions."""
        if not dimensions_data:
            return self
        if self._verbose:
            print("\n--- Phase 3: Initializing Dimensions ---")
        base_symbols = [
            v.split(",")[0].strip() for v in dimensions_data.values()
        ]
        Dimension.set_base_dimensions(base_symbols)
        for name, value_str in dimensions_data.items():
            parts = [p.strip() for p in value_str.split(",")]
            symbol = parts[0]
            if len(parts) > 1 and parts[1] == "noprefix":
                block_prefixes_for_dimension_symbol(symbol)
            dim_instance = Dimension.from_string(symbol)
            self._system.register_dimension(dim_instance, name.capitalize())
        return self

    def add_units(self, units_data: dict[str, str]) -> UnitSystemBuilder:
        """Adds units from a dictionary of unit definitions."""
        if self._verbose:
            print("\n--- Phase 4: Initializing Units ---")

        self._system.unit_definitions.update(units_data)

        # Pass 1: Register all units
        for key, value_str in units_data.items():
            aliases = []
            main_part = value_str
            if "[" in value_str:
                main_part, alias_part = value_str.split("[", 1)
                aliases = [
                    a.strip() for a in alias_part.strip()[:-1].split(",")
                ]

            parts = [p.strip() for p in main_part.split(",") if p.strip()]

            allow_prefixes = True
            if "noprefix" in parts:
                allow_prefixes = False
                parts.remove("noprefix")

            factor = float(parts[0])
            dimension = Dimension.from_string(parts[1])

            symbol = aliases[0] if aliases else key
            all_aliases = set([key] + aliases)

            self._system.register_unit(
                symbol,
                dimension,
                factor,
                key,
                *all_aliases,
                allow_prefixes=allow_prefixes,
            )

        # Pass 2: Register recipes for derived units after all base units are available
        for key, value_str in units_data.items():
            if "[" in value_str:
                main_part, _ = value_str.split("[", 1)
            else:
                main_part = value_str

            parts = [p.strip() for p in main_part.split(",") if p.strip()]
            recipe_str = parts[2] if len(parts) > 2 else None

            if recipe_str:
                unit_def = cast(
                    UnitDefinition, self._system.get_definition(key)
                )
                if unit_def and not unit_def.recipe:
                    # Obtenemos el objeto CompoundUnit a partir de la receta.
                    recipe_unit = self._system.get_unit(recipe_str)

                    # Simplificamos la receta a sus componentes de unidades base.
                    # Esto es crucial para la conversión.
                    simplified_recipe = recipe_unit.simplify(self._system)

                    # Asignamos la receta simplificada al objeto de definición de la unidad.
                    unit_def.recipe = simplified_recipe
                    self._system._UNIT_RECIPES[unit_def.symbol] = (
                        simplified_recipe
                    )

        return self

    def add_constants(
        self, constants_data: dict[str, str]
    ) -> UnitSystemBuilder:
        """Adds constants from a dictionary of constant definitions."""
        if not constants_data:
            return self
        if self._verbose:
            print("\n--- Phase 5: Initializing Constants ---")
        for name, value_str in constants_data.items():
            value_str_part, unit_str = value_str.split(maxsplit=1)
            value = float(value_str_part)
            unit = (
                self._system.get_unit(unit_str.strip())
                if unit_str.strip() != "1"
                else CompoundUnit({})
            )
            _ = self._system.Q_(value, unit)
        return self

    def build(self) -> UnitSystem:
        """Returns the fully constructed and configured UnitSystem object."""
        if self._verbose:
            print("\n--- Initialization Complete ---")
        return self._system


def create_default_system(verbose: bool = False) -> UnitSystem:
    """Creates and populates a default UnitSystem using a decoupled builder."""
    parser = configparser.ConfigParser()
    _load_all_configurations_into(parser, verbose)

    builder = UnitSystemBuilder(name="Default", verbose=verbose)
    return (
        builder.add_settings(
            dict(parser.items("Settings")) if "Settings" in parser else {}
        )
        .add_prefixes(
            dict(parser.items("Prefixes")) if "Prefixes" in parser else {}
        )
        .add_dimensions(
            dict(parser.items("Dimensions")) if "Dimensions" in parser else {}
        )
        .add_units(dict(parser.items("Units")) if "Units" in parser else {})
        .add_constants(
            dict(parser.items("Constants")) if "Constants" in parser else {}
        )
        .build()
    )
