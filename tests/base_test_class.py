import unittest

from measurement.conversions import UNIT_DIMENSIONS, UNIT_REGISTRY
from measurement.dimensions import _DIMENSION_NAME_REGISTRY, Dimension
from measurement.units import CompoundUnit


class BaseTestUnit(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        """Reset the unit registry after each test."""
        _DIMENSION_NAME_REGISTRY.clear()
        UNIT_REGISTRY.clear()
        UNIT_DIMENSIONS.clear()
        CompoundUnit._aliases.clear()
        CompoundUnit._alias_to_exponents.clear()
        CompoundUnit._cache.clear()
        Dimension._cache.clear()
