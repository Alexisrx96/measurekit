"""MeasureKit: A Python Library for Unit-Aware Scientific Calculations.

This library provides a comprehensive framework for performing calculations
with physical quantities, ensuring dimensional consistency and providing a
robust system for unit conversions. It is designed to be intuitive and easy to
use, allowing developers to focus on the logic of their calculations without
worrying about the intricacies of unit management.
"""

# --- Application Assembly ---
# The default system is now lazily loaded by context.get_current_system().
# We expose a proxy or simply rely on get_current_system().

from measurekit.application.context import (
    get_current_system,
    use_system,
)
from measurekit.application.factories import QuantityFactory
from measurekit.domain.measurement.units import get_default_system

# Expose the primary factory method (Inbound Port)
# QuantityFactory will use get_default_system() internally if no system provided.
Q_ = QuantityFactory()


# 3. Expose the `get_unit` function from the configured system instance.
def get_unit(unit_expression):
    """Retrieve a unit by its expression from the active unit system."""
    return get_current_system().get_unit(unit_expression)


# --- Expose Core Domain Objects and Exceptions ---
# IMPORTANT: get_active_system is an alias for get_current_system
from measurekit.application.context import get_active_system
from measurekit.domain.exceptions import (
    ConversionError,
    MeasureKitError,
    UnitNotFoundError,
)
from measurekit.domain.measurement.quantity import Quantity
from measurekit.domain.measurement.uncertainty import Uncertainty
from measurekit.domain.measurement.units import CompoundUnit

__all__ = [
    "Q_",
    "CompoundUnit",
    "ConversionError",
    "MeasureKitError",
    "Quantity",
    "Uncertainty",
    "UnitNotFoundError",
    "get_active_system",
    "get_current_system",
    "get_unit",
    "use_system",
]

__version__ = "0.0.3"

# Register Pandas Accessor if pandas is available
try:
    import pandas as pd

    from measurekit.ext import pandas_support
except ImportError:
    pass

try:
    import numba

    import measurekit.ext.numba_support
except ImportError:
    pass
