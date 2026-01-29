import numpy as np
import pyarrow as pa
import pyarrow.ipc

from measurekit_core import CovarianceStore


def test_covariance_to_arrow():
    print("Testing CovarianceStore.to_arrow()...")

    store = CovarianceStore()
    print("CovarianceStore members:", dir(store))

    # ID 1: Variance = 1.0 (Scalar)
    var1 = np.array([1.0])
    store.register_variable(1, var1)

    # ID 2: Variance = 4.0 (Scalar)
    var2 = np.array([4.0])
    store.register_variable(2, var2)

    # Propagate to create correlation (1 -> 3)
    # J = 2.0
    jacobians = [np.array([2.0])]
    store.propagate(3, [1], jacobians)

    # Verify we have blocks: (1,1), (2,2), (3,3), (1,3)
    # Note: propagate creates (3,3) and possibly (1,3)

    arrow_bytes = store.to_arrow()
    print(f"Arrow bytes length: {len(arrow_bytes)}")

    reader = pa.ipc.open_stream(arrow_bytes)
    batch = reader.read_next_batch()

    df = batch.to_pandas()
    print("\nDecoded Pandas DataFrame:")
    print(df)

    # Check structure
    assert "row_id" in df.columns
    assert "col_id" in df.columns
    assert "data" in df.columns
    assert "indices" in df.columns
    assert "indptr" in df.columns

    # Verify data content
    # We expect block (1,1) -> data=[1.0]
    row1 = df[(df.row_id == 1) & (df.col_id == 1)]
    assert len(row1) == 1
    np.testing.assert_array_equal(row1.iloc[0]["data"], [1.0])

    # Verify block (3,3) -> Variance = J * Var1 * J^T = 2 * 1 * 2 = 4.0
    row3 = df[(df.row_id == 3) & (df.col_id == 3)]
    assert len(row3) == 1
    np.testing.assert_array_equal(row3.iloc[0]["data"], [4.0])

    # Verify cross-block (1,3) -> Cov = Var1 * J^T = 1 * 2 = 2.0
    # Store sorts keys, so checking 1,3 or 3,1
    row13 = df[
        ((df.row_id == 1) & (df.col_id == 3))
        | ((df.row_id == 3) & (df.col_id == 1))
    ]
    assert len(row13) == 1
    np.testing.assert_array_equal(row13.iloc[0]["data"], [2.0])

    print("\nTest passed!")


if __name__ == "__main__":
    test_covariance_to_arrow()
