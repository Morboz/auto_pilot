"""Permission Manager for centralized access control."""

import fnmatch
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from auto_pilot.tools.types.permissions import (
    FileSystemPermission,
    NetworkPermission,
    ResourceLimits,
    SecurityPolicy,
    ToolPermissions,
)

try:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from auto_pilot.models import AgentTool

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.info(
        "Database modules not available, PermissionManager will use in-memory permissions only"
    )

logger = logging.getLogger(__name__)


class PermissionManager:
    """Centralized permission controller for tool execution."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize the permission manager.

        Args:
            db_session: Optional SQLAlchemy async session for database-backed permissions
        """
        self._tool_permissions: Dict[str, ToolPermissions] = {}
        self._default_permissions = ToolPermissions()
        self._security_policies: Dict[str, SecurityPolicy] = {}

        # Database session and caching
        self._db_session: Optional[AsyncSession] = db_session if DB_AVAILABLE else None
        self._permissions_cache: Dict[
            str, Dict[str, ToolPermissions]
        ] = {}  # {agent_id: {tool_name: permissions}}
        self._cache_ttl: Dict[str, datetime] = {}  # {cache_key: expiry_time}
        self._cache_duration = timedelta(minutes=5)  # 缓存有效期 5 分钟

        logger.info("PermissionManager initialized")

    def set_tool_permissions(
        self, tool_name: str, permissions: ToolPermissions
    ) -> None:
        """Set permissions for a specific tool.

        Args:
            tool_name: Name of the tool
            permissions: Permission configuration for the tool
        """
        self._tool_permissions[tool_name] = permissions
        logger.info("Permissions set for tool '%s'", tool_name)

    def get_tool_permissions(self, tool_name: str) -> ToolPermissions:
        """Get permissions for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool permissions (defaults if not configured)
        """
        return self._tool_permissions.get(tool_name, self._default_permissions)

    def set_default_permissions(self, permissions: ToolPermissions) -> None:
        """Set default permissions for all tools.

        Args:
            permissions: Default permission configuration
        """
        self._default_permissions = permissions
        logger.info("Default permissions updated")

    def check_filesystem_access(
        self,
        tool_name: str,
        path: str,
        operation: str,
        workspace_path: Optional[str] = None,
    ) -> bool:
        """Check if a tool can access a file system path.

        Args:
            tool_name: Name of the tool
            path: Path to access
            operation: Operation type (read, write, execute, delete)
            workspace_path: Optional workspace path for relative access

        Returns:
            True if access is allowed
        """
        permissions = self.get_tool_permissions(tool_name)
        fs_perm = permissions.filesystem

        # Resolve path
        resolved_path = Path(path).resolve()
        if workspace_path:
            workspace_path = Path(workspace_path).resolve()
            # Make path relative to workspace if possible
            try:
                resolved_path = resolved_path.relative_to(workspace_path)
            except ValueError:
                # Path is not relative to workspace, use absolute
                pass

        path_str = str(resolved_path)

        # Check denied paths first (explicit deny takes precedence)
        for denied_path in fs_perm.denied_paths:
            if self._path_matches(path_str, denied_path):
                logger.warning(
                    "Tool '%s' denied access to '%s' (denied path)", tool_name, path_str
                )
                return False

        # Check allowed paths
        if not fs_perm.allowed_paths:
            # No allowed paths configured, deny by default
            logger.warning(
                "Tool '%s' denied access to '%s' (no allowed paths)",
                tool_name,
                path_str,
            )
            return False

        for allowed_path in fs_perm.allowed_paths:
            if self._path_matches(path_str, allowed_path):
                # Check if operation is allowed
                if operation in fs_perm.operations:
                    logger.debug(
                        "Tool '%s' granted %s access to '%s'",
                        tool_name,
                        operation,
                        path_str,
                    )
                    return True
                else:
                    logger.warning(
                        "Tool '%s' denied %s access to '%s' (operation not allowed)",
                        tool_name,
                        operation,
                        path_str,
                    )
                    return False

        # No matching allowed path found
        logger.warning(
            "Tool '%s' denied access to '%s' (path not in allowed list)",
            tool_name,
            path_str,
        )
        return False

    def check_network_access(
        self,
        tool_name: str,
        host: str,
        port: int,
        protocol: str = "tcp",
    ) -> bool:
        """Check if a tool can access a network host and port.

        Args:
            tool_name: Name of the tool
            host: Host to access
            port: Port number
            protocol: Protocol type (tcp, udp)

        Returns:
            True if access is allowed
        """
        permissions = self.get_tool_permissions(tool_name)
        net_perm = permissions.network

        if not net_perm.enabled:
            logger.warning(
                "Tool '%s' denied network access (networking disabled)", tool_name
            )
            return False

        # Check denied hosts first
        for denied_host in net_perm.denied_hosts:
            if self._host_matches(host, denied_host):
                logger.warning(
                    "Tool '%s' denied access to host '%s' (denied host)",
                    tool_name,
                    host,
                )
                return False

        # Check allowed hosts
        if net_perm.allowed_hosts:
            allowed = False
            for allowed_host in net_perm.allowed_hosts:
                if self._host_matches(host, allowed_host):
                    allowed = True
                    break

            if not allowed:
                logger.warning(
                    "Tool '%s' denied access to host '%s' (host not allowed)",
                    tool_name,
                    host,
                )
                return False

        # Check allowed ports
        if net_perm.allowed_ports and port not in net_perm.allowed_ports:
            logger.warning(
                "Tool '%s' denied access to port %d (port not allowed)", tool_name, port
            )
            return False

        logger.debug("Tool '%s' granted network access to %s:%d", tool_name, host, port)
        return True

    def check_resource_limits(
        self, tool_name: str, current_usage: Dict[str, float]
    ) -> bool:
        """Check if current resource usage is within limits.

        Args:
            tool_name: Name of the tool
            current_usage: Dictionary of current resource usage metrics

        Returns:
            True if usage is within limits
        """
        permissions = self.get_tool_permissions(tool_name)
        limits = permissions.resources

        # Check CPU usage
        cpu_usage = current_usage.get("cpu_percent", 0)
        if cpu_usage > limits.max_cpu_percent:
            logger.warning(
                "Tool '%s' CPU usage %s%% exceeds limit %s%%",
                tool_name,
                cpu_usage,
                limits.max_cpu_percent,
            )
            return False

        # Check memory usage
        memory_usage = current_usage.get("memory_mb", 0)
        if memory_usage > limits.max_memory_mb:
            logger.warning(
                "Tool '%s' memory usage %sMB exceeds limit %sMB",
                tool_name,
                memory_usage,
                limits.max_memory_mb,
            )
            return False

        # Check disk space
        disk_usage = current_usage.get("disk_space_mb", 0)
        if disk_usage > limits.max_disk_space_mb:
            logger.warning(
                "Tool '%s' disk usage %sMB exceeds limit %sMB",
                tool_name,
                disk_usage,
                limits.max_disk_space_mb,
            )
            return False

        logger.debug("Tool '%s' resource usage within limits", tool_name)
        return True

    def get_effective_permissions(self, tool_name: str) -> Dict[str, Any]:
        """Get effective permissions for a tool (including defaults).

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary of effective permissions
        """
        permissions = self.get_tool_permissions(tool_name)
        return {
            "filesystem": permissions.filesystem.dict(),
            "network": permissions.network.dict(),
            "resources": permissions.resources.dict(),
            "security": permissions.security.dict(),
            "custom": permissions.custom_permissions,
        }

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if a path matches a pattern (supports wildcards).

        Args:
            path: The path to check
            pattern: The pattern to match against

        Returns:
            True if path matches pattern
        """
        # Normalize paths
        path = os.path.normpath(path)
        pattern = os.path.normpath(pattern)

        # Support glob-style wildcards
        if "*" in pattern or "?" in pattern:
            return fnmatch.fnmatch(path, pattern)

        # Support regex patterns
        if pattern.startswith("regex:"):
            regex_pattern = pattern[6:]  # Remove "regex:" prefix
            return bool(re.match(regex_pattern, path))

        # Exact match or prefix match
        return path == pattern or path.startswith(pattern + os.sep)

    def _host_matches(self, host: str, pattern: str) -> bool:
        """Check if a host matches a pattern.

        Args:
            host: The host to check
            pattern: The pattern to match against

        Returns:
            True if host matches pattern
        """
        # Exact match
        if host == pattern:
            return True

        # Support wildcards
        if "*" in pattern:
            return fnmatch.fnmatch(host, pattern)

        # Support regex patterns
        if pattern.startswith("regex:"):
            regex_pattern = pattern[6:]
            return bool(re.match(regex_pattern, host))

        # Domain suffix matching
        if pattern.startswith("*."):
            return host.endswith(pattern[1:])

        return False

    def create_restricted_permissions(self) -> ToolPermissions:
        """Create highly restricted permissions for untrusted tools.

        Returns:
            Restricted permissions configuration
        """
        return ToolPermissions(
            filesystem=FileSystemPermission(
                allowed_paths=[],
                denied_paths=["*"],
                operations=set(),
            ),
            network=NetworkPermission(
                enabled=False,
                allowed_hosts=[],
                allowed_ports=[],
                denied_hosts=["*"],
            ),
            resources=ResourceLimits(
                max_cpu_percent=10.0,
                max_memory_mb=64,
                max_disk_space_mb=10,
                max_execution_time_seconds=5.0,
                max_processes=1,
                max_file_size_mb=1,
            ),
            security=SecurityPolicy(
                enable_sandbox=True,
                enable_output_sanitization=True,
                enable_audit_logging=True,
                allowed_imports=[],
                blocked_imports=["*"],
            ),
        )

    def create_trusted_permissions(self) -> ToolPermissions:
        """Create permissive permissions for trusted tools.

        Returns:
            Trusted permissions configuration
        """
        return ToolPermissions(
            filesystem=FileSystemPermission(
                allowed_paths=["/tmp", "/workspace"],
                denied_paths=["/etc", "/home", "/root"],
                operations={"read", "write", "execute"},
            ),
            network=NetworkPermission(
                enabled=True,
                allowed_hosts=["*.api.openai.com", "*.claude.ai", "localhost"],
                allowed_ports=[80, 443, 8080],
                denied_hosts=[],
            ),
            resources=ResourceLimits(
                max_cpu_percent=80.0,
                max_memory_mb=1024,
                max_disk_space_mb=2048,
                max_execution_time_seconds=300.0,
                max_processes=10,
                max_file_size_mb=100,
            ),
            security=SecurityPolicy(
                enable_sandbox=True,
                enable_output_sanitization=False,
                enable_audit_logging=True,
                allowed_imports=["os", "sys", "json", "requests", "pathlib"],
                blocked_imports=["subprocess", "socket", "ctypes"],
            ),
        )

    async def get_tool_permissions_from_db(
        self, tool_name: str, agent_id: Optional[str] = None
    ) -> Optional[ToolPermissions]:
        """Get permissions for a tool from database (agent-specific).

        Args:
            tool_name: Name of the tool
            agent_id: Optional Agent ID for agent-specific permissions

        Returns:
            ToolPermissions if found in database, None otherwise
        """
        if not self._db_session or not DB_AVAILABLE or not agent_id:
            return None

        try:
            # Build cache key
            cache_key = f"{agent_id}:{tool_name}"

            # Check cache first
            cached_perm = self._get_cached_permission(agent_id, tool_name)
            if cached_perm:
                logger.debug(
                    "Cache hit for tool '%s' and agent '%s'", tool_name, agent_id
                )
                return cached_perm

            # Query database
            from auto_pilot.models import Tool

            # Get tool by name
            tool_result = await self._db_session.execute(
                select(Tool).where(Tool.name == tool_name)
            )
            tool = tool_result.scalar_one_or_none()

            if not tool:
                logger.debug("Tool '%s' not found in database", tool_name)
                return None

            # Get agent-tool relationship
            result = await self._db_session.execute(
                select(AgentTool).where(
                    AgentTool.agent_id == agent_id,
                    AgentTool.tool_id == tool.id,
                )
            )
            agent_tool = result.scalar_one_or_none()

            if not agent_tool or not agent_tool.permissions:
                logger.debug(
                    f"No permissions found in database for tool '{tool_name}' "
                    f"and agent '{agent_id}'"
                )
                return None

            # Parse JSON permissions
            perm_dict = agent_tool.permissions

            # Convert to ToolPermissions object
            tool_permissions = ToolPermissions(
                filesystem=FileSystemPermission(**perm_dict.get("filesystem", {})),
                network=NetworkPermission(**perm_dict.get("network", {})),
                resources=ResourceLimits(**perm_dict.get("resources", {})),
                security=SecurityPolicy(**perm_dict.get("security", {})),
                custom_permissions=perm_dict.get("custom_permissions", {}),
            )

            # Cache the result
            self._cache_permission(agent_id, tool_name, tool_permissions)

            logger.info(
                f"Retrieved permissions for tool '{tool_name}' "
                f"and agent '{agent_id}' from database"
            )

            return tool_permissions

        except Exception as e:
            logger.warning(
                f"Error retrieving permissions from database for tool '{tool_name}' "
                f"and agent '{agent_id}': {e}"
            )
            return None

    def get_tool_permissions(
        self, tool_name: str, agent_id: Optional[str] = None
    ) -> ToolPermissions:
        """Get permissions for a specific tool with three-level fallback.

        Args:
            tool_name: Name of the tool
            agent_id: Optional Agent ID for agent-specific permissions

        Returns:
            Tool permissions (with fallback: DB -> memory -> defaults)
        """
        # Try to get from database first (async)
        # Note: This is an async method, should be called with await in async context
        # For sync context, we check cache and memory first

        # Check cache (works in both sync and async)
        if agent_id:
            cached = self._get_cached_permission(agent_id, tool_name)
            if cached:
                return cached

        # Check memory (code-configured permissions)
        if tool_name in self._tool_permissions:
            return self._tool_permissions[tool_name]

        # If we have DB session and agent_id, return default for now
        # The async version should be used to fetch from DB
        if self._db_session and agent_id:
            # Return default and log that async fetch should be used
            logger.debug(
                f"Database permissions available for tool '{tool_name}' and agent '{agent_id}', "
                f"but use async method get_tool_permissions_from_db() to fetch"
            )

        # Return default permissions
        return self._default_permissions

    async def get_tool_permissions_async(
        self, tool_name: str, agent_id: Optional[str] = None
    ) -> ToolPermissions:
        """Get permissions for a specific tool with full fallback (async).

        Args:
            tool_name: Name of the tool
            agent_id: Optional Agent ID for agent-specific permissions

        Returns:
            Tool permissions (fallback: DB -> memory -> defaults)
        """
        # 1. Try database (highest priority)
        if agent_id and self._db_session:
            db_permissions = await self.get_tool_permissions_from_db(
                tool_name, agent_id
            )
            if db_permissions:
                return db_permissions

        # 2. Try memory (code-configured)
        if tool_name in self._tool_permissions:
            return self._tool_permissions[tool_name]

        # 3. Return default
        return self._default_permissions

    def _get_cached_permission(
        self, agent_id: str, tool_name: str
    ) -> Optional[ToolPermissions]:
        """Get permission from cache if not expired.

        Args:
            agent_id: Agent ID
            tool_name: Tool name

        Returns:
            Cached ToolPermissions or None
        """
        cache_key = f"{agent_id}:{tool_name}"

        # Check if key exists and not expired
        if cache_key in self._cache_ttl:
            if datetime.now() < self._cache_ttl[cache_key]:
                # Return cached permissions for this agent and tool
                agent_cache = self._permissions_cache.get(agent_id, {})
                return agent_cache.get(tool_name)
            else:
                # Cache expired, remove it
                self._clear_cache_entry(agent_id, tool_name)

        return None

    def _cache_permission(
        self, agent_id: str, tool_name: str, permissions: ToolPermissions
    ) -> None:
        """Cache permission with TTL.

        Args:
            agent_id: Agent ID
            tool_name: Tool name
            permissions: ToolPermissions object to cache
        """
        if not agent_id:
            return

        cache_key = f"{agent_id}:{tool_name}"
        expiry_time = datetime.now() + self._cache_duration

        # Initialize agent cache if not exists
        if agent_id not in self._permissions_cache:
            self._permissions_cache[agent_id] = {}

        # Store permission and expiry
        self._permissions_cache[agent_id][tool_name] = permissions
        self._cache_ttl[cache_key] = expiry_time

        logger.debug(
            f"Cached permissions for tool '{tool_name}' "
            f"and agent '{agent_id}' (expires at {expiry_time})"
        )

    def _clear_cache_entry(self, agent_id: str, tool_name: str) -> None:
        """Clear a specific cache entry.

        Args:
            agent_id: Agent ID
            tool_name: Tool name
        """
        cache_key = f"{agent_id}:{tool_name}"

        if agent_id in self._permissions_cache:
            self._permissions_cache[agent_id].pop(tool_name, None)
            if not self._permissions_cache[agent_id]:
                del self._permissions_cache[agent_id]

        self._cache_ttl.pop(cache_key, None)

    def clear_cache(self, agent_id: Optional[str] = None) -> None:
        """Clear permissions cache.

        Args:
            agent_id: Optional agent ID to clear cache for specific agent only
        """
        if agent_id:
            # Clear cache for specific agent
            agent_keys = [
                k for k in self._cache_ttl.keys() if k.startswith(f"{agent_id}:")
            ]
            for key in agent_keys:
                self._cache_ttl.pop(key, None)

            self._permissions_cache.pop(agent_id, None)

            logger.info("Cleared permissions cache for agent '%s'", agent_id)
        else:
            # Clear all cache
            self._permissions_cache.clear()
            self._cache_ttl.clear()

            logger.info("Cleared all permissions cache")

    def set_db_session(self, db_session: AsyncSession) -> None:
        """Set database session (for dependency injection).

        Args:
            db_session: SQLAlchemy async session
        """
        if DB_AVAILABLE:
            self._db_session = db_session
            logger.info("Database session set in PermissionManager")
        else:
            logger.warning("Database modules not available, cannot set session")
