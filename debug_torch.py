import torch

from measurekit import Quantity, get_unit

# Force load torch backend
from measurekit.core.dispatcher import BackendManager

BackendManager._get_or_load_backend("torch")

try:
    u = get_unit("m")
    # Test scalar addition
    a = Quantity.from_input(torch.tensor(1.0), u, None)
    b = Quantity.from_input(torch.tensor(2.0), u, None)
    res = a + b
    print(f"Scalar Add Success: {res}")

    # Test array addition
    a_arr = Quantity.from_input(torch.tensor([1.0, 2.0]), u, None)
    b_arr = Quantity.from_input(torch.tensor([3.0, 4.0]), u, None)
    res_arr = a_arr + b_arr
    print(f"Array Add Success: {res_arr}")

    # Test int/float mixing
    a_f = Quantity.from_input(torch.tensor(1.0, dtype=torch.float64), u, None)
    b_f = Quantity.from_input(torch.tensor(2.0, dtype=torch.float32), u, None)
    res_mix = a_f + b_f
    print(f"Mix Add Success: {res_mix}")

except Exception as e:
    print(f"FAILURE: {e}")
    import traceback

    traceback.print_exc()
