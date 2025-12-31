import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

# Ensure measurekit is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pint

from measurekit import Quantity, u

# Setup Pint for comparison
ureg = pint.UnitRegistry()


def run_benchmarks():
    """Run performance benchmarks comparing MeasureKit with competitors."""
    N = 1_000_000
    iterations = 10
    print(f"Benchmarking with N = {N}, {iterations} iterations...")

    # Pre-allocate data
    arr_np = np.ones(N)

    # --- Contestants Setup ---

    # 1. Pint (The Competitor)
    q_pint = arr_np * ureg.meter

    def pint_task():
        # Sum 1M meters and convert to km
        return q_pint.sum().to("kilometer")

    # 2. MeasureKit + NumPy (Baseline)
    q_mk = Quantity(arr_np, u.m)

    def mk_numpy_task():
        sum_mag = q_mk.magnitude.sum()
        return Quantity(sum_mag, u.m).to(u.km)

    # 3. Pure NumPy (The Speed Limit - No Units)
    def numpy_task():
        return arr_np.sum() / 1000.0

    # 4. MeasureKit + Numba
    mk_numba_task = None
    try:
        # Numba activation
        from numba import NumbaError, TypingError, njit

        import measurekit.ext.numba_support

        @njit
        def numba_sum_op(q):
            # Access magnitude (NumPy array) directly inside the loop
            # Overloads for len() and getitem on Quantity are not implemented, only .magnitude
            mag = q.magnitude
            acc = 0.0
            for i in range(len(mag)):
                acc += mag[i]
            return acc / 1000.0

        # Try warmup - catch RecursionError if it persists
        try:
            numba_sum_op(q_mk)
            print("Numba compiled successfully!")

            def mk_numba_task():
                return numba_sum_op(q_mk)
        except (RecursionError, TypingError, NumbaError) as e:
            print(f"Skipping Numba benchmark due to compilation error: {e}")

    except ImportError:
        print("Numba not installed.")

    # 5. MeasureKit + JAX
    mk_jax_task = None
    try:
        import os

        import jax.numpy as jnp
        from jax import jit
        # Use CPU to be fair against numpy/pint if GPU not avail

        q_jax = Quantity(jnp.ones(N), u.m)

        @jit
        def jax_sum_op(q):
            return q.magnitude.sum() / 1000.0

        # Warmup JAX
        try:
            jax_sum_op(q_jax).block_until_ready()

            def mk_jax_task():
                return jax_sum_op(q_jax).block_until_ready()
        except:
            print("JAX failed warmup")
    except ImportError:
        print("JAX not found.")

    # --- Execution ---
    all_tasks = {
        "Pint": pint_task,
        "MeasureKit (NumPy)": mk_numpy_task,
        "Pure NumPy": numpy_task,
    }
    if mk_numba_task:
        all_tasks["MeasureKit (Numba)"] = mk_numba_task
    if mk_jax_task:
        all_tasks["MeasureKit (JAX)"] = mk_jax_task

    results = {}
    for name, task in all_tasks.items():
        print(f"   Executing {name}...")
        try:
            task()
            start = time.perf_counter()
            for _ in range(iterations):
                task()
            avg_time = (time.perf_counter() - start) / iterations
            results[name] = avg_time
            print(f"      Mean: {avg_time * 1000:.4f} ms")
        except Exception as e:
            print(f"      Failed: {e}")

    # --- Visualization ---
    if not results:
        print("No results to plot.")
        return

    names = sorted(results.keys(), key=lambda x: results[x], reverse=True)
    times_ms = [results[n] * 1000 for n in names]

    plt.figure(figsize=(10, 6), dpi=100)
    colors = []
    for n in names:
        if "Pint" in n:
            colors.append("#e74c3c")  # Red
        elif "Numba" in n:
            colors.append("#f1c40f")  # Yellow
        elif "JAX" in n:
            colors.append("#9b59b6")  # Purple
        elif "MeasureKit" in n:
            colors.append("#2ecc71")  # Green
        else:
            colors.append("#95a5a6")  # Gray

    bars = plt.bar(names, times_ms, color=colors, edgecolor="black", alpha=0.8)
    plt.yscale("log")
    plt.ylabel("Execution Time (ms) - Log Scale")
    plt.title(
        "Performance Benchmark: Sum & Convert (1M Elements)", fontsize=14
    )
    plt.grid(True, which="both", ls="-", alpha=0.1)

    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            yval * 1.1,
            f"{yval:.2f}",
            va="bottom",
            ha="center",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig("benchmark_results.png")
    print("\nBenchmark complete. Saved to 'benchmark_results.png'.")


if __name__ == "__main__":
    run_benchmarks()
