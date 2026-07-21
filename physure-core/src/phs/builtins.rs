use crate::error::{PhysureError, PhysureResult};
use super::value::PhsValue;

pub fn eval_builtin(name: &str, args: &[PhsValue]) -> PhysureResult<Option<PhsValue>> {
    match name {
        "sqrt" => {
            if args.len() != 1 {
                return Err(PhysureError::Generic("sqrt expects 1 argument".into()));
            }
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number(n.sqrt()))),
                PhsValue::Quantity(q) => Ok(Some(PhsValue::Quantity(q.sqrt()?))),
                _ => Err(PhysureError::Generic("sqrt expects a number or quantity".into())),
            }
        }
        "sin" => {
            if args.len() != 1 {
                return Err(PhysureError::Generic("sin expects 1 argument".into()));
            }
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number(n.sin()))),
                PhsValue::Quantity(q) => Ok(Some(PhsValue::Number(q.value.mean().sin()))),
                _ => Err(PhysureError::Generic("sin expects a number".into())),
            }
        }
        "cos" => {
            if args.len() != 1 {
                return Err(PhysureError::Generic("cos expects 1 argument".into()));
            }
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number(n.cos()))),
                PhsValue::Quantity(q) => Ok(Some(PhsValue::Number(q.value.mean().cos()))),
                _ => Err(PhysureError::Generic("cos expects a number".into())),
            }
        }
        "exp" => {
            if args.len() != 1 {
                return Err(PhysureError::Generic("exp expects 1 argument".into()));
            }
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number(n.exp()))),
                _ => Err(PhysureError::Generic("exp expects a number".into())),
            }
        }
        "ln" => {
            if args.len() != 1 {
                return Err(PhysureError::Generic("ln expects 1 argument".into()));
            }
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number(n.ln()))),
                _ => Err(PhysureError::Generic("ln expects a number".into())),
            }
        }
        "abs" => {
            if args.len() != 1 {
                return Err(PhysureError::Generic("abs expects 1 argument".into()));
            }
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number(n.abs()))),
                _ => Err(PhysureError::Generic("abs expects a number".into())),
            }
        }
        "round" => {
            if args.is_empty() {
                return Err(PhysureError::Generic("round expects arguments".into()));
            }
            let decimals = match args.get(1) {
                Some(PhsValue::Number(d)) => *d as i32,
                _ => 0,
            };
            let factor = 10.0f64.powi(decimals);
            match &args[0] {
                PhsValue::Number(n) => Ok(Some(PhsValue::Number((n * factor).round() / factor))),
                PhsValue::Quantity(q) => {
                    use crate::quantity::Quantity;
                    let rounded = Quantity::new_scalar(
                        (q.value.mean() * factor).round() / factor,
                        0.0,
                        q.unit.clone(),
                        None,
                        None,
                    );
                    Ok(Some(PhsValue::Quantity(rounded)))
                }
                _ => Err(PhysureError::Generic("round expects number or quantity".into())),
            }
        }
        "linspace" => {
            if args.len() < 2 {
                return Err(PhysureError::Generic("linspace expects start and stop".into()));
            }
            let start = match &args[0] {
                PhsValue::Number(n) => *n,
                PhsValue::Quantity(q) => q.value.mean(),
                _ => 0.0,
            };
            let stop = match &args[1] {
                PhsValue::Number(n) => *n,
                PhsValue::Quantity(q) => q.value.mean(),
                _ => 1.0,
            };
            let count = if args.len() >= 3 {
                match &args[2] {
                    PhsValue::Number(n) => *n as usize,
                    _ => 50,
                }
            } else {
                50
            };
            let step = if count > 1 { (stop - start) / (count - 1) as f64 } else { 0.0 };
            let vec: Vec<PhsValue> = (0..count)
                .map(|i| PhsValue::Number(start + i as f64 * step))
                .collect();
            Ok(Some(PhsValue::Vector(vec)))
        }
        "plot" => Ok(Some(PhsValue::String("[PLOT]".to_string()))),
        _ => Ok(None),
    }
}
