"""Property-Based Tests for Algebraic and Physical Invariants."""

import numpy as np
from hypothesis import HealthCheck, Phase, assume, given, settings
from hypothesis import strategies as st

from measurekit import Quantity
from tests.strategies import (
    backend_arrays,
    linear_units,
    quantities,
    same_shape_quantities,
    same_unit_quantities,
)

# Common settings for property checks
# We reduce max_examples for complex backend interactions
SETTINGS = settings(max_examples=50, deadline=None)


# -----------------------------------------------------------------------------
# Algebraic Group Properties (Scalar focus for rigor)
# -----------------------------------------------------------------------------


@given(
    same_unit_quantities(
        n=2,
        backend="numpy",
        unit_strategy=linear_units(),
        allow_uncertainty=False,
    )
)
@settings(max_examples=50, deadline=None, phases=[Phase.generate])
def test_commutativity_addition(qs):
    """a + b == b + a"""
    a, b = qs

    try:
        res1 = a + b
        res2 = b + a
    except (ValueError, RuntimeError):
        # Skip invalid shapes
        assume(False)

    # Use loose tolerance for floating point
    assert np.allclose(res1.magnitude, res2.magnitude, rtol=1e-5, atol=1e-8)
    assert res1.unit == res2.unit


@given(
    same_shape_quantities(
        n=2,
        backend="numpy",
        allow_uncertainty=False,
    )
)
@settings(max_examples=50, deadline=None, phases=[Phase.generate])
def test_commutativity_multiplication(qs):
    """a * b == b * a (for scalars/element-wise)"""
    a, b = qs
    try:
        res1 = a * b
        res2 = b * a
    except (ValueError, RuntimeError):
        assume(False)

    assert np.allclose(res1.magnitude, res2.magnitude, rtol=1e-5, atol=1e-8)
    assert res1.unit == res2.unit


@given(
    same_unit_quantities(
        n=3,
        backend="numpy",
        unit_strategy=linear_units(),
        allow_uncertainty=False,
    )
)
@settings(max_examples=50, deadline=None, phases=[Phase.generate])
def test_associativity_addition(qs):
    """(a + b) + c == a + (b + c)"""
    a, b, c = qs
    try:
        res1 = (a + b) + c
        res2 = a + (b + c)
    except (ValueError, RuntimeError):
        assume(False)

    assert np.allclose(res1.magnitude, res2.magnitude, rtol=1e-4, atol=1e-7)


@given(
    same_shape_quantities(
        n=3,
        backend="numpy",
        allow_uncertainty=False,
    )
)
@settings(max_examples=50, deadline=None, phases=[Phase.generate])
def test_associativity_multiplication(qs):
    """(a * b) * c == a * (b * c)"""
    a, b, c = qs
    try:
        res1 = (a * b) * c
        res2 = a * (b * c)
    except (ValueError, RuntimeError):
        assume(False)

    assert np.allclose(res1.magnitude, res2.magnitude, rtol=1e-4, atol=1e-7)
    assert res1.unit == res2.unit


@st.composite
def distributivity_triplet(draw):
    """Generates (a, b, c) such that (b + c) is valid and a * (b + c) is valid."""
    # 1. Generate b and c with same unit and shape
    b, c = draw(
        same_unit_quantities(
            n=2,
            backend="numpy",
            unit_strategy=linear_units(),
            allow_uncertainty=False,
        )
    )
    # 2. Generate a with same shape as b, c
    a = draw(
        quantities(
            backend="numpy",
            magnitude=backend_arrays(shape=b.magnitude.shape, backend="numpy"),
            allow_uncertainty=False,
        )
    )
    return a, b, c


@given(distributivity_triplet())
@settings(max_examples=50, deadline=None, phases=[Phase.generate])
def test_distributivity(triplet):
    """a * (b + c) == a * b + a * c"""
    a, b, c = triplet
    try:
        res1 = a * (b + c)
        res2 = a * b + a * c
    except (ValueError, RuntimeError):
        assume(False)

    assert np.allclose(res1.magnitude, res2.magnitude, rtol=1e-4, atol=1e-7)
    assert res1.unit == res2.unit


# -----------------------------------------------------------------------------
# Physical Invariants
# -----------------------------------------------------------------------------


@given(
    same_unit_quantities(
        n=2,
        backend="numpy",
        unit_strategy=linear_units(),
        allow_uncertainty=False,
    )
)
@settings(
    max_examples=50,
    deadline=None,
    phases=[Phase.generate],
    suppress_health_check=[HealthCheck.filter_too_much],
)
def test_unit_invariance(qs):
    """(a + b).to(target) == a.to(target) + b.to(target)

    Physical result shouldn't depend on intermediate representation.
    """
    a, b = qs
    system = a.system

    # Find a compatible unit to convert to
    compatible_units = []
    candidates = system.UNIT_REGISTRY.get(a.dimension, {})
    for name in candidates:
        if name != a.unit.to_string():
            compatible_units.append(name)

    assume(len(compatible_units) > 0)
    target_unit = compatible_units[0]

    try:
        lhs = (a + b).to(target_unit)
        rhs = a.to(target_unit) + b.to(target_unit)
    except (ValueError, RuntimeError):
        assume(False)

    assert np.allclose(lhs.magnitude, rhs.magnitude, rtol=1e-4, atol=1e-6)


@given(
    quantities(backend="numpy", allow_uncertainty=False),
    st.floats(min_value=0.1, max_value=10.0),
)
@settings(max_examples=50, deadline=None, phases=[Phase.generate])
def test_dimensional_homogeneity_scaling(q, scale):
    """f(scale * x) == scale * f(x) for linear functions."""
    res1 = q * scale
    res2 = Quantity.from_input(q.magnitude * scale, q.unit, q.system)

    assert res1.unit == res2.unit

    m1 = res1.magnitude
    m2 = res2.magnitude

    def to_np(x):
        if hasattr(x, "toarray"):
            return x.toarray()
        if hasattr(x, "todense"):
            return x.todense()
        if hasattr(x, "cpu"):
            x = x.cpu()
        if hasattr(x, "detach"):
            x = x.detach()
        if hasattr(x, "numpy"):
            return x.numpy()
        return np.asarray(x)

    np.testing.assert_allclose(to_np(m1), to_np(m2), rtol=1e-5)
