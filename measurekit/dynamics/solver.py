# measurekit/dynamics/solver.py
"""This module provides a unit-aware solver for ordinary differential equation (ODE) initial value problems.

It wraps the powerful `solve_ivp` function from the SciPy library, allowing
users to define their differential equations using `measurekit.Quantity`
objects. This ensures that all calculations are dimensionally correct,
preventing common errors in physics and engineering simulations.
"""

from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

from measurekit.measurement.api import Q_
from measurekit.measurement.quantity import Quantity


class ODESolution:
    """A class to store and present the solution of an ODE.

    Allows for easy access to the results.
    """

    def __init__(self, t: Quantity, y: list[Quantity]):
        """Initializes the ODESolution with time points and state values."""
        self.t = t
        self.y = y

    def __repr__(self):
        """Provides a concise string representation of the solution."""
        return (
            f"ODESolution(t=[{self.t[0]:.2f}...{self.t[-1]:.2f}],"
            f" num_states={len(self.y)})"
        )


def solve_unit_aware_ivp(
    fun: Callable[[Quantity, list[Quantity]], list[Quantity]],
    t_span: list[Quantity],
    y0: list[Quantity],
    t_eval: np.ndarray | None = None,
    **kwargs,
) -> ODESolution:
    """Solves an initial value problem, handling units consciously and efficiently."""
    # --- 1. Unit Unpacking (ONCE) ---
    # Why? We extract all unit information BEFORE entering the solver's
    # loop. This is the key to efficiency.
    t_unit = t_span[0].unit
    y0_values = np.array([q.magnitude for q in y0])
    y0_units = [q.unit for q in y0]

    # We calculate the expected units for the derivatives beforehand.
    dydt_units = [state_unit / t_unit for state_unit in y0_units]

    t_span_values = [t_span[0].magnitude, t_span[1].to(t_unit).magnitude]

    # --- 2. Function Wrapper Creation (Efficient Approach) ---
    # Why? This wrapper now works exclusively with NumPy arrays.
    # The trick is that it "closes" over the unit variables
    # (t_unit, y0_units, dydt_units) to be able to repack and
    # unpack at the call boundaries.
    def fun_wrapper(t_val: float, y_val: np.ndarray) -> np.ndarray:
        # a. Repackaging into Quantities for the user's DX
        t_q = Q_(t_val, t_unit)
        y_q = [Q_(val, unit) for val, unit in zip(y_val, y0_units)]

        # b. Calling the user's original function
        dy_dt_q = fun(t_q, y_q)

        # c. Unpacking the derivatives into a numeric array
        # Necessary conversions are performed to ensure consistency.
        dy_dt_values = np.array(
            [
                res.to(expected_unit).magnitude
                for res, expected_unit in zip(dy_dt_q, dydt_units)
            ]
        )

        return dy_dt_values

    # --- 3. Calling the SciPy Solver ---
    # SciPy only sees numbers, which allows it to run at maximum speed.
    sol = solve_ivp(
        fun_wrapper, t_span_values, y0_values, t_eval=t_eval, **kwargs
    )

    # --- 4. Repackaging the Final Solution (ONCE) ---
    # Why? Once SciPy has finished its work, we take the resulting
    # numeric arrays and convert them back into Quantity objects
    # for the user.
    solution_t = Q_(sol.t, t_unit)
    solution_y = [
        Q_(state_values, y0_units[i]) for i, state_values in enumerate(sol.y)
    ]

    return ODESolution(solution_t, solution_y)
