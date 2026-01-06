import numpy as np

from tests.strategies import linear_units, same_unit_quantities


# Mocking the test function
def check_commutativity(qs):
    a, b = qs
    try:
        res1 = a + b
        res2 = b + a
    except (ValueError, RuntimeError):
        return  # Skip

    try:
        # Check magnitude
        m1 = res1.magnitude
        m2 = res2.magnitude

        # Convert to numpy if needed
        if hasattr(m1, "cpu"):
            m1 = m1.cpu().numpy()
        if hasattr(m2, "cpu"):
            m2 = m2.cpu().numpy()
        if hasattr(m1, "__array__"):
            m1 = np.array(m1)
        if hasattr(m2, "__array__"):
            m2 = np.array(m2)

        if not np.allclose(m1, m2, rtol=1e-5, atol=1e-8):
            print(f"Mismatch: a={a}, b={b}")
            print(f"res1={res1.magnitude}, res2={res2.magnitude}")
            raise AssertionError("Magnitude Mismatch")

        if res1.unit != res2.unit:
            print(f"Unit Mismatch: a={a}, b={b}")
            raise AssertionError("Unit Mismatch")

    except Exception as e:
        print(f"Caught: {e}")
        raise e


# Validating the strategy
if __name__ == "__main__":
    from hypothesis import find

    print("Searching for failure...")
    try:
        # We try to find an example that raises AssertionError
        find(
            same_unit_quantities(n=2, unit_strategy=linear_units()),
            lambda qs: check_commutativity(qs),
        )
    except Exception as e:
        print(f"Found falsifying example: {e}")
