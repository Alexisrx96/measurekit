use pyo3::prelude::*;
use pyo3::Bound;
use pyo3::PyResult;
use num_rational::Rational64;
use pyo3::types::{PyTuple, PyDict};
use std::collections::HashMap;

use crate::units::RationalUnit;
use crate::uncertainty::{UncertaintyBackend, GaussianBackend, MonteCarloBackend, UnscentedBackend};

#[pyclass(subclass, module = "measurekit_core")]
pub struct Quantity {
    pub value: Box<dyn UncertaintyBackend>,
    pub unit: RationalUnit,
}

impl Clone for Quantity {
    fn clone(&self) -> Self {
        Quantity {
            value: dyn_clone::clone_box(&*self.value),
            unit: self.unit.clone(),
        }
    }
}

#[pymethods]
impl Quantity {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        // 1. Check for Copy Constructor pattern (magnitude=CoreQuantity)
        let mut existing_core = None;
        if args.len() > 0 {
             existing_core = args.get_item(0)?.extract::<Quantity>().ok();
        }
        if existing_core.is_none() {
            if let Some(kw) = kwargs {
                if let Some(mag) = kw.get_item("magnitude").ok().flatten() {
                    existing_core = mag.extract::<Quantity>().ok();
                }
            }
        }
        if let Some(core) = existing_core {
            return Ok(core.clone());
        }

        let mut mean = 0.0;
        let mut std_dev = 0.0;
        let mut unit = None;
        let mut mode = None;
        let mut samples = None;

        // Extract from positional args
        if args.len() > 0 {
            mean = args.get_item(0)?.extract::<f64>()?;
        }
        if args.len() > 1 {
            std_dev = args.get_item(1)?.extract::<f64>()?;
        }
        if args.len() > 2 {
            // Only extract if it's actually a RationalUnit
            unit = args.get_item(2)?.extract::<RationalUnit>().ok();
        }
        if args.len() > 3 {
            mode = args.get_item(3)?.extract::<String>().ok();
        }
        if args.len() > 4 {
            samples = args.get_item(4)?.extract::<usize>().ok();
        }

        // Override with keyword args
        if let Some(kw) = kwargs {
            if let Some(v) = kw.get_item("mean")?.or_else(|| kw.get_item("magnitude").ok().flatten()) {
                // Only extract if it's a float, not a CoreQuantity (already handled above)
                if let Ok(m) = v.extract::<f64>() {
                    mean = m;
                }
            }
            if let Some(v) = kw.get_item("std_dev")?.or_else(|| kw.get_item("uncertainty").ok().flatten()) {
                if let Ok(s) = v.extract::<f64>() {
                    std_dev = s;
                }
            }
            if let Some(v) = kw.get_item("unit")? {
                if let Ok(u) = v.extract::<RationalUnit>() {
                    unit = Some(u);
                }
            }
            if let Some(v) = kw.get_item("mode")? {
                mode = v.extract::<String>().ok();
            }
            if let Some(v) = kw.get_item("samples")? {
                samples = v.extract::<usize>().ok();
            }
        }

        let u = unit.ok_or_else(|| pyo3::exceptions::PyValueError::new_err("unit is required and must be a RationalUnit"))?;

        let backend: Box<dyn UncertaintyBackend> = match mode.as_deref() {
            Some("monte_carlo") => Box::new(MonteCarloBackend::from_stats(mean, std_dev, samples.unwrap_or(1000))),
            Some("unscented") => Box::new(UnscentedBackend::new_scalar(mean, std_dev)),
            _ => Box::new(GaussianBackend { mean, std_dev }),
        };
        Ok(Quantity { value: backend, unit: u })
    }

    #[getter]
    pub fn mean(&self) -> f64 { self.value.mean() }

    #[getter]
    pub fn std_dev(&self) -> f64 { self.value.std_dev() }

    #[getter]
    fn core_unit(&self) -> RationalUnit { self.unit.clone() }

    fn __add__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        if let Ok(other_qi) = other.extract::<Quantity>() {
            if self.unit != other_qi.unit {
                return Err(pyo3::exceptions::PyTypeError::new_err("Unit mismatch"));
            }
            Ok(Quantity { value: self.value.propagate_add(&*other_qi.value), unit: self.unit.clone() })
        } else if let Ok(val) = other.extract::<f64>() {
            let o = GaussianBackend { mean: val, std_dev: 0.0 };
            Ok(Quantity { value: self.value.propagate_add(&o), unit: self.unit.clone() })
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Invalid operand for add"))
        }
    }

    fn __radd__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        self.__add__(other)
    }

    fn __sub__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        if let Ok(other_qi) = other.extract::<Quantity>() {
            if self.unit != other_qi.unit {
                return Err(pyo3::exceptions::PyTypeError::new_err("Unit mismatch"));
            }
            Ok(Quantity { value: self.value.propagate_sub(&*other_qi.value), unit: self.unit.clone() })
        } else if let Ok(val) = other.extract::<f64>() {
            let o = GaussianBackend { mean: val, std_dev: 0.0 };
            Ok(Quantity { value: self.value.propagate_sub(&o), unit: self.unit.clone() })
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Invalid operand for sub"))
        }
    }

    fn __rsub__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        if let Ok(val) = other.extract::<f64>() {
            let o = GaussianBackend { mean: val, std_dev: 0.0 };
            Ok(Quantity { value: o.propagate_sub(&*self.value), unit: self.unit.clone() })
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Invalid operand for rsub"))
        }
    }

    fn __mul__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        if let Ok(other_qi) = other.extract::<Quantity>() {
            Ok(Quantity {
                value: self.value.propagate_mul(&*other_qi.value),
                unit: self.unit.__mul__(&other_qi.unit),
            })
        } else if let Ok(val) = other.extract::<f64>() {
            let o = GaussianBackend { mean: val, std_dev: 0.0 };
            Ok(Quantity { value: self.value.propagate_mul(&o), unit: self.unit.clone() })
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Invalid operand for mul"))
        }
    }

    fn __rmul__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        self.__mul__(other)
    }

    fn __truediv__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        if let Ok(other_qi) = other.extract::<Quantity>() {
            Ok(Quantity {
                value: self.value.propagate_div(&*other_qi.value),
                unit: self.unit.__truediv__(&other_qi.unit),
            })
        } else if let Ok(val) = other.extract::<f64>() {
            let o = GaussianBackend { mean: val, std_dev: 0.0 };
            Ok(Quantity { value: self.value.propagate_div(&o), unit: self.unit.clone() })
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Invalid operand for div"))
        }
    }

    fn __rtruediv__(&self, other: Bound<'_, PyAny>) -> PyResult<Quantity> {
        if let Ok(val) = other.extract::<f64>() {
            let o = GaussianBackend { mean: val, std_dev: 0.0 };
            Ok(Quantity {
                value: o.propagate_div(&*self.value),
                unit: RationalUnit::new(None).__truediv__(&self.unit),
            })
        } else {
            Err(pyo3::exceptions::PyTypeError::new_err("Invalid operand for rtruediv"))
        }
    }

    fn __float__(&self) -> f64 { self.mean() }
    fn __int__(&self) -> i64 { self.mean() as i64 }

    fn __pow__(&self, exponent: f64, _modulo: Option<Bound<'_, PyAny>>) -> PyResult<Quantity> {
        let mut new_dims = HashMap::new();
        let ratio = if exponent.fract() == 0.0 {
             Rational64::new(exponent as i64, 1)
        } else {
             num_rational::Ratio::<i64>::approximate_float(exponent).unwrap_or(num_rational::Ratio::new(0, 1))
        };

        for (base, (num, den)) in &self.unit.dimensions {
            let res = Rational64::new(*num, *den) * ratio;
            if *res.numer() != 0 {
                new_dims.insert(base.clone(), (*res.numer(), *res.denom()));
            }
        }

        Ok(Quantity {
            value: self.value.propagate_pow(exponent),
            unit: RationalUnit { 
                id: RationalUnit::calculate_id(&new_dims), 
                dimensions: new_dims 
            },
        })
    }

    fn __neg__(&self) -> PyResult<Quantity> {
        let neg_one = GaussianBackend { mean: -1.0, std_dev: 0.0 };
        Ok(Quantity { 
            value: self.value.propagate_mul(&neg_one), 
            unit: self.unit.clone() 
        })
    }

    fn __pos__(&self) -> Quantity {
        self.clone()
    }

    fn __abs__(&self) -> Quantity {
        self.propagate_function("abs".to_string())
    }

    fn propagate_function(&self, func: String) -> Quantity {
        Quantity {
            value: self.value.propagate_function(&func),
            unit: self.unit.clone(),
        }
    }

    pub fn to_unit(&self, target_unit: RationalUnit, factor: f64) -> Quantity {
        Quantity {
            value: self.value.propagate_mul(&GaussianBackend { mean: factor, std_dev: 0.0 }),
            unit: target_unit,
        }
    }

    fn __repr__(&self) -> String {
        format!("{:.4} +/- {:.4} {}", self.mean(), self.std_dev(), self.unit.__repr__())
    }
}
