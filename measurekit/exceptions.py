"""Exceptions for MeasureKit.

.. autoclass:: MeasureKitError
.. autoclass:: IncompatibleUnitsError
.. autoclass:: ConversionError
.. autoclass:: UnitNotFoundError

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from measurekit.measurement.quantity import Quantity
    from measurekit.measurement.units import CompoundUnit


class MeasureKitError(Exception):
    """Base exception for all MeasureKit errors."""

    pass


class IncompatibleUnitsError(MeasureKitError):
    """Raised when trying to perform an operation with incompatible units."""

    def __init__(self, unit1: CompoundUnit, unit2: CompoundUnit):
        """Initialize the exception with the incompatible units.

        :param unit1: The first unit involved in the operation.
        :param unit2: The second unit involved in the operation.
        """
        self.unit1 = unit1
        self.unit2 = unit2
        super().__init__(
            f"Cannot operate with incompatible units: '{unit1}' and '{unit2}'."
        )


class ConversionError(MeasureKitError):
    """Raised when a unit conversion is not possible."""

    def __init__(self, from_unit: CompoundUnit, to_unit: CompoundUnit):
        """Initialize the exception with the units involved in the failed conversion.

        :param from_unit: The unit from which we are trying to convert.
        :param to_unit: The unit to which we are trying to convert.
        """
        self.from_unit = from_unit
        self.to_unit = to_unit
        super().__init__(
            f"No conversion path from '{from_unit}' to '{to_unit}'."
        )


class UnitNotFoundError(MeasureKitError, KeyError):
    """Raised when a unit is not found in the registry."""

    def __init__(self, unit_name: str):
        """Initialize the exception with the missing unit name.

        :param unit_name: The name of the unit that was not found.
        """
        self.unit_name = unit_name
        super().__init__(f"Unit '{unit_name}' not found or registered.")
