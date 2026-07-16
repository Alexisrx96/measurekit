import math

import numpy as np
import pytest

import physure as mk
from physure import Q_
from physure.domain.measurement.quantity import Quantity


def get_val(q):
    mag = q.magnitude
    return float(mag.mean()) if hasattr(mag, "mean") else float(mag)


def test_check_and_handle_rust_transcendental_not_rust_wrapped():
    with mk.propagation_mode("correlated"):
        q = Q_(0.5, "rad", uncertainty=0.1)
        assert q._check_and_handle_rust_transcendental("sin") is None


def test_check_and_handle_rust_transcendental_rust_wrapped():
    with mk.uncertainty_mode("gaussian"):
        q = Q_(0.5, "rad", uncertainty=0.1)
        result = q._check_and_handle_rust_transcendental("sin")
        assert result is not None
        assert isinstance(result, Quantity)
        assert math.isclose(get_val(result), math.sin(0.5), rel_tol=1e-9)


# tanh omitted: no backend (python/numpy/jax/core_backend.py) implements a
# tanh method today, so there is no trusted Python result to compare against.
# Pre-existing gap, unrelated to Rust delegation — Rust's tanh correctness is
# covered by the Rust-side unit tests and the Task 3 manual smoke test.
@pytest.mark.parametrize(
    ("func_name", "input_value", "input_unit"),
    [
        ("sin", 0.5, "rad"),
        ("cos", 0.5, "rad"),
        ("tan", 0.5, "rad"),
        ("exp", 0.5, ""),
        ("log", 2.0, ""),
    ],
)
def test_rust_python_parity(func_name, input_value, input_unit):
    with mk.uncertainty_mode("gaussian"):
        rust_q = Q_(input_value, input_unit, uncertainty=0.1)
        rust_result = getattr(rust_q, func_name)()

    with mk.propagation_mode("correlated"):
        python_q = Q_(input_value, input_unit, uncertainty=0.1)
        python_result = getattr(python_q, func_name)()

    assert math.isclose(
        get_val(rust_result), get_val(python_result), rel_tol=1e-9
    )
    assert math.isclose(
        rust_result.uncertainty, python_result.uncertainty, rel_tol=1e-6
    )


def test_tensor_backend_mean_raises_on_multi_element_array():
    with mk.uncertainty_mode("gaussian"):
        rust_q = Q_(1.0, "m", uncertainty=0.1)
    array_q = Q_(np.array([1.0, 2.0, 3.0]), "m")
    with pytest.raises(Exception):  # noqa: B017, PT011
        _ = rust_q + array_q
