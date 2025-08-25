from typing import Callable

import sympy as sp

from measurement.dimensions import Dimension
from measurement.quantity import Quantity
from measurement.units import CompoundUnit
from notation.lexer import to_subscript


class Function:
    def __init__(
        self,
        parameters: dict[str, Dimension],
        output: Dimension,
        func: Callable[..., float],
        reference_units: dict[Dimension, CompoundUnit],
        symbolic_func: sp.Expr | None = None,
    ):
        """Defines a function that operates on physical quantities.

        :param parameters: Dict mapping parameter names to their expected
        dimensions.
        :param output: The expected dimension of the output.
        :param func: The function to compute the output.
        :param reference_units: A mapping of dimensions to reference units for
        internal conversions.
        :param symbolic_func: SymPy function to allow differentiation.
        """
        self.parameters = parameters
        self.output = output
        self.func = func
        self.reference_units = reference_units
        self.symbolic_func = symbolic_func

    def __call__(self, output_unit: CompoundUnit, **kwargs) -> Quantity:
        """Calls the function by providing the required parameters as Quantity
        objects.
        """
        converted_values = {}

        for param, expected_dim in self.parameters.items():
            if param not in kwargs:
                raise ValueError(f"Missing parameter: {param}")

            value = kwargs[param]
            if not isinstance(value, Quantity):
                raise TypeError(f"Parameter '{param}' must be a Quantity")

            if value.dimension != expected_dim:
                raise ValueError(
                    f"Incorrect dimension for '{param}': expected "
                    f"{expected_dim}, got {value.dimension}"
                )

            # Convert to the reference unit
            ref_unit = self.reference_units[expected_dim]
            converted_values[param] = value.to(ref_unit).value

        # Compute result
        result_value = self.func(**converted_values)

        # Validate output unit
        if output_unit.dimension != self.output:
            raise ValueError(
                f"Output unit {output_unit} does not match expected dimension"
                f" {self.output}"
            )
        return Quantity(result_value, output_unit)

    def derivative(self, respect_to: str):
        """Returns a new Function representing the derivative of the function
        with respect to a variable."""
        if self.symbolic_func is None:
            raise ValueError(
                "No symbolic function available for differentiation."
            )

        if respect_to not in self.parameters:
            raise ValueError(
                f"Cannot differentiate with respect to {respect_to}, it's not "
                "a parameter."
            )

        # Compute derivative
        symbolic_vars = {param: sp.Symbol(param) for param in self.parameters}
        symbolic_expr = self.symbolic_func.subs(symbolic_vars)
        derivative_expr = sp.diff(symbolic_expr, symbolic_vars[respect_to])

        # Determine new output dimension
        respect_dim = self.parameters[respect_to]
        new_output_dim = self.output / respect_dim

        # Convert symbolic function to Python
        derivative_func = sp.lambdify(
            list(symbolic_vars.values()), derivative_expr
        )

        return Function(
            parameters=self.parameters,
            output=new_output_dim,
            func=derivative_func,
            reference_units=self.reference_units,
            symbolic_func=derivative_expr,
        )

    def __str__(self):
        """Returns a readable representation of the function."""
        param_str = ", ".join(self.parameters.keys())
        eq_str = (
            str(self.symbolic_func)
            if self.symbolic_func
            else "<No symbolic equation>"
        )

        return (
            f"Function({to_subscript(param_str)}) -> {self.output}: "
            f"{to_subscript(eq_str)}"
        )

    def __repr__(self):
        """Returns a detailed representation useful for debugging."""
        return (
            "Function"
            f"({self.parameters=}, {self.output=}, {self.symbolic_func=}, "
            f"{self.reference_units=})"
        )
