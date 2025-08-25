from collections import defaultdict
from typing import TYPE_CHECKING, Optional

from measurement.dimensions import Dimension
from notation.base_entity import BaseExponentEntity
from notation.lexer import generate_tokens
from notation.parsers import NotationParser

if TYPE_CHECKING:
    from measurement.units import CompoundUnit


class UnitDefinition:
    """Singleton class representing a unit definition."""

    _instances = {}
    symbol: str
    dimension: Dimension
    factor_to_base: float
    name: Optional[str]

    def __new__(
        cls,
        symbol: str,
        dimension: Dimension,
        factor_to_base: float,
        name: Optional[str] = None,
    ):
        key = (symbol, dimension, factor_to_base)
        if key in cls._instances:
            return cls._instances[key]
        instance = super().__new__(cls)
        cls._instances[key] = instance
        instance.symbol = symbol
        instance.dimension = dimension
        instance.factor_to_base = factor_to_base
        instance.name = name
        return instance

    def __init__(
        self,
        symbol: str,
        dimension: Dimension,
        factor_to_base: float,
        name: Optional[str],
    ):
        pass

    def __str__(self) -> str:
        return (
            "UnitDefinition"
            f"({self.symbol}, {self.dimension}, {self.factor_to_base})"
        )

    def __repr__(self) -> str:
        return (
            "UnitDefinition("
            f"{self.symbol}, {self.dimension}, "
            f"{self.factor_to_base}, {self.name})"
        )


UNIT_REGISTRY: dict[Dimension, dict[str, UnitDefinition]] = defaultdict(dict)
UNIT_DIMENSIONS: dict[str, Dimension] = {}


def register_unit(
    symbol: str,
    dimension: Dimension,
    factor_to_base: float,
    name: Optional[str],
    *aliases: str,
) -> None:
    """Registers a new unit in the system."""
    from measurement.units import get_unit, CompoundUnit

    tokens = generate_tokens(symbol)
    parser = NotationParser(tokens, BaseExponentEntity)
    result = parser.parse()
    normalized_symbol = str(result)

    unit = UnitDefinition(normalized_symbol, dimension, factor_to_base, name)
    UNIT_REGISTRY[dimension][normalized_symbol] = unit
    UNIT_DIMENSIONS[normalized_symbol] = dimension

    if aliases and (compound_unit := get_unit(normalized_symbol)):
        for alias in aliases:
            CompoundUnit.register_alias(compound_unit.exponents, alias)


def get_conversion_factor(
    dimension: Dimension, from_unit: str, to_unit: str
) -> float:
    """
    Returns the conversion factor between two units of the same dimension.
    """
    try:
        return (
            UNIT_REGISTRY[dimension][from_unit].factor_to_base
            / UNIT_REGISTRY[dimension][to_unit].factor_to_base
        )
    except KeyError as exc:
        raise ValueError(
            "Invalid conversion: "
            f"{from_unit} to {to_unit} in dimension {dimension}"
        ) from exc


def find_dimension_for_unit(unit: str) -> Dimension:
    """Finds the dimension of a given unit."""
    if unit in UNIT_DIMENSIONS:
        return UNIT_DIMENSIONS[unit]
    raise ValueError(f"Unit '{unit}' is not registered.")


def compound_factor(compound: "CompoundUnit") -> float:
    """Calculates the conversion factor for a compound unit."""
    factor = 1.0
    unit_def = UNIT_REGISTRY.get(compound.dimension, {}).get(str(compound))
    if unit_def is not None:
        return unit_def.factor_to_base
    for unit, exp in compound.exponents.items():
        dim = find_dimension_for_unit(unit)
        unit_def = UNIT_REGISTRY.get(dim, {}).get(unit, None)
        if unit_def is None:
            raise ValueError(f"Unit '{unit}' is not registered for conversion")
        factor *= unit_def.factor_to_base**exp
    return factor


def get_compound_unit_conversion_factor(
    source: "CompoundUnit", target: "CompoundUnit"
) -> float:
    """Calculates the conversion factor between two compound units."""
    if source.dimension != target.dimension:
        raise ValueError(
            f"Incompatible compound unit dimensions. {source} != {target}"
        )
    return compound_factor(source) / compound_factor(target)
