"""Built-in calculator tool for mathematical operations."""

import ast
import logging
import operator
from typing import Any, Dict

from ..types.base import ToolDefinition

logger = logging.getLogger(__name__)


class CalculatorTool:
    """Safe calculator for mathematical expressions."""

    # Allowed operators
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    @staticmethod
    def get_definition() -> ToolDefinition:
        """Get tool definition for calculator."""
        from ..types.base import ToolMetadata, ToolSchema

        return ToolDefinition(
            metadata=ToolMetadata(
                name="calculator",
                description="Evaluate mathematical expressions safely. Supports +, -, *, /, ** (power), and parentheses.",
                category="utilities",
                tags=["math", "calculator", "computation"],
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * (5 + 3)', '2 ** 8')",
                        }
                    },
                    "required": ["expression"],
                }
            ),
        )

    @staticmethod
    def _eval_expr(node):
        """Safely evaluate an AST node."""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python 3.7
            return node.n
        elif isinstance(node, ast.BinOp):
            op = CalculatorTool._OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            left = CalculatorTool._eval_expr(node.left)
            right = CalculatorTool._eval_expr(node.right)
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            op = CalculatorTool._OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(
                    f"Unsupported unary operator: {type(node.op).__name__}"
                )
            operand = CalculatorTool._eval_expr(node.operand)
            return op(operand)
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    @staticmethod
    async def execute(expression: str) -> Dict[str, Any]:
        """Execute calculator operation.

        Args:
            expression: Mathematical expression to evaluate

        Returns:
            Dictionary with calculation result
        """
        try:
            # Parse the expression
            expression = expression.strip()
            tree = ast.parse(expression, mode="eval")

            # Evaluate safely
            result = CalculatorTool._eval_expr(tree.body)

            return {"success": True, "expression": expression, "result": result}
        except SyntaxError as e:
            logger.error("Syntax error in expression '%s': %s", expression, str(e))
            return {
                "success": False,
                "error": f"Invalid mathematical expression: {str(e)}",
                "error_type": "syntax_error",
            }
        except ValueError as e:
            logger.error("Value error in expression '%s': %s", expression, str(e))
            return {"success": False, "error": str(e), "error_type": "value_error"}
        except ZeroDivisionError:
            logger.error("Division by zero in expression '%s'", expression)
            return {
                "success": False,
                "error": "Division by zero",
                "error_type": "zero_division",
            }
        except Exception as e:
            logger.error("Unexpected error evaluating '%s': %s", expression, str(e))
            return {"success": False, "error": str(e), "error_type": "unexpected_error"}
