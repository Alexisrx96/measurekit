use std::collections::HashMap;
use crate::error::{PhysureError, PhysureResult};
use crate::units::UnitRegistry;
use super::ast::{BinaryOp, Expr, ParamDef, Statement, UnaryOp};
use super::builtins::eval_builtin;
use super::value::PhsValue;

#[derive(Debug, Clone)]
pub struct UserFn {
    pub params: Vec<ParamDef>,
    pub body: Vec<Statement>,
}

pub struct PhsInterpreter {
    env: HashMap<String, PhsValue>,
    functions: HashMap<String, UserFn>,
    registry: UnitRegistry,
}

impl Default for PhsInterpreter {
    fn default() -> Self {
        Self::new()
    }
}

impl PhsInterpreter {
    pub fn new() -> Self {
        Self {
            env: HashMap::new(),
            functions: HashMap::new(),
            registry: UnitRegistry::build_default_si(),
        }
    }

    pub fn with_registry(registry: UnitRegistry) -> Self {
        Self {
            env: HashMap::new(),
            functions: HashMap::new(),
            registry,
        }
    }

    pub fn get_var(&self, name: &str) -> Option<&PhsValue> {
        self.env.get(name)
    }

    pub fn set_var(&mut self, name: impl Into<String>, val: PhsValue) {
        self.env.insert(name.into(), val);
    }

    pub fn run_statement(&mut self, stmt: &Statement) -> PhysureResult<PhsValue> {
        match stmt {
            Statement::Assign { name, expr } => {
                let val = self.eval_expr(expr)?;
                self.env.insert(name.clone(), val);
                Ok(PhsValue::None)
            }
            Statement::Query { expr } => self.eval_expr(expr),
            Statement::Convert { expr, target_unit: _ } => self.eval_expr(expr),
            Statement::Format { expr, spec: _ } => self.eval_expr(expr),
            Statement::AssignAndQuery { name, expr } => {
                let val = self.eval_expr(expr)?;
                self.env.insert(name.clone(), val.clone());
                Ok(val)
            }
            Statement::Assert { left, right, op } => {
                let l_val = self.eval_expr(left)?;
                let r_val = self.eval_expr(right)?;
                let res = self.eval_binary_op(op, &l_val, &r_val)?;
                Ok(res)
            }
            Statement::FnDef { name, params, body } => {
                self.functions.insert(
                    name.clone(),
                    UserFn {
                        params: params.clone(),
                        body: body.clone(),
                    },
                );
                Ok(PhsValue::None)
            }
            Statement::DisplayText(text) => Ok(PhsValue::String(text.clone())),
            Statement::ExprStmt(expr) => self.eval_expr(expr),
        }
    }

    pub fn eval_expr(&mut self, expr: &Expr) -> PhysureResult<PhsValue> {
        match expr {
            Expr::Number(n) => Ok(PhsValue::Number(*n)),
            Expr::StringLiteral(s) => Ok(PhsValue::String(s.clone())),
            Expr::Ident(name) => {
                if let Some(val) = self.env.get(name) {
                    return Ok(val.clone());
                }
                if let Some(unit) = self.registry.get_unit(name) {
                    use crate::quantity::Quantity;
                    return Ok(PhsValue::Quantity(Quantity::new_scalar(
                        1.0, 0.0, unit, None, None,
                    )));
                }
                if let Ok(unit) = crate::units::parser::Parser::parse_expression(name) {
                    use crate::quantity::Quantity;
                    return Ok(PhsValue::Quantity(Quantity::new_scalar(
                        1.0, 0.0, unit, None, None,
                    )));
                }
                Ok(PhsValue::ident(name.clone()))
            }
            Expr::Unary { op, expr } => {
                let val = self.eval_expr(expr)?;
                match (op, val) {
                    (UnaryOp::Neg, PhsValue::Number(n)) => Ok(PhsValue::Number(-n)),
                    (UnaryOp::Sqrt, PhsValue::Number(n)) => Ok(PhsValue::Number(n.sqrt())),
                    (UnaryOp::Sqrt, PhsValue::Quantity(q)) => Ok(PhsValue::Quantity(q.sqrt()?)),
                    _ => Err(PhysureError::Generic("Unsupported unary operation".into())),
                }
            }
            Expr::Binary { op, left, right } => {
                let l_val = self.eval_expr(left)?;
                let r_val = self.eval_expr(right)?;
                self.eval_binary_op(op, &l_val, &r_val)
            }
            Expr::ImplicitMul { left, right } => {
                let l_val = self.eval_expr(left)?;
                let r_val = self.eval_expr(right)?;
                self.eval_binary_op(&BinaryOp::Mul, &l_val, &r_val)
            }
            Expr::Call { name, args } => {
                let evaluated_args: PhysureResult<Vec<PhsValue>> =
                    args.iter().map(|arg| self.eval_expr(arg)).collect();
                let evaluated_args = evaluated_args?;

                if let Some(builtin_res) = eval_builtin(name, &evaluated_args)? {
                    return Ok(builtin_res);
                }

                if let Some(user_fn) = self.functions.get(name).cloned() {
                    if user_fn.params.len() != evaluated_args.len() {
                        return Err(PhysureError::Generic(format!(
                            "Function '{}' expects {} arguments, got {}",
                            name,
                            user_fn.params.len(),
                            evaluated_args.len()
                        )));
                    }
                    let mut local_interpreter = PhsInterpreter {
                        env: self.env.clone(),
                        functions: self.functions.clone(),
                        registry: self.registry.clone(),
                    };
                    for (param, arg_val) in user_fn.params.iter().zip(evaluated_args) {
                        local_interpreter.env.insert(param.name.clone(), arg_val);
                    }
                    let mut last_val = PhsValue::None;
                    for stmt in &user_fn.body {
                        last_val = local_interpreter.run_statement(stmt)?;
                    }
                    return Ok(last_val);
                }

                Err(PhysureError::Generic(format!("Unknown function '{}'", name)))
            }
            Expr::Ternary {
                cond,
                then_expr,
                else_expr,
            } => {
                let cond_val = self.eval_expr(cond)?;
                if is_truthy(&cond_val) {
                    self.eval_expr(then_expr)
                } else {
                    self.eval_expr(else_expr)
                }
            }
            Expr::Let { name, val, body } => {
                let evaluated_val = self.eval_expr(val)?;
                let mut local_env = self.env.clone();
                local_env.insert(name.clone(), evaluated_val);
                let mut local_interpreter = PhsInterpreter {
                    env: local_env,
                    functions: self.functions.clone(),
                    registry: self.registry.clone(),
                };
                local_interpreter.eval_expr(body)
            }
            Expr::If {
                cond,
                then_expr,
                else_expr,
            } => {
                let cond_val = self.eval_expr(cond)?;
                if is_truthy(&cond_val) {
                    self.eval_expr(then_expr)
                } else {
                    self.eval_expr(else_expr)
                }
            }
            Expr::Vector(items) => {
                let evaluated: PhysureResult<Vec<PhsValue>> =
                    items.iter().map(|item| self.eval_expr(item)).collect();
                Ok(PhsValue::Vector(evaluated?))
            }
            Expr::Uncertainty { val, unc } => {
                let mean_val = self.eval_expr(val)?;
                let unc_val = self.eval_expr(unc)?;
                let (mean, unit) = match mean_val {
                    PhsValue::Number(n) => (n, crate::units::RationalUnit::dimensionless()),
                    PhsValue::Quantity(q) => (q.value.mean(), q.unit),
                    _ => (0.0, crate::units::RationalUnit::dimensionless()),
                };
                let std_dev = match unc_val {
                    PhsValue::Number(n) => n,
                    PhsValue::Quantity(q) => q.value.mean(),
                    _ => 0.0,
                };
                use crate::quantity::Quantity;
                Ok(PhsValue::Quantity(Quantity::new_scalar(mean, std_dev, unit, None, None)))
            }
        }
    }

    fn eval_binary_op(
        &mut self,
        op: &BinaryOp,
        l_val: &PhsValue,
        r_val: &PhsValue,
    ) -> PhysureResult<PhsValue> {
        use crate::quantity::Quantity;

        let l_q = match l_val {
            PhsValue::String(s) => {
                if let Ok(unit) = crate::units::parser::Parser::parse_expression(s) {
                    Some(Quantity::new_scalar(1.0, 0.0, unit, None, None))
                } else {
                    None
                }
            }
            _ => None,
        };
        let r_q = match r_val {
            PhsValue::String(s) => {
                if let Ok(unit) = crate::units::parser::Parser::parse_expression(s) {
                    Some(Quantity::new_scalar(1.0, 0.0, unit, None, None))
                } else {
                    None
                }
            }
            _ => None,
        };

        if l_q.is_some() || r_q.is_some() {
            let left_v = l_q.map(PhsValue::Quantity).unwrap_or_else(|| l_val.clone());
            let right_v = r_q.map(PhsValue::Quantity).unwrap_or_else(|| r_val.clone());
            return self.eval_binary_op(op, &left_v, &right_v);
        }

        match (op, l_val, r_val) {
            // Number op Number
            (BinaryOp::Add, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Number(a + b)),
            (BinaryOp::Sub, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Number(a - b)),
            (BinaryOp::Mul, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Number(a * b)),
            (BinaryOp::Div, PhsValue::Number(a), PhsValue::Number(b)) => {
                if *b == 0.0 {
                    Err(PhysureError::Generic("Division by zero".into()))
                } else {
                    Ok(PhsValue::Number(a / b))
                }
            }
            (BinaryOp::Pow, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Number(a.powf(*b))),
            (BinaryOp::Eq, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Bool((a - b).abs() < 1e-9)),
            (BinaryOp::Neq, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Bool((a - b).abs() >= 1e-9)),
            (BinaryOp::Lt, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Bool(a < b)),
            (BinaryOp::Gt, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Bool(a > b)),
            (BinaryOp::Lte, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Bool(a <= b)),
            (BinaryOp::Gte, PhsValue::Number(a), PhsValue::Number(b)) => Ok(PhsValue::Bool(a >= b)),
            (BinaryOp::ApproxEq, PhsValue::Number(a), PhsValue::Number(b)) => {
                Ok(PhsValue::Bool((a - b).abs() < 1e-5))
            }

            // Quantity op Quantity
            (BinaryOp::Add, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Quantity(a.add(b)?)),
            (BinaryOp::Sub, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Quantity(a.sub(b)?)),
            (BinaryOp::Mul, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Quantity(a.mul(b)?)),
            (BinaryOp::Div, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Quantity(a.div(b)?)),
            (BinaryOp::Pow, PhsValue::Quantity(a), PhsValue::Number(b)) => Ok(PhsValue::Quantity(a.pow(*b)?)),
            (BinaryOp::Gt, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Bool(a.value.mean() > b.value.mean())),
            (BinaryOp::Lt, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Bool(a.value.mean() < b.value.mean())),
            (BinaryOp::Gte, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Bool(a.value.mean() >= b.value.mean())),
            (BinaryOp::Lte, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Bool(a.value.mean() <= b.value.mean())),
            (BinaryOp::ApproxEq, PhsValue::Quantity(a), PhsValue::Quantity(b)) => Ok(PhsValue::Bool(a.approx_eq(b, 1e-5, 1e-5))),

            // Number op Quantity / Quantity op Number
            (BinaryOp::Mul, PhsValue::Number(n), PhsValue::Quantity(q)) => {
                let scaled = Quantity::new_scalar(n * q.value.mean(), 0.0, q.unit.clone(), None, None);
                Ok(PhsValue::Quantity(scaled))
            }
            (BinaryOp::Mul, PhsValue::Quantity(q), PhsValue::Number(n)) => {
                let scaled = Quantity::new_scalar(n * q.value.mean(), 0.0, q.unit.clone(), None, None);
                Ok(PhsValue::Quantity(scaled))
            }
            (BinaryOp::Div, PhsValue::Quantity(q), PhsValue::Number(n)) => {
                if *n == 0.0 {
                    Err(PhysureError::Generic("Division by zero".into()))
                } else {
                    let scaled = Quantity::new_scalar(q.value.mean() / n, 0.0, q.unit.clone(), None, None);
                    Ok(PhsValue::Quantity(scaled))
                }
            }

            // Vector operations (element-wise)
            (op, PhsValue::Vector(vec), other) => {
                let res: PhysureResult<Vec<PhsValue>> = vec.iter().map(|item| self.eval_binary_op(op, item, other)).collect();
                Ok(PhsValue::Vector(res?))
            }
            (op, other, PhsValue::Vector(vec)) => {
                let res: PhysureResult<Vec<PhsValue>> = vec.iter().map(|item| self.eval_binary_op(op, other, item)).collect();
                Ok(PhsValue::Vector(res?))
            }

            _ => Err(PhysureError::Generic("Operation not implemented for types".into())),
        }
    }
}

// Internal helper for ident handling in interpreter
impl PhsValue {
    fn ident(s: String) -> Self {
        PhsValue::String(s)
    }
}

fn is_truthy(val: &PhsValue) -> bool {
    match val {
        PhsValue::Bool(b) => *b,
        PhsValue::Number(n) => *n != 0.0,
        PhsValue::None => false,
        _ => true,
    }
}
