import pickle
import tempfile
from pathlib import Path

import numpy as np

import measurekit as mk
from measurekit.core.dispatcher import BackendManager
from measurekit.domain.measurement.vectorized_uncertainty import (
    clear_global_stores,
    ensure_store,
)


def test_save_load_state(tmp_path):
    print("Starting manual state test...")
    val = np.array([1.0, 2.0])
    backend = BackendManager.get_backend(val)

    # clear globals first
    clear_global_stores()

    store_a = ensure_store(backend)
    slc_a = store_a.register_independent_array(val)

    print("Store created. Config type:", type(store_a.config))
    try:
        pc_dump = pickle.dumps(store_a.config)
        print(f"Explicit PruningConfig pickle OK. Size: {len(pc_dump)}")
    except Exception as e:
        print("Explicit PruningConfig pickle FAIL:", e)

    try:
        store_dump = pickle.dumps(store_a)
        print(f"Explicit CovarianceStore pickle OK. Size: {len(store_dump)}")
    except Exception as e:
        print("Explicit CovarianceStore pickle FAIL:", e)

    state_file = tmp_path / "measurekit_state.pkl"
    print("Saving state via mk.save_state...")
    try:
        mk.save_state(state_file)
        print("State saved.")
    except Exception as e:
        print("Save failed:", e)
        raise

    clear_global_stores()
    print("Globals cleared. Loading state...")
    mk.load_state(state_file)
    print("State loaded.")

    store_restored = ensure_store(backend)
    block_restored = store_restored.get_covariance_block(slc_a, slc_a)

    print("Restored Block:\n", block_restored.toarray())

    print("Manual test finished.")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_save_load_state(Path(tmp_dir))
