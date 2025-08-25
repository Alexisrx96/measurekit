from __future__ import annotations

import math
from fractions import Fraction
from numbers import Real
from typing import Any

import numpy as np

from measurement.dimensions import Dimension
from measurement.units import CompoundUnit, get_unit

Numeric = int | float


class Quantity(Real):
    default_unit: CompoundUnit | None = None
    _cache: dict[CompoundUnit, type] = {}

    value: float
    fraction: Fraction
    unit: CompoundUnit
    dimension: Dimension

    @classmethod
    def __class_getitem__(cls, item: CompoundUnit) -> type:
        if item in cls._cache:
            return cls._cache[item]
        new_cls = type(
            f"{cls.__name__}[{item}]", (cls,), {"default_unit": item}
        )
        cls._cache[item] = new_cls
        return new_cls

    def __init__(
        self,
        value: Numeric | Quantity = 1,
        unit: CompoundUnit | None = None,
    ):
        if isinstance(value, Quantity):
            value, unit = value.value, value.unit

        if unit is None:
            if self.default_unit is None:
                raise ValueError(
                    "No unit provided and no default unit available."
                )
            unit = self.default_unit

        if self.default_unit is not None and unit != self.default_unit:
            conversion_factor = unit.conversion_factor_to(self.default_unit)
            value = value * conversion_factor
            unit = self.default_unit

        self.value = value
        self.fraction = Fraction(str(value))
        self.unit = unit
        self.dimension = unit.dimension

    def to(self, target_unit: CompoundUnit | str) -> Quantity:
        if not isinstance(self.unit, CompoundUnit):
            raise TypeError(
                "Conversion is only supported for CompoundUnit types"
            )
        if isinstance(target_unit, str):
            target_unit = get_unit(target_unit)

        new_value = self.value * self.unit.conversion_factor_to(target_unit)
        return Quantity(new_value, target_unit)

    def __add__(self, other: Quantity) -> Quantity:
        if self.dimension != other.dimension or self.unit != other.unit:
            raise ValueError(
                "Cannot add quantities with different dimensions or units"
                f"{self.dimension} != {other.dimension}"
                f"{self.unit} != {other.unit}"
            )
        return Quantity(self.value + other.value, self.unit)

    def __sub__(self, other: Quantity) -> Quantity:
        if self.dimension != other.dimension or self.unit != other.unit:
            raise ValueError(
                "Cannot subtract quantities with different dimensions or units"
            )
        return Quantity(self.value - other.value, self.unit)

    def __mul__(self, other: Numeric | Quantity | CompoundUnit) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self.value * other.value, self.unit * other.unit)
        if isinstance(other, CompoundUnit):
            if other.dimension != self.dimension:
                return Quantity(self.value, self.unit * other)
            return Quantity(
                self.value * other.conversion_factor_to(self.unit), self.unit
            )
        return Quantity(self.value * other, self.unit)

    def __rdiv__(self, other: Numeric | Quantity) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self.value / other.value, self.unit / other.unit)
        return Quantity(self.value / other, 1 / self.unit)

    def __truediv__(self, other: Numeric | Quantity) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(self.value / other.value, self.unit / other.unit)
        return Quantity(self.value / other, self.unit)

    def __pow__(self, exponent: int) -> Quantity:
        return Quantity(self.value**exponent, self.unit**exponent)

    def __format__(self, format_spec: str) -> str:
        """
        Format the Quantity using a composite format specification.

        The format_spec can be provided in one of the following forms:
          1. "<numeric_format>|<unit_format>" (e.g., ".2f|full" or "frac|alias")
          2. "<numeric_format>" (e.g., ".2f", where the unit defaults to 'full')
          3. "<unit_format>" if the format_spec is recognized as a unit format (e.g., "alias" or "full")
             so that the numeric part defaults to str(self.value).

        Special case:
          - "frac" for the numeric part will output the Fraction representation.
        """
        recognized_unit_formats = {"alias", "full"}

        # Check for a composite spec using the delimiter '|'.
        if "|" in format_spec:
            numeric_format, unit_format = format_spec.split("|", 1)
        else:
            # If the provided format spec is one of the recognized unit formats,
            # treat it as a unit spec and default the numeric part.
            if (
                format_spec in recognized_unit_formats
                or format_spec.startswith("alias:")
                or format_spec.startswith("full:")
            ):
                numeric_format = ""
                unit_format = format_spec
            else:
                numeric_format = format_spec
                unit_format = "full"  # Default unit format.

        # Format numeric part.
        if numeric_format == "frac":
            numeric_str = str(self.fraction)
        elif numeric_format:
            try:
                numeric_str = format(float(self.value), numeric_format)
            except (ValueError, TypeError):
                numeric_str = str(self.value)
        else:
            numeric_str = str(self.value)

        # Format unit part.
        unit_str = format(self.unit, unit_format)
        return f"{numeric_str} {unit_str}"

    def __str__(self) -> str:
        return f"{self.value} {self.unit:full}"

    def __repr__(self) -> str:
        return f"Quantity({self.value!r}, {self.unit!r})"

    def __rtruediv__(self, other: Numeric) -> Quantity:
        return Quantity(other / self.value, 1 / self.unit)

    def __radd__(self, other: Numeric) -> Quantity:
        return Quantity(self.value + other, self.unit)

    def __rmul__(self, other: Numeric) -> Quantity:
        return Quantity(self.value * other, self.unit)

    def __rsub__(self, other: Numeric) -> Quantity:
        return Quantity(other - self.value, 1 / self.unit)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quantity):
            raise TypeError(f"Expected Quantity, got {type(other).__name__}")
        if self.dimension != other.dimension or self.unit != other.unit:
            raise ValueError(
                "Cannot compare quantities with different dimensions "
                f"{self.dimension} != {other.dimension} "
                f"{self.unit} != {other.unit}"
            )
        return self.value == other.value

    def __hash__(self) -> int:
        return hash((self.value, self.unit))

    def __neg__(self) -> Quantity:
        return Quantity(-self.value, self.unit)

    def __pos__(self) -> Quantity:
        return Quantity(+self.value, self.unit)

    def __rpow__(self, base: Numeric) -> Quantity:
        return base**self.value

    def __abs__(self) -> Quantity:
        return Quantity(abs(self.value), self.unit)

    def __float__(self) -> float:
        return float(self.value)

    def __trunc__(self) -> int:
        return math.trunc(self.value)

    def __floor__(self) -> int:
        return math.floor(self.value)

    def __ceil__(self) -> int:
        return int(math.ceil(self.value))

    def __round__(self, ndigits: int | None = None):
        if ndigits is None:
            return Quantity(round(self.value), self.unit)
        return Quantity(round(self.value, ndigits), self.unit)

    def __floordiv__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            raise TypeError("Expected Quantity, got %s" % type(other).__name__)
        return Quantity(self.value // other.value, self.unit / other.unit)

    def __rfloordiv__(self, other: Numeric) -> Quantity:
        return Quantity(other // self.value, 1 / self.unit)

    def __mod__(self, other: Quantity) -> Quantity:
        if not isinstance(other, Quantity):
            raise TypeError("Expected Quantity, got %s" % type(other).__name__)
        return Quantity(self.value % other.value, self.unit)

    def __rmod__(self, other: Numeric) -> Quantity:
        return Quantity(other % self.value, self.unit)

    def __lt__(self, other: Quantity | Any) -> bool:
        if not isinstance(other, Quantity):
            raise TypeError(f"Expected Quantity, got {type(other).__name__}")
        if self.dimension != other.dimension:
            raise ValueError(
                "Cannot compare quantities with different dimensions"
                f"{self.dimension} != {other.dimension}"
            )
        return self.value < other.value

    def __le__(self, other: Quantity | Any) -> bool:
        if not isinstance(other, Quantity):
            raise TypeError(f"Expected Quantity, got {type(other).__name__}")
        if self.dimension != other.dimension:
            raise ValueError(
                "Cannot compare quantities with different dimensions"
                f"{self.dimension} != {other.dimension}"
            )
        return self.value <= other.value

    def __gt__(self, other: Quantity | Any) -> bool:
        if not isinstance(other, Quantity):
            raise TypeError(f"Expected Quantity, got {type(other).__name__}")
        if self.dimension != other.dimension:
            raise ValueError(
                "Cannot compare quantities with different dimensions"
                f"{self.dimension} != {other.dimension}"
            )
        return self.value > other.value

    def __ge__(self, other: Quantity | Any) -> bool:
        if not isinstance(other, Quantity):
            raise TypeError(f"Expected Quantity, got {type(other).__name__}")
        if self.dimension != other.dimension:
            raise ValueError(
                "Cannot compare quantities with different dimensions"
                f"{self.dimension} != {other.dimension}"
            )
        return self.value >= other.value

    # def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
    #     """Handle NumPy operations, preserving units."""
    #     if method != "__call__":
    #         return NotImplemented

    #     values, units = [], []
    #     for inp in inputs:
    #         if isinstance(inp, Quantity):
    #             values.append(inp.value)
    #             units.append(inp.unit)
    #         else:
    #             values.append(inp)
    #             units.append(None)

    #     result_value = ufunc(*values, **kwargs)

    #     # Handle unit transformations for sqrt, sin, log, etc.
    #     if ufunc == np.sqrt:
    #         if any(exp % 2 != 0 for _, exp in units[0].exponents.items()):
    #             raise ValueError(f"Cannot take square root of unit {units[0]}")
    #         result_unit = units[0] ** 0.5
    #     elif ufunc in {np.sin, np.cos, np.tan, np.exp, np.log}:
    #         if units[0] != get_unit(""):
    #             raise ValueError(f"{ufunc.__name__} requires a dimensionless quantity")
    #         result_unit = get_unit("")
    #     else:
    #         result_unit = units[0]

    #     return Quantity(result_value, result_unit)


Real.register(Quantity)

__all__ = ["Quantity"]
