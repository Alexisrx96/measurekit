"""Adding a bare number to a dimensioned quantity must raise.

Regression tests for the '5 m + 2' bug: the scalar was silently assumed
to carry self's unit, producing '7 m'. A bare number carries no unit, so
it may only combine additively with a dimensionless quantity.
"""

import pytest

from physure import Q_
from physure.domain.exceptions import IncompatibleUnitsError


class TestBareNumberRejected:
    def test_add_scalar_to_dimensioned_raises(self):
        with pytest.raises(IncompatibleUnitsError):
            Q_(5, "m") + 2

    def test_radd_scalar_to_dimensioned_raises(self):
        with pytest.raises(IncompatibleUnitsError):
            2 + Q_(5, "m")

    def test_sub_scalar_from_dimensioned_raises(self):
        with pytest.raises(IncompatibleUnitsError):
            Q_(5, "m") - 2

    def test_rsub_dimensioned_from_scalar_raises(self):
        with pytest.raises(IncompatibleUnitsError):
            2 - Q_(5, "m")

    def test_add_scalar_with_uncertainty_raises(self):
        with pytest.raises(IncompatibleUnitsError):
            Q_(5.0, "m", uncertainty=0.1) + 2

    def test_add_float_raises(self):
        with pytest.raises(IncompatibleUnitsError):
            Q_(5, "km") + 2.5

    def test_add_array_to_dimensioned_raises(self):
        np = pytest.importorskip("numpy")
        with pytest.raises(IncompatibleUnitsError):
            Q_(np.array([1.0, 2.0]), "m") + np.array([3.0, 4.0])


class TestDimensionlessStillWorks:
    def test_add_scalar_to_dimensionless(self):
        assert (Q_(5, "") + 2).magnitude == 7.0

    def test_radd_scalar_to_dimensionless(self):
        assert (2 + Q_(5, "")).magnitude == 7.0

    def test_sub_scalar_from_dimensionless(self):
        assert (Q_(5, "") - 2).magnitude == 3.0

    def test_quantity_addition_unaffected(self):
        assert (Q_(5, "m") + Q_(2, "m")).magnitude == 7.0

    def test_mul_by_scalar_unaffected(self):
        # Multiplying by a bare number is legitimate (scaling).
        assert (Q_(5, "m") * 2).magnitude == 10
