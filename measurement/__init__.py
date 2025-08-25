"""Measurement package initialization."""

from measurement.conversions import UNIT_REGISTRY
from measurement.dimensions import Dimension
from measurement.units import CompoundUnit

# Initialize the unit registry
UNIT_REGISTRY.clear()