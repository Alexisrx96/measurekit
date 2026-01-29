import numpy as np

from measurekit.backends.numpy_backend import NumpyBackend
from measurekit.core.dispatcher import (
    ensure_backend_compatible,
)


class MockBackend(NumpyBackend):
    @ensure_backend_compatible
    def add(self, x, y):
        # x and y should be arrays now if they were lists
        if isinstance(x, list):
            raise TypeError("x is list")
        if isinstance(y, list):
            raise TypeError("y is list")
        return x + y


def test_decorator():
    backend = MockBackend()

    # Test list + list -> array + array
    res = backend.add([1, 2], [3, 4])
    assert isinstance(res, np.ndarray)
    assert np.all(res == np.array([4, 6]))
    print("Mixed input check passed.")


if __name__ == "__main__":
    test_decorator()
