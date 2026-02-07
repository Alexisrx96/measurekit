# Phase 4: CI/CD Pipeline — Overview

← [Back to Master Plan](../00_MASTER_PLAN.md)

**Status:** 🔴 Not Started  
**Priority:** P3 (Low — Build after core is stable)

---

## Objectives

1. Automated testing across Python versions
2. WASM build and release pipeline
3. Documentation generation
4. Performance regression tracking

---

## Current CI Status

Check `.github/workflows/` for existing configuration.

---

## Target Pipeline

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - run: pytest tests/ -v

  rust-test:
    runs-on: ubuntu-latest
    steps:
      - run: cargo test --manifest-path measurekit_core/Cargo.toml

  wasm-build:
    runs-on: ubuntu-latest
    steps:
      - uses: maturin-action/action@v1
        with:
          target: wasm32-unknown-emscripten
          args: --release --out dist

  docs:
    runs-on: ubuntu-latest
    steps:
      - run: mkdocs build
      - uses: actions/upload-pages-artifact@v2

  benchmark:
    runs-on: ubuntu-latest
    steps:
      - run: pytest benchmarks/ --benchmark-json=output.json
      - uses: benchmark-action/github-action-benchmark@v1
```

---

## Release Workflow

```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ["v*"]

jobs:
  build-wheels:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: pypa/cibuildwheel@v2

  build-wasm:
    # Build WASM wheel

  publish:
    needs: [build-wheels, build-wasm]
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
```

---

## Tasks (Future)

1. Set up GitHub Actions matrix build
2. Configure `cibuildwheel` for native wheels
3. Add WASM build to release pipeline
4. Performance benchmark tracking
5. Auto-generate API docs from docstrings
