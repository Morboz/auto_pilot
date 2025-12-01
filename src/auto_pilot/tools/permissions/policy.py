"""Security Policy Enforcer for runtime policy enforcement."""

import fnmatch
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from auto_pilot.tools.types.permissions import SecurityPolicy, ToolPermissions

logger = logging.getLogger(__name__)


class SecurityPolicyEnforcer:
    """Runtime security policy enforcement for tool execution."""

    def __init__(self):
        """Initialize the security policy enforcer."""
        self._global_policies: List[SecurityPolicy] = []
        self._audit_log: List[Dict[str, Any]] = []
        logger.info("SecurityPolicyEnforcer initialized")

    def add_global_policy(self, policy: SecurityPolicy) -> None:
        """Add a global security policy.

        Args:
            policy: Security policy to add
        """
        self._global_policies.append(policy)
        logger.info("Global security policy added")

    def validate_import(
        self, tool_name: str, import_name: str, permissions: ToolPermissions
    ) -> bool:
        """Validate if an import is allowed.

        Args:
            tool_name: Name of the tool
            import_name: Name of the module to import
            permissions: Tool permissions

        Returns:
            True if import is allowed
        """
        security_policy = permissions.security

        # Check blocked imports first
        for blocked in security_policy.blocked_imports:
            if self._matches_pattern(import_name, blocked):
                self._log_security_event(
                    "import_blocked",
                    tool_name,
                    f"Import '{import_name}' blocked by pattern '{blocked}'",
                )
                return False

        # Check allowed imports (if whitelist is specified)
        if security_policy.allowed_imports:
            allowed = False
            for allowed_import in security_policy.allowed_imports:
                if self._matches_pattern(import_name, allowed_import):
                    allowed = True
                    break

            if not allowed:
                self._log_security_event(
                    "import_denied",
                    tool_name,
                    f"Import '{import_name}' not in allowed list",
                )
                return False

        # Check against global policies
        for global_policy in self._global_policies:
            if not self._validate_import_against_policy(import_name, global_policy):
                self._log_security_event(
                    "import_denied_by_global_policy",
                    tool_name,
                    f"Import '{import_name}' denied by global policy",
                )
                return False

        self._log_security_event(
            "import_allowed",
            tool_name,
            f"Import '{import_name}' allowed",
        )
        return True

    def validate_environment_variable(
        self,
        tool_name: str,
        var_name: str,
        var_value: str,
        permissions: ToolPermissions,
    ) -> bool:
        """Validate if an environment variable can be set.

        Args:
            tool_name: Name of the tool
            var_name: Environment variable name
            var_value: Environment variable value
            permissions: Tool permissions

        Returns:
            True if setting is allowed
        """
        security_policy = permissions.security

        # Check if variable is explicitly allowed
        if var_name in security_policy.environment_variables:
            allowed_value = security_policy.environment_variables[var_name]
            if allowed_value == var_value or allowed_value == "*":
                return True
            else:
                self._log_security_event(
                    "env_var_value_blocked",
                    tool_name,
                    f"Environment variable '{var_name}' value blocked",
                )
                return False

        # Check against sensitive variable patterns
        sensitive_patterns = [
            r".*PASSWORD.*",
            r".*SECRET.*",
            r".*TOKEN.*",
            r".*PRIVATE.*",
            r".*KEY.*",
        ]

        for pattern in sensitive_patterns:
            if re.match(pattern, var_name, re.IGNORECASE):
                self._log_security_event(
                    "env_var_sensitive_blocked",
                    tool_name,
                    f"Sensitive environment variable '{var_name}' blocked",
                )
                return False

        return True

    def sanitize_output(self, output: str, permissions: ToolPermissions) -> str:
        """Sanitize tool output to prevent information leakage.

        Args:
            output: Raw output from tool
            permissions: Tool permissions

        Returns:
            Sanitized output
        """
        if not permissions.security.enable_output_sanitization:
            return output

        # Patterns to sanitize
        sanitization_patterns = [
            # File paths
            (r"/[^\s]*", "[FILE_PATH]"),
            # IP addresses
            (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_ADDRESS]"),
            # Email addresses
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
            # API keys (basic pattern)
            (r"\b[a-zA-Z0-9]{32,}\b", "[API_KEY]"),
            # Passwords in common formats
            (r"password\s*[:=]\s*[^\s]+", "password=[REDACTED]"),
            (r"pwd\s*[:=]\s*[^\s]+", "pwd=[REDACTED]"),
        ]

        sanitized = output
        for pattern, replacement in sanitization_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def audit_execution(
        self,
        tool_name: str,
        execution_context: Dict[str, Any],
        permissions: ToolPermissions,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Audit tool execution for security monitoring.

        Args:
            tool_name: Name of the tool
            execution_context: Execution context information
            permissions: Permissions used during execution
            result: Execution result (if available)
        """
        if not permissions.security.enable_audit_logging:
            return

        audit_entry = {
            "timestamp": datetime.now(),
            "tool_name": tool_name,
            "execution_id": execution_context.get("execution_id"),
            "permissions_snapshot": permissions.dict(),
            "resource_usage": execution_context.get("resource_usage", {}),
            "success": result.get("success") if result else None,
            "error_type": result.get("error_type") if result else None,
        }

        self._audit_log.append(audit_entry)
        logger.info("Audit log entry created for tool '%s'", tool_name)

    def get_audit_log(
        self, tool_name: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries.

        Args:
            tool_name: Filter by tool name (optional)
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        entries = self._audit_log

        if tool_name:
            entries = [entry for entry in entries if entry["tool_name"] == tool_name]

        # Return most recent entries
        return entries[-limit:]

    def clear_audit_log(self) -> None:
        """Clear the audit log."""
        self._audit_log.clear()
        logger.info("Audit log cleared")

    def _validate_import_against_policy(
        self, import_name: str, policy: SecurityPolicy
    ) -> bool:
        """Validate import against a specific security policy.

        Args:
            import_name: Name of the import
            policy: Security policy to check against

        Returns:
            True if import is allowed by policy
        """
        # Check blocked imports
        for blocked in policy.blocked_imports:
            if self._matches_pattern(import_name, blocked):
                return False

        # Check allowed imports (if whitelist exists)
        if policy.allowed_imports:
            allowed = False
            for allowed_import in policy.allowed_imports:
                if self._matches_pattern(import_name, allowed_import):
                    allowed = True
                    break
            return allowed

        return True

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if a value matches a pattern.

        Args:
            value: Value to check
            pattern: Pattern to match against

        Returns:
            True if value matches pattern
        """
        # Exact match
        if value == pattern:
            return True

        # Wildcard matching
        if "*" in pattern:
            return fnmatch.fnmatch(value, pattern)

        # Regex matching
        if pattern.startswith("regex:"):
            regex_pattern = pattern[6:]
            return bool(re.match(regex_pattern, value))

        return False

    def _log_security_event(
        self, event_type: str, tool_name: str, message: str
    ) -> None:
        """Log a security event.

        Args:
            event_type: Type of security event
            tool_name: Name of the tool
            message: Event message
        """
        logger.warning(
            f"Security event '{event_type}' for tool '{tool_name}': {message}"
        )

    def generate_security_report(
        self, tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a security report.

        Args:
            tool_name: Filter by specific tool (optional)

        Returns:
            Security report with statistics
        """
        audit_entries = self.get_audit_log(tool_name)

        total_executions = len(audit_entries)
        successful_executions = sum(
            1 for entry in audit_entries if entry.get("success")
        )
        failed_executions = total_executions - successful_executions

        security_events = {}
        for entry in audit_entries:
            # Analyze security-relevant events
            if entry.get("error_type") in ["permission_denied", "security_violation"]:
                error_type = entry["error_type"]
                security_events[error_type] = security_events.get(error_type, 0) + 1

        return {
            "tool_name": tool_name or "all_tools",
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions
            if total_executions > 0
            else 0,
            "security_events": security_events,
            "report_generated": datetime.now(),
        }
