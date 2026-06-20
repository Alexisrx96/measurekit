# UX/DX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three targeted UX/DX pain points: descriptive error messages for unknown units, rich Jupyter display, and ergonomic `.m`/`.u` aliases plus scalar unpacking.

**Architecture:** Three independent changes, each self-contained. Error fix goes in `measurekit/domain/exceptions.py` + `units.py`. Display and ergonomics go in `quantity.py`. No new files except the exception class already lives in `exceptions.py`.

**Tech Stack:** Python stdlib `difflib`, existing `sympy` (already used in `to_latex()`), pytest.

---

## Pre-flight

```bash
uv run pytest tests/measurement_tests/ -q   # baseline — must be green before starting
```

---

## Task 1: Add `UnknownUnitError` to exceptions module

**Files:**
- Modify: `measurekit/domain/exceptions.py`

**Context:** `IncompatibleUnitsError`, `UnitNotFoundError`, and `ConversionError` already live here. `UnknownUnitError` is a sibling — it fires when a unit string has no registered dimension. It must subclass both `MeasureKitError` and `ValueError` so existing `except ValueError` handlers keep working.

- [ ] **Step 1: Write the failing test**

Add to `tests/measurement_tests/test_units.py`:

```python
from measurekit.domain.exceptions import UnknownUnitError

def test_unknown_unit_error_is_value_error():
    err = UnknownUnitError("xyz")
    assert isinstance(err, ValueError)
    assert "xyz" in str(err)

def test_unknown_unit_error_with_suggestions():
    err = UnknownUnitError("metter", suggestions=["meter", "m"])
    assert "meter" in str(err)
    assert "m" in str(err)

def test_unknown_unit_error_no_suggestions():
    err = UnknownUnitError("qqqq")
    assert "qqqq" in str(err)
    assert "Did you mean" not in str(err)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_unknown_unit_error_is_value_error -xvs
```

Expected: `ImportError` or `AttributeError` — `UnknownUnitError` doesn't exist yet.

- [ ] **Step 3: Implement `UnknownUnitError`**

In `measurekit/domain/exceptions.py`, add after `UnitNotFoundError`:

```python
class UnknownUnitError(MeasureKitError, ValueError):
    """Raised when a unit string has no registered dimension."""

    def __init__(self, unit_name: str, suggestions: list[str] | None = None):
        self.unit_name = unit_name
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"Unknown unit '{unit_name}'.{hint}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_unknown_unit_error_is_value_error tests/measurement_tests/test_units.py::test_unknown_unit_error_with_suggestions tests/measurement_tests/test_units.py::test_unknown_unit_error_no_suggestions -xvs
```

Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add measurekit/domain/exceptions.py tests/measurement_tests/test_units.py
git commit -m "feat(errors): add UnknownUnitError with suggestion support"
```

---

## Task 2: Wire `UnknownUnitError` with `difflib` into `CompoundUnit.dimension()`

**Files:**
- Modify: `measurekit/domain/measurement/units.py` (line ~165)

**Context:** `CompoundUnit.dimension()` in `units.py` raises a bare `ValueError` when it detects an unknown base unit (the identity-loop check at line ~164). `system.UNIT_DIMENSIONS` is a `dict[str, Dimension]` — its keys are all known unit names. Pass those to `difflib.get_close_matches`.

- [ ] **Step 1: Write the failing test**

Add to `tests/measurement_tests/test_units.py`:

```python
import difflib
from measurekit.domain.exceptions import UnknownUnitError

def test_dimension_unknown_unit_raises_with_suggestion(system):
    """CompoundUnit.dimension() raises UnknownUnitError with a suggestion."""
    from measurekit.domain.measurement.converters import LinearConverter
    from measurekit.domain.measurement.dimensions import Dimension

    # Register 'meter' so get_close_matches can suggest it
    system.register_unit("meter", Dimension({"L": 1}), LinearConverter(1.0), "meter")

    bad_unit = CompoundUnit({"meterr": 1})  # typo — no dimension registered
    with pytest.raises(UnknownUnitError, match="meterr"):
        bad_unit.dimension(system)

def test_dimension_unknown_unit_no_suggestion(system):
    """UnknownUnitError message has no 'Did you mean' when nothing is close."""
    bad_unit = CompoundUnit({"xyzqqqq": 1})
    with pytest.raises(UnknownUnitError) as exc_info:
        bad_unit.dimension(system)
    assert "Did you mean" not in str(exc_info.value)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_dimension_unknown_unit_raises_with_suggestion tests/measurement_tests/test_units.py::test_dimension_unknown_unit_no_suggestion -xvs
```

Expected: FAIL — still raises `ValueError`, not `UnknownUnitError`.

- [ ] **Step 3: Update `CompoundUnit.dimension()` in `units.py`**

At the top of `units.py`, the import block already has `from measurekit.domain.exceptions import IncompatibleUnitsError`. Add `UnknownUnitError` to that import:

```python
from measurekit.domain.exceptions import IncompatibleUnitsError, UnknownUnitError
```

Then replace the bare `raise ValueError` at line ~165 (inside the `if is_identity:` block):

```python
# Before:
if is_identity:
    raise ValueError(
        f"Unknown dimension for unit '{unit_name}'"
    )

# After:
if is_identity:
    import difflib
    known = list(system.UNIT_DIMENSIONS.keys())
    suggestions = difflib.get_close_matches(unit_name, known, n=3, cutoff=0.6)
    raise UnknownUnitError(unit_name, suggestions or None)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_dimension_unknown_unit_raises_with_suggestion tests/measurement_tests/test_units.py::test_dimension_unknown_unit_no_suggestion -xvs
```

Expected: both PASS.

- [ ] **Step 5: Run full measurement test suite to check no regressions**

```bash
uv run pytest tests/measurement_tests/ -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add measurekit/domain/measurement/units.py tests/measurement_tests/test_units.py
git commit -m "feat(errors): raise UnknownUnitError with difflib suggestions in CompoundUnit.dimension()"
```

---

## Task 3: Add `_repr_html_` and `_repr_mimebundle_` to `Quantity`

**Files:**
- Modify: `measurekit/domain/measurement/quantity.py` (after line 754, near `_repr_latex_`)
- Test: `tests/measurement_tests/test_quantity.py`

**Context:** `_repr_latex_` is at line 752. `to_latex()` is at line 744. Add the two new repr methods directly after `_repr_latex_` (line 754). When `uncertainty` is present (`self._has_uncertainty` is True), include it in the HTML as ` ± {uncertainty}`.

- [ ] **Step 1: Write the failing test**

Add to `tests/measurement_tests/test_quantity.py`:

```python
def test_repr_html_returns_string(quantity_system, units):
    from measurekit.domain.measurement.quantity import Quantity
    q = Quantity(10.0, units["meter"], system=quantity_system)
    html = q._repr_html_()
    assert isinstance(html, str)
    assert "10.0" in html
    assert "<span" in html

def test_repr_html_dimensionless(quantity_system):
    from measurekit.domain.measurement.units import CompoundUnit
    from measurekit.domain.measurement.quantity import Quantity
    q = Quantity(1.0, CompoundUnit({}), system=quantity_system)
    html = q._repr_html_()
    assert "dimensionless" in html

def test_repr_mimebundle_keys(quantity_system, units):
    from measurekit.domain.measurement.quantity import Quantity
    q = Quantity(10.0, units["meter"], system=quantity_system)
    bundle = q._repr_mimebundle_()
    assert "text/plain" in bundle
    assert "text/latex" in bundle
    assert "text/html" in bundle
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/measurement_tests/test_quantity.py::test_repr_html_returns_string tests/measurement_tests/test_quantity.py::test_repr_html_dimensionless tests/measurement_tests/test_quantity.py::test_repr_mimebundle_keys -xvs
```

Expected: `AttributeError: 'Quantity' object has no attribute '_repr_html_'`.

- [ ] **Step 3: Add `_repr_html_` and `_repr_mimebundle_` to `Quantity`**

In `quantity.py`, add immediately after the `_repr_latex_` method (after line 754):

```python
def _repr_html_(self) -> str:
    """HTML display for Jupyter notebooks."""
    unit_str = self.unit.to_latex() or "dimensionless"
    mag = self.magnitude
    if self._has_uncertainty:
        return (
            f'<span style="font-family:monospace">'
            f'{mag} &plusmn; {self.uncertainty} '
            f'<span style="color:#888">{unit_str}</span>'
            f'</span>'
        )
    return (
        f'<span style="font-family:monospace">'
        f'{mag} <span style="color:#888">{unit_str}</span>'
        f'</span>'
    )

def _repr_mimebundle_(self, **kwargs) -> dict:
    """MIME bundle for Jupyter — lets the frontend pick the best format."""
    return {
        "text/plain": repr(self),
        "text/latex": self._repr_latex_(),
        "text/html": self._repr_html_(),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/measurement_tests/test_quantity.py::test_repr_html_returns_string tests/measurement_tests/test_quantity.py::test_repr_html_dimensionless tests/measurement_tests/test_quantity.py::test_repr_mimebundle_keys -xvs
```

Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add measurekit/domain/measurement/quantity.py tests/measurement_tests/test_quantity.py
git commit -m "feat(display): add _repr_html_ and _repr_mimebundle_ to Quantity"
```

---

## Task 4: Add `.m`, `.u`, and scalar `__iter__` to `Quantity`

**Files:**
- Modify: `measurekit/domain/measurement/quantity.py`
- Test: `tests/measurement_tests/test_quantity.py`

**Context:** `.m` (magnitude alias) and `.u` (unit alias) don't exist yet. `__iter__` at line 1043 already handles array quantities by yielding elements. The fix makes it conditional: for scalar quantities (`len(magnitude)` raises `TypeError`) yield `(magnitude, unit)`, for arrays keep the existing element-by-element behavior.

- [ ] **Step 1: Write the failing tests**

Add to `tests/measurement_tests/test_quantity.py`:

```python
def test_m_alias(quantity_system, units):
    from measurekit.domain.measurement.quantity import Quantity
    q = Quantity(42.0, units["meter"], system=quantity_system)
    assert q.m == 42.0
    assert q.m is q.magnitude

def test_u_alias(quantity_system, units):
    from measurekit.domain.measurement.quantity import Quantity
    q = Quantity(42.0, units["meter"], system=quantity_system)
    assert q.u is q.unit

def test_scalar_unpack(quantity_system, units):
    from measurekit.domain.measurement.quantity import Quantity
    q = Quantity(42.0, units["meter"], system=quantity_system)
    mag, unit = q
    assert mag == 42.0
    assert unit is q.unit

def test_array_iter_unchanged(quantity_system, units):
    """Array __iter__ must still yield individual Quantity elements."""
    import numpy as np
    from measurekit.domain.measurement.quantity import Quantity
    arr = Quantity(np.array([1.0, 2.0, 3.0]), units["meter"], system=quantity_system)
    elements = list(arr)
    assert len(elements) == 3
    assert elements[0].magnitude == pytest.approx(1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/measurement_tests/test_quantity.py::test_m_alias tests/measurement_tests/test_quantity.py::test_u_alias tests/measurement_tests/test_quantity.py::test_scalar_unpack tests/measurement_tests/test_quantity.py::test_array_iter_unchanged -xvs
```

Expected: `test_m_alias` and `test_u_alias` fail with `AttributeError`; `test_scalar_unpack` fails because current `__iter__` raises `TypeError` on scalar; `test_array_iter_unchanged` should PASS (existing behavior).

- [ ] **Step 3: Add `.m` and `.u` properties**

In `quantity.py`, add after the `std_dev` property (search for `def std_dev` and add below its block):

```python
@property
def m(self) -> ValueType:
    """Alias for .magnitude (pint-compatible shorthand)."""
    return self.magnitude

@property
def u(self) -> CompoundUnit:
    """Alias for .unit."""
    return self.unit
```

- [ ] **Step 4: Replace `__iter__` at line ~1043**

Find the existing `__iter__` (line ~1043) and replace it:

```python
# Before:
def __iter__(self):
    """Iterates over elements."""
    # Yield quantities for each element
    # This is slow but correct for iteration
    for i in range(len(self)):
        yield self[i]

# After:
def __iter__(self):
    """Scalar: yields (magnitude, unit) for unpacking. Array: yields elements."""
    try:
        n = len(self.magnitude)
    except TypeError:
        yield self.magnitude
        yield self.unit
        return
    for i in range(n):
        yield self[i]
```

- [ ] **Step 5: Run all four tests**

```bash
uv run pytest tests/measurement_tests/test_quantity.py::test_m_alias tests/measurement_tests/test_quantity.py::test_u_alias tests/measurement_tests/test_quantity.py::test_scalar_unpack tests/measurement_tests/test_quantity.py::test_array_iter_unchanged -xvs
```

Expected: all 4 PASS.

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: all green (no regressions from `__iter__` change).

- [ ] **Step 7: Commit**

```bash
git add measurekit/domain/measurement/quantity.py tests/measurement_tests/test_quantity.py
git commit -m "feat(ergonomics): add .m/.u aliases and scalar unpacking to Quantity"
```

---

## Task 5: Export `UnknownUnitError` from the public API

**Files:**
- Modify: `measurekit/__init__.py`

**Context:** `IncompatibleUnitsError` is importable from `measurekit.domain.exceptions` but not from the top-level `measurekit` package. Users catching errors should be able to `from measurekit import UnknownUnitError`.

- [ ] **Step 1: Write the failing test**

Add to `tests/measurement_tests/test_units.py`:

```python
def test_unknown_unit_error_importable_from_top_level():
    from measurekit import UnknownUnitError  # must not raise
    assert issubclass(UnknownUnitError, ValueError)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_unknown_unit_error_importable_from_top_level -xvs
```

Expected: `ImportError`.

- [ ] **Step 3: Add lazy export in `__init__.py`**

In `measurekit/__init__.py`, inside the `__getattr__` function, add alongside the other exports:

```python
if name == "UnknownUnitError":
    from measurekit.domain.exceptions import UnknownUnitError
    return UnknownUnitError
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_unknown_unit_error_importable_from_top_level -xvs
```

Expected: PASS.

- [ ] **Step 5: Final full suite run**

```bash
uv run pytest tests/ -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add measurekit/__init__.py tests/measurement_tests/test_units.py
git commit -m "feat: export UnknownUnitError from top-level measurekit package"
```

---

## Self-Review

**Spec coverage check:**
- A (error messages): Tasks 1 + 2 — `UnknownUnitError` added, wired with difflib ✓
- B (Jupyter display): Task 3 — `_repr_html_` + `_repr_mimebundle_` ✓
- C (ergonomics): Task 4 — `.m`, `.u`, scalar `__iter__` ✓
- Public API ergonomics: Task 5 — top-level import ✓

**Placeholder scan:** No TBDs, all code blocks complete ✓

**Type consistency:** `UnknownUnitError` name used consistently across Tasks 1, 2, 5 ✓; `.m`/`.u` property names consistent across Task 4 tests and implementation ✓

**`__iter__` collision note:** The existing `__iter__` iterates array elements. The new conditional `__iter__` preserves that for arrays and adds scalar unpacking. `test_array_iter_unchanged` in Task 4 guards the regression ✓
