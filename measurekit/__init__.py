__IS_STARTED = False

if not __IS_STARTED:
    __IS_STARTED = True
    from measurekit.startup import initialize_system

    initialize_system()

from measurekit.exceptions import (
    ConversionError,
    MeasureKitError,
    UnitNotFoundError,
)
from measurekit.measurement.api import Q_
from measurekit.measurement.quantity import Quantity
from measurekit.measurement.uncertainty import Uncertainty
from measurekit.measurement.units import CompoundUnit, get_unit

__all__ = [
    "Q_",
    "Quantity",
    "get_unit",
    "CompoundUnit",
    "Uncertainty",
    "MeasureKitError",
    "ConversionError",
    "UnitNotFoundError",
]

__version__ = "0.0.1"
