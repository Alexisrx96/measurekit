"""This module provides functionality for handling units in the measurement
system.

It includes the definition and manipulation of compound units, as well as
utility functions for unit conversion and retrieval. The module leverages the
concept of dimensions to ensure compatibility and correctness in unit
operations.

Classes:
- CompoundUnit: Represents a unit composed of various base units raised to
different powers. Provides methods for arithmetic operations, conversion, and
string representation.

Functions:
- get_unit: Retrieves a unit definition based on a string expression.

Imports:
- Various utility functions and classes from related modules for parsing and
  conversions.
"""

from __future__ import annotations

import importlib
import logging
from collections import defaultdict
from dataclasses import dataclass
from functools import singledispatchmethod
from typing import TYPE_CHECKING, ClassVar, cast

from measurement.conversions import (
    UNIT_DIMENSIONS,
    get_compound_unit_conversion_factor,
)
from measurement.dimensions import Dimension
from notation.lexer import generate_tokens, to_superscript
from notation.parsers import NotationParser
from notation.typing import ExponentsDict

if TYPE_CHECKING:
    from measurement.quantity import Quantity


@dataclass(frozen=True)
class CompoundUnit:
    """Represents a unit composed of various base units raised to different
    powers.

    Provides methods for arithmetic operations, conversion, and string
    representation.
    """

    _cache: ClassVar[dict[tuple, CompoundUnit]] = {}
    _aliases: ClassVar[dict[tuple, list[str]]] = defaultdict(list)
    _alias_to_exponents: ClassVar[dict[str, tuple]] = {}

    __slots__ = ("exponents",)

    exponents: ExponentsDict

    def __new__(cls, exponents: ExponentsDict) -> CompoundUnit:
        """Creates a new CompoundUnit instance with a unique set of
        exponents."""
        key = tuple(sorted((k, v) for k, v in exponents.items() if v != 0))
        if key in cls._cache:
            return cls._cache[key]
        instance = super().__new__(cls)
        object.__setattr__(instance, "exponents", dict(key))
        cls._cache[key] = instance
        return instance

    def __init__(self, exponents: ExponentsDict | None = None) -> None:
        """Initializes a CompoundUnit with given exponents."""

    @classmethod
    def register_alias(cls, exponents: ExponentsDict, *aliases: str) -> None:
        """Registers aliases for a given set of exponents."""
        if not aliases:
            return

        # Sort the exponents to create a consistent key
        key = tuple(sorted((k, v) for k, v in exponents.items() if v != 0))

        # Initialize if not already present
        if key not in cls._aliases:
            cls._aliases[key] = []

        # Add new aliases while preserving existing ones and their order
        for alias in aliases:
            # Check if this alias is already used for a different exponent set
            if (
                alias in cls._alias_to_exponents
                and cls._alias_to_exponents[alias] != key
            ):
                # If already registered with different exponents, skip it
                logging.warning(
                    f"Alias '{alias}' already registered with different exponents. "
                    f"Existing: {cls._alias_to_exponents[alias]}, Attempted: {key}"
                )
                continue

            # Remove the alias if it already exists in the current list (to avoid duplicates)
            if alias in cls._aliases[key]:
                cls._aliases[key].remove(alias)

            # Add to the beginning of the list for highest priority
            cls._aliases[key].insert(-1, alias)

            # Update the reverse lookup
            cls._alias_to_exponents[alias] = key

    def to_string(
        self, use_alias: bool = False, alias_preference: str | None = None
    ) -> str:
        """Converts the CompoundUnit to a string representation."""
        # First, check if we should use an alias and if one exists
        if use_alias:
            # Use a tuple of sorted exponents as a key for the aliases dictionary
            key = tuple(
                sorted((k, v) for k, v in self.exponents.items() if v != 0)
            )
            if key in self._aliases and self._aliases[key]:
                aliases = self._aliases[key]
                if alias_preference and alias_preference in aliases:
                    return alias_preference
                # Return the first alias (highest priority)
                return aliases[0]

        # If no alias or if aliases are not to be used, generate the string representation
        numerator, denominator = [], []
        for unit, exp in sorted(
            self.exponents.items(), key=lambda x: (-x[1], x[0])
        ):
            formatted = (
                f"{unit}{to_superscript(abs(exp)) if abs(exp) != 1 else ''}"
            )
            (numerator if exp > 0 else denominator).append(formatted)
        n = "·".join(numerator)
        d = "·".join(denominator)
        if d and n:
            return f"{n}/{f'({d})' if '·' in d else d}"
        if d and not n:
            return f"1/{f'({d})' if '·' in d else d}"
        if n and not d:
            return n
        return "1"

    def get_aliases(self) -> list[str]:
        """Returns a list of registered aliases for the current exponents, ordered by priority."""
        key = tuple(
            sorted((k, v) for k, v in self.exponents.items() if v != 0)
        )
        return self._aliases.get(
            key, []
        ).copy()  # Return a copy to prevent modification

    def __format__(self, format_spec: str) -> str:
        """Formats the CompoundUnit based on the given specification."""
        if not format_spec or format_spec == "full":
            # Default empty format spec returns full representation
            return self.to_string(use_alias=False)

        parts = format_spec.split(":")
        if parts[0] == "alias":
            alias_preference = parts[1] if len(parts) > 1 else None
            return self.to_string(
                use_alias=True, alias_preference=alias_preference
            )

        # Default to full format for any unrecognized format spec
        return self.to_string(use_alias=False)

    def __str__(self) -> str:
        """Returns a string representation of the CompoundUnit.

        Uses the first registered alias if available, otherwise uses the
        standard exponent representation.
        """
        return self.to_string(use_alias=False)

    def __repr__(self) -> str:
        """Returns a detailed string representation of the CompoundUnit."""
        return f"CompoundUnit({self.exponents!r})"

    def __eq__(self, other: object) -> bool:
        """Checks equality between two CompoundUnit instances."""
        return (
            isinstance(other, CompoundUnit)
            and self.exponents == other.exponents
        )

    def __hash__(self) -> int:
        """Returns a hash value for the CompoundUnit."""
        return hash(tuple(sorted(self.exponents.items())))

    def __mul__(self, other: CompoundUnit) -> CompoundUnit:
        """Multiplies two CompoundUnit instances."""
        result: ExponentsDict = self.exponents.copy()
        for unit, exp in other.exponents.items():
            result[unit] = result.get(unit, 0) + exp
        return CompoundUnit(result)

    def __truediv__(self, other: CompoundUnit) -> CompoundUnit:
        """Divides the current CompoundUnit by another."""
        result: ExponentsDict = self.exponents.copy()
        for unit, exp in other.exponents.items():
            result[unit] = result.get(unit, 0) - exp
        return CompoundUnit(result)

    def __pow__(self, exponent: int) -> CompoundUnit:
        """Raises the CompoundUnit to the power of exponent."""
        return CompoundUnit(
            {u: exp * exponent for u, exp in self.exponents.items()}
        )

    @property
    def dimension(self) -> Dimension:
        """Calculates the dimension of the CompoundUnit."""
        overall = Dimension({})
        for unit, exp in self.exponents.items():
            if unit in UNIT_DIMENSIONS:
                overall *= UNIT_DIMENSIONS[unit] ** exp
            else:
                raise ValueError(f"Unknown dimension for unit '{unit}'")
        return overall

    def conversion_factor_to(self, target: CompoundUnit) -> float:
        """Calculates the conversion factor to another CompoundUnit."""
        return get_compound_unit_conversion_factor(self, target)

    def convert_value(self, value: float, target: CompoundUnit) -> float:
        """Converts a value to the target CompoundUnit."""
        return value * self.conversion_factor_to(target)

    @singledispatchmethod
    def __rtruediv__(self, other: float | int) -> CompoundUnit:
        """Handles division of a scalar by a CompoundUnit."""
        return CompoundUnit({u: -exp for u, exp in self.exponents.items()})

    def __rmul__(self, other: float | int | Quantity) -> Quantity:
        """Handles multiplication of a scalar by a CompoundUnit."""
        q: type[Quantity] = importlib.import_module(
            "measurement.quantity"
        ).Quantity
        if isinstance(other, (float, int)):
            return q(other, self)
        if isinstance(other, q):
            return q(other.value, other.unit * self)
        return NotImplemented


def get_unit(unit_expression: str) -> CompoundUnit:
    """Parses a unit expression and returns the corresponding CompoundUnit.

    This function first checks if the provided unit expression is already
    registered as an alias. If so, it retrieves the associated exponents,
    constructs the CompoundUnit, and returns it immediately. Otherwise, it
    tokenizes and parses the expression.

    Args:
        unit_expression (str): The unit expression to parse.

    Returns:
        CompoundUnit: The parsed CompoundUnit.
    """
    # First, check if the unit_expression is a registered alias.
    if unit_expression in CompoundUnit._alias_to_exponents:
        key = CompoundUnit._alias_to_exponents[unit_expression]
        exponents = dict(key)
        return CompoundUnit(exponents)

    # If no alias was found, parse the unit expression normally.
    tokens = generate_tokens(unit_expression)
    parser = NotationParser(tokens, CompoundUnit)
    return cast(CompoundUnit, parser.parse())
