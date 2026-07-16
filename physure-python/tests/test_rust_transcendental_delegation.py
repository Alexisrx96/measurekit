import math

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
