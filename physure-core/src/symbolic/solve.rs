use crate::error::{PhysureError, PhysureResult};
use super::ast::Node;

impl Node {
    pub fn solve_equation(&self, target: &str) -> PhysureResult<Node> {
        let simplified = self.simplify();

        // Check if expression is linear: a * target + b = 0
        if let Some((a, b)) = simplified.linear_coeff(target) {
            if a != 0.0 {
                let solution = Node::Div(
                    Box::new(Node::Number(-b)),
                    Box::new(Node::Number(a)),
                );
                return Ok(solution.simplify());
            }
        }

        // Try power rule equation: a * target^n + b = 0 => target = (-b / a)^(1/n)
        if let Node::Add(terms) = &simplified {
            let mut target_term: Option<&Node> = None;
            let mut const_val = 0.0;

            for t in terms {
                if t.depends_on(target) {
                    if target_term.is_none() {
                        target_term = Some(t);
                    } else {
                        return Err(PhysureError::Generic(format!(
                            "Multiple non-linear terms for target '{}' in equation",
                            target
                        )));
                    }
                } else if let Node::Number(n) = t {
                    const_val += n;
                }
            }

            if let Some(t_node) = target_term {
                if let Node::Pow(base, exp) = t_node {
                    if let Node::Symbol(s) = &**base {
                        if s == target {
                            let solution = Node::Pow(
                                Box::new(Node::Number(-const_val)),
                                Box::new(Node::Div(Box::new(Node::Number(1.0)), exp.clone())),
                            );
                            return Ok(solution.simplify());
                        }
                    }
                }
            }
        }

        Err(PhysureError::Generic(format!(
            "Cannot solve equation symbolically for target '{}'",
            target
        )))
    }
}
