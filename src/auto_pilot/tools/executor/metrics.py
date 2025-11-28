"""Execution metrics collection and monitoring."""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExecutionMetrics:
    """Collects and manages execution metrics for tool execution."""

    def __init__(self):
        """Initialize execution metrics."""
        self.executions: List[Dict[str, Any]] = []
        self.metrics_by_tool: Dict[str, List[Dict[str, Any]]] = {}
        self.start_time = time.time()
        logger.info("ExecutionMetrics initialized")

    def record_execution(self, tool_name: str, result: Any) -> None:
        """Record a tool execution.

        Args:
            tool_name: Name of the tool
            result: Execution result
        """
        execution = {
            "timestamp": datetime.now(),
            "tool_name": tool_name,
            "success": result.success if hasattr(result, "success") else False,
            "execution_time_ms": float(result.execution_time_ms)
            if hasattr(result, "execution_time_ms")
            else 0.0,
            "error_type": result.error_type if hasattr(result, "error_type") else None,
            "resource_usage": result.resource_usage
            if hasattr(result, "resource_usage")
            else None,
        }

        self.executions.append(execution)

        if tool_name not in self.metrics_by_tool:
            self.metrics_by_tool[tool_name] = []
        self.metrics_by_tool[tool_name].append(execution)

        logger.debug("Recorded execution for tool '%s'", tool_name)

    def get_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution metrics.

        Args:
            tool_name: Optional tool name to filter by

        Returns:
            Dictionary with metrics
        """
        executions = (
            self.metrics_by_tool.get(tool_name, self.executions)
            if tool_name
            else self.executions
        )

        if not executions:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "average_execution_time_ms": 0.0,
                "total_execution_time_ms": 0.0,
            }

        total_executions = len(executions)
        successful_executions = sum(1 for e in executions if e["success"])
        failed_executions = total_executions - successful_executions
        success_rate = successful_executions / total_executions
        total_execution_time = sum(e["execution_time_ms"] for e in executions)
        average_execution_time = total_execution_time / total_executions

        metrics = {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": success_rate,
            "average_execution_time_ms": average_execution_time,
            "total_execution_time_ms": total_execution_time,
            "uptime_seconds": time.time() - self.start_time,
        }

        # Add tool-specific metrics if not filtered
        if not tool_name:
            error_types = {}
            for execution in executions:
                error_type = execution["error_type"]
                if error_type:
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            metrics["error_types"] = error_types

            # Most/least successful tools
            tool_success_rates = {}
            for t_name, tool_executions in self.metrics_by_tool.items():
                if tool_executions:
                    success_count = sum(1 for e in tool_executions if e["success"])
                    tool_success_rates[t_name] = success_count / len(tool_executions)

            if tool_success_rates:
                metrics["most_successful_tools"] = sorted(
                    tool_success_rates.items(), key=lambda x: x[1], reverse=True
                )[:5]
                metrics["least_successful_tools"] = sorted(
                    tool_success_rates.items(), key=lambda x: x[1]
                )[:5]

        return metrics

    def get_performance_trends(
        self, tool_name: Optional[str] = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get performance trends over time.

        Args:
            tool_name: Optional tool name to filter by
            hours: Number of hours to look back

        Returns:
            List of performance data points
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        executions = (
            self.metrics_by_tool.get(tool_name, self.executions)
            if tool_name
            else self.executions
        )

        recent_executions = [e for e in executions if e["timestamp"] > cutoff_time]

        # Group by hour
        hourly_data = {}
        for execution in recent_executions:
            hour_key = execution["timestamp"].replace(minute=0, second=0, microsecond=0)
            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            hourly_data[hour_key].append(execution)

        trends = []
        for hour, hour_executions in sorted(hourly_data.items()):
            total = len(hour_executions)
            successful = sum(1 for e in hour_executions if e["success"])
            avg_time = sum(e["execution_time_ms"] for e in hour_executions) / total

            trends.append(
                {
                    "hour": hour.isoformat(),
                    "total_executions": total,
                    "successful_executions": successful,
                    "success_rate": successful / total,
                    "average_execution_time_ms": avg_time,
                }
            )

        return trends

    def get_slowest_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest tool executions.

        Args:
            limit: Maximum number to return

        Returns:
            List of slowest executions
        """
        sorted_executions = sorted(
            self.executions, key=lambda e: e["execution_time_ms"], reverse=True
        )
        return sorted_executions[:limit]

    def get_most_frequent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequent errors.

        Args:
            limit: Maximum number to return

        Returns:
            List of most frequent errors
        """
        error_counts = {}
        for execution in self.executions:
            error_type = execution["error_type"]
            if error_type:
                if error_type not in error_counts:
                    error_counts[error_type] = {
                        "count": 0,
                        "last_seen": None,
                        "tool_name": execution["tool_name"],
                    }
                error_counts[error_type]["count"] += 1
                error_counts[error_type]["last_seen"] = execution["timestamp"]

        sorted_errors = sorted(
            error_counts.items(), key=lambda x: x[1]["count"], reverse=True
        )

        return [
            {"error_type": error_type, **info}
            for error_type, info in sorted_errors[:limit]
        ]

    def clear(self) -> None:
        """Clear all metrics."""
        self.executions.clear()
        self.metrics_by_tool.clear()
        self.start_time = time.time()
        logger.info("Execution metrics cleared")

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format.

        Args:
            format: Export format (json, csv)

        Returns:
            Formatted metrics string
        """
        import json

        metrics = self.get_metrics()

        if format == "json":
            return json.dumps(metrics, indent=2, default=str)
        elif format == "csv":
            # Simplified CSV export
            lines = ["tool_name,success,execution_time_ms,error_type"]
            for execution in self.executions:
                lines.append(
                    f"{execution['tool_name']},{execution['success']},"
                    f"{execution['execution_time_ms']},{execution['error_type']}"
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")
