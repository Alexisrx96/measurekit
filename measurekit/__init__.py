# measurekit/__init__.py (Refactored)

from measurekit.context import _set_global_default_system
from measurekit.measurement.api import QuantityFactory
from measurekit.startup import create_default_system
from measurekit.system import UnitSystem

# --- Application Assembly ---
# 1. Create the concrete adapter instance. This is our main application object.
default_system: UnitSystem = create_default_system(
    True
)  # <- This is the long-running call

# *** FIX FOR CIRCULAR IMPORT: Now set the global reference in the context module.
_set_global_default_system(default_system)

# breakpoint()
# 2. Expose the primary factory method (Inbound Port) from our configured system.
#    This binds the `Q_` factory to our fully configured `default_system`.
Q_ = QuantityFactory()


# 3. Expose the `get_unit` function from the configured system instance.
def get_unit(unit_expression):
    return get_active_system().get_unit(unit_expression)


# --- Expose Core Domain Objects and Exceptions ---
from measurekit.context import get_active_system, system_context
from measurekit.exceptions import (
    ConversionError,
    MeasureKitError,
    UnitNotFoundError,
)
from measurekit.measurement.quantity import Quantity
from measurekit.measurement.uncertainty import Uncertainty
from measurekit.measurement.units import CompoundUnit

__all__ = [
    "Q_",
    "get_unit",
    "Quantity",
    "CompoundUnit",
    "Uncertainty",
    "MeasureKitError",
    "ConversionError",
    "UnitNotFoundError",
    "default_system",
    "system_context",
    "get_active_system",
]

__version__ = "0.0.2"
