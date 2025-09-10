"""Test suite for the Unit class."""

import math
import unittest

import numpy as np

from measurekit.measurement.api import Q_
from measurekit.measurement.conversions import register_unit
from measurekit.measurement.dimensions import Dimension
from measurekit.measurement.units import CompoundUnit
from tests.base_test_class import BaseTestUnit


class TestUnit(BaseTestUnit):
    """Tests for the Unit class."""

    def setUp(self):
        """Set up common units and dimensions for tests."""
        # Base dimensions
        length = Dimension({"L": 1})
        time = Dimension({"T": 1})
        mass = Dimension({"M": 1})

        # Register base units with conversion factors
        register_unit("m", length, 1.0, "meter")
        register_unit("cm", length, 0.01, "centimeter")
        register_unit("km", length, 1000.0, "kilometer")
        register_unit("s", time, 1.0, "second")
        register_unit("min", time, 60.0, "minute")
        register_unit("h", time, 3600.0, "hour")
        register_unit("kg", mass, 1.0, "kilogram")
        register_unit("g", mass, 0.001, "gram")

        # Create common compound units
        self.meter = CompoundUnit({"m": 1})
        self.centimeter = CompoundUnit({"cm": 1})
        self.kilometer = CompoundUnit({"km": 1})
        self.second = CompoundUnit({"s": 1})
        self.minute = CompoundUnit({"min": 1})
        self.kilogram = CompoundUnit({"kg": 1})
        self.gram = CompoundUnit({"g": 1})
        self.newton = CompoundUnit({"kg": 1, "m": 1, "s": -2})

        # Register aliases
        CompoundUnit.register_alias({"m": 1}, "length")
        CompoundUnit.register_alias({"s": 1}, "time")
        CompoundUnit.register_alias({"kg": 1}, "mass")
        CompoundUnit.register_alias({"m": 1, "s": -1}, "velocity", "speed")
        CompoundUnit.register_alias({"kg": 1, "m": 1, "s": -2}, "force")

    def test_initialization(self):
        """Test different initialization patterns."""
        # Basic initialization with value and unit
        q1 = Q_(5.0, self.meter)
        self.assertEqual(q1.magnitude, 5.0)
        self.assertEqual(q1.unit, self.meter)
        self.assertEqual(q1.dimension, self.meter.dimension)

        # Initialize with another quantity
        q2 = Q_(q1.magnitude, q1.unit)
        self.assertEqual(q2.magnitude, 5.0)
        self.assertEqual(q2.unit, self.meter)

        # Initialize with default unit
        UnitWithMeter = Q_[self.meter]
        q3 = UnitWithMeter(10.0)
        self.assertEqual(q3.magnitude, 10.0)
        self.assertEqual(q3.unit, self.meter)

        # Initialize with a different unit but same dimension
        q4 = UnitWithMeter(10.0, self.centimeter)
        self.assertEqual(
            q4.magnitude, 0.1
        )  # Converted to meters (default unit)
        self.assertEqual(q4.unit, self.meter)

        # Initialization without unit should raise error if no default
        with self.assertRaises(ValueError):
            Q_(5.0)

    def test_class_getitem(self):
        """
        Test the __class_getitem__ method for creating specialized
        quantity types.
        """
        # Create a specialized quantity type
        LengthUnit = Q_[self.meter]

        # Create instances
        length1 = LengthUnit(5.0)
        length2 = LengthUnit(10.0)

        # Verify correct defaults
        self.assertEqual(length1.unit, self.meter)
        self.assertEqual(length2.unit, self.meter)

        # Caching behavior - getting the same specialized type
        LengthUnit2 = Q_[self.meter]
        self.assertIs(LengthUnit, LengthUnit2)

    def test_conversion(self):
        """Test unit conversion with the to method."""
        # Create a quantity with meters
        length = Q_(5.0, self.meter)

        # Convert to centimeters
        length_cm = length.to(self.centimeter)
        self.assertEqual(length_cm.magnitude, 500.0)
        self.assertEqual(length_cm.unit, self.centimeter)

        # Convert to kilometers
        length_km = length.to(self.kilometer)
        self.assertEqual(length_km.magnitude, 0.005)
        self.assertEqual(length_km.unit, self.kilometer)

        # Convert using string unit
        length_cm_str = length.to("cm")
        self.assertEqual(length_cm_str.magnitude, 500.0)
        self.assertEqual(length_cm_str.unit, self.centimeter)

        # Converting between incompatible dimensions should raise error
        time = Q_(10.0, self.second)
        with self.assertRaises(ValueError):
            time.to(self.meter)

    def test_arithmetic_operations(self):
        """Test arithmetic operations between quantities."""
        # Addition
        length1 = Q_(5.0, self.meter)
        length2 = Q_(10.0, self.meter)
        sum_length = length1 + length2
        self.assertEqual(sum_length.magnitude, 15.0)
        self.assertEqual(sum_length.unit, self.meter)

        # Addition with incompatible units should raise error
        time = Q_(10.0, self.second)
        with self.assertRaises(ValueError):
            length1 + time

        # Subtraction
        diff_length = length2 - length1
        self.assertEqual(diff_length.magnitude, 5.0)
        self.assertEqual(diff_length.unit, self.meter)

        # Multiplication
        time = Q_(2.0, self.second)
        velocity = length1 / time
        self.assertEqual(velocity.magnitude, 2.5)
        self.assertEqual(velocity.unit.exponents, {"m": 1, "s": -1})

        # Division
        area = Q_(10.0, self.meter**2)
        length_from_area = area / length1
        self.assertEqual(length_from_area.magnitude, 2.0)
        self.assertEqual(length_from_area.unit, self.meter)

        # Power
        area = length1**2
        self.assertEqual(area.magnitude, 25.0)
        self.assertEqual(area.unit.exponents, {"m": 2})

        # Scalar operations
        double_length = length1 * 2
        self.assertEqual(double_length.magnitude, 10.0)
        self.assertEqual(double_length.unit, self.meter)

        half_length = length1 / 2
        self.assertEqual(half_length.magnitude, 2.5)
        self.assertEqual(half_length.unit, self.meter)

        # Right operations
        double_length_right = 2 * length1
        self.assertEqual(double_length_right.magnitude, 10.0)
        self.assertEqual(double_length_right.unit, self.meter)

        inverse_length = 1 / length1
        self.assertEqual(inverse_length.magnitude, 0.2)
        self.assertEqual(inverse_length.unit.exponents, {"m": -1})

    def test_comparison_operations(self):
        """Test comparison operations between quantities."""
        length1 = Q_(5.0, self.meter)
        length2 = Q_(10.0, self.meter)
        length3 = Q_(5.0, self.meter)

        # Equality
        self.assertEqual(length1, length3)
        self.assertNotEqual(length1, length2)

        # Comparison with incompatible units should raise error
        time = Q_(5.0, self.second)
        with self.assertRaises(
            ValueError,
            msg=(
                "Cannot compare quantities with different dimensions"
                " L != T m != s"
            ),
        ):
            length1 == time  # noqa: B015

        # Less than, greater than
        self.assertLess(length1, length2)
        self.assertGreater(length2, length1)
        self.assertLessEqual(length1, length3)
        self.assertGreaterEqual(length1, length3)

    def test_numeric_protocol(self):
        """Test adherence to Python's numeric protocols."""
        length = Q_(5.0, self.meter)

        # Basic numeric operations
        self.assertEqual(float(length), 5.0)
        self.assertEqual(abs(-length).magnitude, 5.0)
        self.assertEqual((+length).magnitude, 5.0)
        self.assertEqual((-length).magnitude, -5.0)

        # Rounding
        self.assertEqual(round(Q_(5.6, self.meter)).magnitude, 6.0)
        self.assertEqual(round(Q_(5.4, self.meter)).magnitude, 5.0)
        self.assertEqual(round(Q_(5.55, self.meter), 1).magnitude, 5.6)

        # Math functions through Real protocol
        self.assertEqual(math.floor(length), Q_(5, self.meter))
        self.assertEqual(math.ceil(Q_(5.1, self.meter)), Q_(6, self.meter))
        self.assertEqual(math.trunc(Q_(5.1, self.meter)), Q_(5, self.meter))

    def test_formatting(self):
        """Test string formatting methods."""
        length = Q_(5.0, self.meter)

        # Basic string representation
        self.assertEqual(str(length), "5.0 m")
        self.assertEqual(
            repr(length),
            "Quantity(5.0, CompoundUnit({'m': 1}), uncertainty=0.0)",
        )

        # Formatting
        self.assertEqual(f"{length:.2f}", "5.00 m")
        self.assertEqual(f"{length:frac}", "5 m")

    def test_extended_arithmetic(self):
        """Test additional arithmetic operations."""
        length1 = Q_(10.0, self.meter)
        length2 = Q_(3.0, self.meter)

        # Floor division
        result = length1 // length2
        self.assertEqual(result.magnitude, 3.0)
        self.assertEqual(result.unit.exponents, {})  # dimensionless

        # Modulo
        remainder = length1 % length2
        self.assertEqual(remainder.magnitude, 1.0)
        self.assertEqual(remainder.unit, self.meter)

        # Right floor division
        scalar_div = 20 // length2
        self.assertEqual(scalar_div.magnitude, 6.0)
        self.assertEqual(scalar_div.unit.exponents, {"m": -1})

        # Right modulo
        scalar_mod = 11 % length1
        self.assertEqual(scalar_mod.magnitude, 1.0)
        self.assertEqual(scalar_mod.unit, self.meter)

    def test_uncertainty_propagation2(self):
        """Test the propagation of uncertainty in arithmetic operations."""
        # Multiplicación
        q1 = Q_(10.0, self.meter, uncertainty=0.1)  # (10.0 ± 0.1) m
        q2 = Q_(5.0, self.second, uncertainty=0.2)  # (5.0 ± 0.2) s

        result_mul = q1 * q2
        self.assertAlmostEqual(result_mul.magnitude, 50.0)
        # √( (0.1/10)^2 + (0.2/5)^2 ) * 50 ≈ 2.06
        self.assertAlmostEqual(result_mul.uncertainty, 2.06155, places=5)

        # División
        result_div = q1 / q2
        self.assertAlmostEqual(result_div.magnitude, 2.0)
        # √( (0.1/10)^2 + (0.2/5)^2 ) * 2 ≈ 0.0824
        self.assertAlmostEqual(result_div.uncertainty, 0.08246, places=5)

        # Suma
        q3 = Q_(20.0, self.meter, uncertainty=0.4)
        result_add = q1 + q3
        self.assertAlmostEqual(result_add.magnitude, 30.0)
        # √( 0.1^2 + 0.4^2 ) ≈ 0.412
        self.assertAlmostEqual(result_add.uncertainty, 0.41231, places=5)

    def test_uncertainty_propagation(self):
        """Test the propagation of uncertainty for basic arithmetic."""
        # Por qué este cambio: En lugar de usar @pytest.mark.parametrize,
        # definimos los casos de prueba en una lista de tuplas y los
        # recorremos con un bucle for. Esto es 100% compatible con unittest.
        test_cases = [
            # q1_val, q1_unc, q2_val, q2_unc, op, expected_val, expected_unc
            # Suma: δz = sqrt(δx² + δy²)
            (10.0, 0.1, 5.0, 0.2, "+", 15.0, 0.22361),
            # Resta: δz = sqrt(δx² + δy²)
            (10.0, 0.1, 5.0, 0.2, "-", 5.0, 0.22361),
            # Multiplicación: δz = |z|*sqrt((δx/x)²+(δy/y)²)
            (10.0, 0.1, 5.0, 0.2, "*", 50.0, 2.06155),
            # División: δz = |z|*sqrt((δx/x)²+(δy/y)²)
            (10.0, 0.1, 5.0, 0.2, "/", 2.0, 0.08246),
            # Potencia: δz = |z*n|*(δx/x)
            (10.0, 0.1, 2, 0, "**", 100.0, 2.0),
        ]

        for (
            q1_val,
            q1_unc,
            q2_val,
            q2_unc,
            op,
            expected_val,
            expected_unc,
        ) in test_cases:
            # Usamos subtests para que, si uno falla, te diga exactamente
            # cuál fue.
            with self.subTest(op=op, q1_val=q1_val, q2_val=q2_val):
                q1 = Q_(q1_val, self.meter, uncertainty=q1_unc)

                if op == "**":
                    result = q1**q2_val
                else:
                    unit2 = self.meter if op in "+-" else self.second
                    q2 = Q_(q2_val, unit2, uncertainty=q2_unc)

                    if op == "+":
                        result = q1 + q2
                    elif op == "-":
                        result = q1 - q2
                    elif op == "*":
                        result = q1 * q2
                    elif op == "/":
                        result = q1 / q2

                # Usamos assertAlmostEqual para comparar números de punto
                # flotante.
                self.assertAlmostEqual(result.magnitude, expected_val)
                self.assertAlmostEqual(
                    result.uncertainty, expected_unc, places=5
                )

    def test_rtruediv_uncertainty(self):
        """Test uncertainty for inverse division (1/q)."""
        q = Q_(4.0, self.meter, uncertainty=0.1)  # 4.0 ± 0.1 m
        result = 1 / q  # Debería ser 0.25 ± 0.00625 m⁻¹

        # δz = |z| * (δx/x) = 0.25 * (0.1 / 4.0) = 0.00625
        self.assertAlmostEqual(result.magnitude, 0.25)
        self.assertEqual(result.unit.exponents, {"m": -1})
        self.assertAlmostEqual(result.uncertainty, 0.00625)

    def test_numpy_sqrt_uncertainty(self):
        """Test uncertainty propagation for numpy.sqrt."""
        area = Q_(100.0, self.meter**2, uncertainty=2.0)  # (100 ± 2) m²
        length = np.sqrt(area)  # Debería ser (10 ± 0.1) m

        # δz = |z| * 0.5 * (δx/x) = 10 * 0.5 * (2/100) = 0.1
        self.assertAlmostEqual(length.magnitude, 10.0)
        self.assertEqual(length.unit, self.meter)
        self.assertAlmostEqual(length.uncertainty, 0.1)


if __name__ == "__main__":
    unittest.main()
