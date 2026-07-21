use std::fmt;
use crate::quantity::Quantity;

#[derive(Debug, Clone, PartialEq)]
pub enum PhsValue {
    None,
    Number(f64),
    Quantity(Quantity),
    Bool(bool),
    String(String),
    Vector(Vec<PhsValue>),
}

impl fmt::Display for PhsValue {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PhsValue::None => write!(f, ""),
            PhsValue::Number(n) => write!(f, "{}", n),
            PhsValue::Quantity(q) => write!(f, "{}", q),
            PhsValue::Bool(b) => write!(f, "{}", if *b { "true" } else { "false" }),
            PhsValue::String(s) => write!(f, "{}", s),
            PhsValue::Vector(v) => {
                let items: Vec<String> = v.iter().map(|item| item.to_string()).collect();
                write!(f, "[{}]", items.join(", "))
            }
        }
    }
}
