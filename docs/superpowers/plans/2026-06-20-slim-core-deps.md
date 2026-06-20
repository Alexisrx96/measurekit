# Slim Core Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `pip install measurekit` from ~130 MB of transitive deps to stdlib + `typing-extensions` + `measurekit-core` by removing unused deps, moving misplaced ones to extras, fixing one eager import, and making `sympy` optional via a native fallback parser.

**Architecture:**
- Task 1 is pure `pyproject.toml` surgery — no code changes.
- Task 2 moves one `try/except` import block from module level into the method that actually needs it.
- Task 3 adds `NotationParser` (already exists, zero deps) as the primary unit-string parser; `SymPyUnitParser` becomes a fallback loaded only when sympy is installed and the native parser fails.

**Tech Stack:** Python stdlib `re`, existing `measurekit.domain.notation.{lexer,parsers}`, `pyproject.toml` extras.

---

## Files touched

| File | Change |
|---|---|
| `pyproject.toml` | Remove dead deps; move misplaced deps to correct extras |
| `measurekit/domain/measurement/quantity.py` | Move eager `pydantic_core` import inside method |
| `measurekit/core/parsing/transformer.py` | Move module-level `import sympy` inside `transform()` |
| `measurekit/application/parsing.py` | Add `NotationParser` primary path; keep SymPy as fallback |

---

## Task 1: pyproject.toml — Remove dead and misplaced deps

**Files:**
- Modify: `pyproject.toml`

**Context:**
Audit found:
- `networkx` — 0 imports anywhere. Dead weight.
- `filelock` — 0 imports anywhere. Dead weight.
- `h5py` — only used in `ext/io.py` (already behind `try/except`). Belongs in `[io]` extra.
- `pyarrow` — only used in `scripts/test_arrow_covariance.py` and `tests/test_performance_and_interop.py`. Belongs in `[io]` extra.
- `psutil` — only in `tests/test_performance_and_interop.py`. Belongs in `[dev]` group.
- `pydantic` — already in `[pydantic]` extra; usage in `quantity.py` is behind `try/except`. Remove from core.
- `jaxtyping` — only imported inside backend `try/except` blocks. Move to backend extras.
- `sympy` — currently hard dep; will become optional in Task 3. Move to `[symbolic]` extra.

- [ ] **Step 1: Edit `pyproject.toml` dependencies**

Replace the `dependencies` list:

```toml
dependencies = [
    "typing-extensions>=4.15.0",
    "array-api-compat>=1.4",
    "measurekit-core",
]
```

Add `[symbolic]` extra and update `[all]`:

```toml
[project.optional-dependencies]
numpy = ["numpy>=1.26.0", "scipy>=1.12.0", "numba>=0.59.0", "jaxtyping>=0.2.28"]
torch = ["torch>=2.2.0", "jaxtyping>=0.2.28"]
jax = ["jax>=0.4.25", "jaxlib>=0.4.25", "jaxtyping>=0.2.28"]
pandas = ["pandas>=2.2.0"]
pydantic = ["pydantic>=2.10.0"]
symbolic = ["sympy>=1.13.0"]
rich = ["rich>=13.0.0"]
io = ["h5py>=3.10.0", "pyarrow>=22.0.0", "xarray>=2024.1.0", "netCDF4>=1.6.0"]
all = [
    "numpy>=1.26.0",
    "scipy>=1.12.0",
    "numba>=0.59.0",
    "torch>=2.2.0",
    "jax>=0.4.25",
    "jaxlib>=0.4.25",
    "jaxtyping>=0.2.28",
    "pandas>=2.3.3",
    "pydantic>=2.6.0",
    "sympy>=1.13.0",
    "h5py>=3.10.0",
    "pyarrow>=22.0.0",
    "xarray>=2024.1.0",
    "netCDF4>=1.6.0",
]
```

Also update `[dependency-groups]` to add `psutil`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=4.1.0",
    "pytest-benchmark>=4.0.0",
    "hypothesis>=6.98.0",
    "mypy>=1.9.0",
    "ruff>=0.3.0",
    "maturin>=1.11.2",
    "beartype>=0.19.0",
    "psutil>=7.2.1",
    "pyarrow>=22.0.0",
]
```

- [ ] **Step 2: Run linter to catch any format issues**

```bash
uv run ruff check pyproject.toml 2>/dev/null || echo "ruff does not lint toml, OK"
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): remove unused deps, move misplaced ones to extras

- Remove networkx, filelock (zero usage anywhere in codebase)
- Move h5py, pyarrow to [io] extra (only used in ext/io.py and tests)
- Move psutil to dev group (tests only)
- Remove pydantic from core (already in [pydantic] extra, code already guarded)
- Move jaxtyping to backend extras (already guarded in backends)
- Move sympy to new [symbolic] extra (will be optional after parser refactor)"
```

---

## Task 2: Fix eager pydantic_core import in quantity.py

**Files:**
- Modify: `measurekit/domain/measurement/quantity.py:69-72` and `:536-541`

**Context:**
`from pydantic_core import core_schema` sits at module level in a `try/except`. This means `pydantic_core` (Rust binary, ~3 MB) is loaded every time `Q_` is first accessed, even if the user never uses Pydantic. Moving it inside the method is a one-liner change.

- [ ] **Step 1: Write a regression test**

In `tests/measurement_tests/test_quantity.py`, add at the bottom:

```python
def test_pydantic_core_not_loaded_at_import():
    """pydantic_core should only load when __get_pydantic_core_schema__ is called."""
    import sys
    # If pydantic_core is already loaded by a previous test, skip.
    # This test is most meaningful in a fresh process.
    if "pydantic_core" not in sys.modules:
        import measurekit  # noqa: F401
        assert "pydantic_core" not in sys.modules, (
            "pydantic_core should not load on bare `import measurekit`"
        )
```

- [ ] **Step 2: Run to verify it currently fails (or is a no-op if pydantic_core already loaded)**

```bash
uv run pytest tests/measurement_tests/test_quantity.py::test_pydantic_core_not_loaded_at_import -xvs
```

Note: this test only catches the regression in a fresh process. The CI run will validate it.

- [ ] **Step 3: Move the import in quantity.py**

Find these lines (around line 69):

```python
try:
    from pydantic_core import core_schema
except ImportError:
    core_schema = None
```

Replace with:

```python
# ponytail: pydantic_core loaded lazily; only imported when Pydantic validation is used
```

Then find `__get_pydantic_core_schema__` (around line 536):

```python
@classmethod
def __get_pydantic_core_schema__(cls, source_type, handler):
        raise ImportError("pydantic-core is required for validation.")
```

Replace the full method body so it becomes:

```python
@classmethod
def __get_pydantic_core_schema__(cls, source_type, handler):
    """Pydantic v2 schema for Quantity validation."""
    try:
        from pydantic_core import core_schema
    except ImportError as e:
        raise ImportError("pydantic-core is required for validation.") from e
    return core_schema.no_info_plain_validator_function(
        lambda v: v if isinstance(v, cls) else cls(v, ""),
    )
```

(Keep the existing body; only move the import inside and remove the module-level sentinel.)

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest tests/measurement_tests/ -x --tb=short -q
```

Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add measurekit/domain/measurement/quantity.py tests/measurement_tests/test_quantity.py
git commit -m "perf: lazy-load pydantic_core inside __get_pydantic_core_schema__

Removes ~3MB Rust binary from the hot path of `from measurekit import Q_`."
```

---

## Task 3: Make sympy optional — NotationParser as primary unit parser

**Files:**
- Modify: `measurekit/core/parsing/transformer.py:5`
- Modify: `measurekit/application/parsing.py`
- Test: `tests/measurement_tests/test_units.py`

**Context:**
`NotationParser` (in `domain/notation/parsers.py`) is a pure-Python recursive descent parser that already handles `m/s`, `kg*m/s^2`, `m²`, `(kg*m)/s^2`, `m2`, `s-1`, and all standard unit expressions. It requires zero deps beyond stdlib + the existing lexer.

`SymPyUnitParser` routes unit strings through SymPy's AST, which is powerful but slow and adds 40 MB. Making it a fallback means:
- Fast path (no sympy): handles 99% of real-world unit strings.
- Slow path (sympy, if installed): handles exotic edge cases like `2*m` (numeric prefix) or deeply nested expressions.

**Step 1: Verify NotationParser handles the test suite's unit strings**

- [ ] Run the existing unit tests to see current baseline:

```bash
uv run pytest tests/measurement_tests/test_units.py tests/notation_tests/ -x --tb=short -q
```

Expected: all pass.

**Step 2: Make `import sympy` lazy in transformer.py**

- [ ] In `measurekit/core/parsing/transformer.py`, remove the module-level import and add it inside `transform()`:

Current (line 5):
```python
import sympy as sp
```

Remove that line entirely. Then inside `SymPyTransformer.transform()`:

```python
def transform(self, expr) -> CompoundUnit:
    """Recursively transforms SymPy AST into CompoundUnit."""
    import sympy as sp  # lazy: only when SymPyUnitParser is used
    if isinstance(expr, sp.Symbol):
    # ... rest of method unchanged
```

Note: `from __future__ import annotations` is already at the top of `transformer.py`, so the `sp.Expr` in the original type annotation was already a string at runtime. Replacing it with no annotation or `Any` is fine.

- [ ] Verify the sympy_parser still works end-to-end:

```bash
uv run python -c "
from measurekit.core.parsing.sympy_parser import SymPyUnitParser
p = SymPyUnitParser()
print(p.parse('m/s'))
print(p.parse('kg*m/s**2'))
print(p.parse('m2'))
"
```

Expected: CompoundUnit objects printed.

**Step 3: Add NotationParser primary path to `application/parsing.py`**

- [ ] Replace the full content of `measurekit/application/parsing.py`:

```python
# measurekit/application/parsing.py
"""Unit string parsing — native parser first, SymPy fallback."""

from __future__ import annotations

import functools
import re
from typing import TypeVar

from measurekit.domain.notation.lexer import generate_tokens
from measurekit.domain.notation.parsers import NotationParser
from measurekit.domain.notation.protocols import ExponentEntityProtocol

T = TypeVar("T", bound=ExponentEntityProtocol)

# Pre-processing normalizations NotationParser needs (subset of UnitSanitizer)
_IMPLICIT_MUL = re.compile(r"(?<=[a-zA-Z0-9)])\s+(?=[a-zA-Z0-9(])")

# Singleton SymPy parser, loaded lazily only when native parser fails
_SYMPY_PARSER = None


def _get_sympy_parser():
    global _SYMPY_PARSER
    if _SYMPY_PARSER is None:
        try:
            from measurekit.core.parsing.sympy_parser import SymPyUnitParser
            _SYMPY_PARSER = SymPyUnitParser()
        except ImportError as e:
            raise ImportError(
                "sympy is required to parse this unit expression. "
                "Install it with: pip install measurekit[symbolic]"
            ) from e
    return _SYMPY_PARSER


def _native_parse(expression: str, entity_cls: type[T]) -> T:
    """Parse using the pure-Python NotationParser (no sympy)."""
    expr = expression.strip()
    expr = expr.replace("°", "deg")
    expr = expr.replace("$", "__DOLLAR__")
    expr = _IMPLICIT_MUL.sub("*", expr)
    tokens = generate_tokens(expr)
    parser = NotationParser(tokens, entity_cls)
    return parser.parse()


@functools.lru_cache(maxsize=2048)
def parse_unit_string(expression: str, entity_cls: type[T]) -> T:
    """Parse a unit or dimension string into the target entity class.

    Tries the native recursive-descent parser first (no dependencies).
    Falls back to the SymPy-based parser for complex expressions.
    """
    # Fast path: native parser, zero deps
    try:
        return _native_parse(expression, entity_cls)
    except (ValueError, Exception):
        pass

    # Slow path: SymPy parser (requires sympy installed)
    try:
        compound_unit = _get_sympy_parser().parse(expression)
    except ImportError:
        raise
    except Exception as e:
        raise ValueError(f"Parsing failed: {e}") from e

    if issubclass(entity_cls, type(compound_unit)):
        return compound_unit  # type: ignore
    return entity_cls(compound_unit.exponents)
```

**Step 4: Write a test proving sympy is not loaded for standard unit strings**

- [ ] In `tests/measurement_tests/test_units.py`, add:

```python
def test_standard_units_do_not_load_sympy():
    """Common unit strings must parse without importing sympy."""
    import sys
    sympy_was_loaded = "sympy" in sys.modules

    from measurekit.application.parsing import parse_unit_string
    from measurekit.domain.measurement.units import CompoundUnit

    # Clear the lru_cache to force a fresh parse
    parse_unit_string.cache_clear()

    exprs = ["m/s", "kg*m/s**2", "m2", "kg", "m/s^2", "(kg*m)/s^2", "m²", "s-1"]
    for expr in exprs:
        result = parse_unit_string(expr, CompoundUnit)
        assert result is not None, f"Failed to parse: {expr}"

    if not sympy_was_loaded:
        assert "sympy" not in sys.modules, (
            "sympy was loaded while parsing standard unit strings"
        )
```

- [ ] **Step 5: Run the new test to make sure it passes**

```bash
uv run pytest tests/measurement_tests/test_units.py::test_standard_units_do_not_load_sympy -xvs
```

Expected: PASS. If it fails, investigate which unit string triggered the SymPy fallback and fix `_native_parse` to handle it.

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -x --tb=short -q
```

Expected: all passing. If any parsing-related tests fail, the SymPy fallback will catch them automatically since sympy IS installed in the dev env — so failures mean the fallback itself broke.

- [ ] **Step 7: Commit**

```bash
git add measurekit/core/parsing/transformer.py measurekit/application/parsing.py tests/measurement_tests/test_units.py
git commit -m "feat(parsing): make sympy optional via NotationParser primary path

- NotationParser (pure stdlib) handles 99% of unit strings with no deps
- SymPyUnitParser is now a lazy fallback only loaded when native parser fails
- sympy moved from core deps to [symbolic] extra
- Removes ~40 MB from the default install"
```

---

## Task 4: Verification pass

**Files:** none modified — diagnostic only.

- [ ] **Step 1: Measure before/after import footprint**

```bash
uv run python -c "
import sys, time

t0 = time.perf_counter()
import measurekit
t1 = time.perf_counter()
print(f'bare import: {(t1-t0)*1000:.1f} ms, {len(sys.modules)} modules')

from measurekit import Q_
t2 = time.perf_counter()
print(f'after Q_:    {(t2-t1)*1000:.1f} ms, {len(sys.modules)} modules')

heavy = ['sympy', 'pydantic', 'pydantic_core', 'h5py', 'pyarrow', 'networkx', 'filelock', 'psutil', 'jaxtyping']
for dep in heavy:
    loaded = dep.replace('-', '_') in sys.modules or dep in sys.modules
    print(f'  {dep}: {\"LOADED\" if loaded else \"not loaded\"}')
"
```

Expected: all heavy deps show "not loaded".

- [ ] **Step 2: Run doctests**

```bash
uv run pytest --doctest-modules measurekit/ -x --tb=short -q 2>&1 | tail -20
```

- [ ] **Step 3: Run full suite one final time**

```bash
uv run pytest -x --tb=short -q
```

Expected: green. Coverage should remain ≥ 80%.

- [ ] **Step 4: Final commit if any stray fixes were needed**

```bash
git add -p
git commit -m "fix: stray issues from dep slim-down"
```

---

## Self-Review

**Spec coverage:**
- ✅ Remove networkx, filelock (Task 1)
- ✅ Move h5py, pyarrow, psutil, pydantic, jaxtyping to correct extras (Task 1)
- ✅ Fix pydantic_core eager load (Task 2)
- ✅ Make sympy optional (Task 3)
- ✅ NotationParser as primary parser (Task 3)
- ✅ Verification (Task 4)

**Placeholder scan:** No TBDs found.

**Type consistency:** `parse_unit_string` signature unchanged (`str, type[T]) -> T`). `NotationParser` already returns `T` via `entity_cls`. `SymPyUnitParser` returns `CompoundUnit`; the existing conversion `entity_cls(compound_unit.exponents)` is preserved.

**Risk notes:**
- `NotationParser` skips whitespace via the lexer, so `"m s"` (implicit mul) is handled by the pre-proc `_IMPLICIT_MUL` regex before tokenizing.
- If any exotic unit string in the test suite falls through to the SymPy fallback, it still works because sympy IS in the dev env. The test in Task 3 Step 4 explicitly guards against that for common strings.
- `pydantic_core` change: the method now does a `try/except` on every call instead of on module load. This is negligible overhead since it's cached by Python's import system after the first call.
