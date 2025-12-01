"""Tool Registry implementation for managing tool definitions."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from auto_pilot.tools.types.base import ToolDefinition

from .validators import SchemaValidator

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for managing tool definitions with metadata and schemas."""

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_versions: Dict[str, List[ToolDefinition]] = {}
        self._validator = SchemaValidator()
        logger.info("ToolRegistry initialized")

    def register_tool(
        self,
        tool_definition: ToolDefinition,
        validate_schema: bool = True,
        overwrite_existing: bool = False,
    ) -> bool:
        """Register a tool in the registry.

        Args:
            tool_definition: Complete tool definition with metadata and schema
            validate_schema: Whether to validate the JSON schema
            overwrite_existing: Whether to overwrite if tool already exists

        Returns:
            True if registration succeeded

        Raises:
            ValueError: If tool validation fails or tool already exists
        """
        tool_name = tool_definition.name

        # Check if tool already exists
        if tool_name in self._tools and not overwrite_existing:
            raise ValueError(
                f"Tool '{tool_name}' already exists. Use overwrite_existing=True to replace."
            )

        # Validate schema if requested
        if validate_schema:
            try:
                self._validator.validate_tool_schema(tool_definition.parameters.schema_dict)
            except Exception as e:
                raise ValueError(f"Tool schema validation failed for '{tool_name}': {str(e)}")

        # Update timestamps
        now = datetime.now()
        tool_definition.metadata.updated_at = now
        if tool_name not in self._tools:
            tool_definition.metadata.created_at = now

        # Store the tool
        self._tools[tool_name] = tool_definition

        # Store in version history
        if tool_name not in self._tool_versions:
            self._tool_versions[tool_name] = []

        # Add to version history (create a copy to avoid reference issues)
        import copy

        self._tool_versions[tool_name].append(copy.deepcopy(tool_definition))

        logger.info(
            f"Tool '{tool_name}' registered successfully (version {tool_definition.metadata.version})"
        )
        return True

    def get_tool(self, tool_name: str, version: Optional[str] = None) -> Optional[ToolDefinition]:
        """Get a tool definition by name and optional version.

        Args:
            tool_name: Name of the tool
            version: Specific version to retrieve (latest if None)

        Returns:
            Tool definition or None if not found
        """
        if version is None:
            return self._tools.get(tool_name)

        # Get specific version
        versions = self._tool_versions.get(tool_name, [])
        for tool_def in versions:
            if tool_def.metadata.version == version:
                return tool_def

        return None

    def list_tools(
        self,
        category: Optional[str] = None,
        include_deprecated: bool = False,
        tag_filter: Optional[List[str]] = None,
    ) -> List[ToolDefinition]:
        """List all registered tools with optional filtering.

        Args:
            category: Filter by tool category
            include_deprecated: Whether to include deprecated tools
            tag_filter: List of tags that tools must have

        Returns:
            List of tool definitions matching the criteria
        """
        tools = []

        for tool_def in self._tools.values():
            # Apply filters
            if category and tool_def.metadata.category != category:
                continue

            if not include_deprecated and tool_def.metadata.deprecated:
                continue

            if tag_filter:
                tool_tags = set(tool_def.metadata.tags)
                required_tags = set(tag_filter)
                if not required_tags.issubset(tool_tags):
                    continue

            tools.append(tool_def)

        return tools

    def search_tools(self, query: str) -> List[ToolDefinition]:
        """Search for tools by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching tool definitions
        """
        query_lower = query.lower()
        matching_tools = []

        for tool_def in self._tools.values():
            # Search in name, description, and tags
            if (
                query_lower in tool_def.name.lower()
                or query_lower in tool_def.description.lower()
                or any(query_lower in tag.lower() for tag in tool_def.metadata.tags)
            ):
                matching_tools.append(tool_def)

        return matching_tools

    def get_tool_versions(self, tool_name: str) -> List[str]:
        """Get all available versions for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of version strings
        """
        versions = self._tool_versions.get(tool_name, [])
        return [tool_def.metadata.version for tool_def in versions]

    def deprecate_tool(self, tool_name: str, message: str = "") -> bool:
        """Deprecate a tool.

        Args:
            tool_name: Name of the tool to deprecate
            message: Deprecation message

        Returns:
            True if deprecation succeeded
        """
        if tool_name not in self._tools:
            return False

        tool_def = self._tools[tool_name]
        tool_def.metadata.deprecated = True
        tool_def.metadata.deprecated_message = message
        tool_def.metadata.updated_at = datetime.now()

        logger.info("Tool '%s' deprecated: %s", tool_name, message)
        return True

    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the registry.

        Args:
            tool_name: Name of the tool to remove

        Returns:
            True if removal succeeded
        """
        if tool_name not in self._tools:
            return False

        del self._tools[tool_name]
        if tool_name in self._tool_versions:
            del self._tool_versions[tool_name]

        logger.info("Tool '%s' removed from registry", tool_name)
        return True

    def clear_registry(self) -> None:
        """Clear all tools from the registry."""
        self._tools.clear()
        self._tool_versions.clear()
        logger.info("Tool registry cleared")

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry.

        Returns:
            Dictionary with registry statistics
        """
        deprecated_count = sum(1 for tool in self._tools.values() if tool.metadata.deprecated)

        return {
            "total_tools": len(self._tools),
            "deprecated_tools": deprecated_count,
            "active_tools": len(self._tools) - deprecated_count,
            "categories": list(
                set(
                    tool.metadata.category
                    for tool in self._tools.values()
                    if tool.metadata.category
                )
            ),
            "total_versions": sum(len(versions) for versions in self._tool_versions.values()),
        }

    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against a tool's schema.

        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate

        Returns:
            True if parameters are valid

        Raises:
            ValueError: If tool doesn't exist or validation fails
        """
        tool_def = self.get_tool(tool_name)
        if not tool_def:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        return self._validator.validate_parameters(tool_def.parameters.schema_dict, parameters)

    def export_registry(self, include_deprecated: bool = True) -> Dict[str, Any]:
        """Export the entire registry as a dictionary.

        Args:
            include_deprecated: Whether to include deprecated tools

        Returns:
            Dictionary representation of the registry
        """
        tools = {}
        for tool_name, tool_def in self._tools.items():
            if not include_deprecated and tool_def.metadata.deprecated:
                continue
            tools[tool_name] = tool_def.dict()

        return {
            "tools": tools,
            "export_timestamp": datetime.now().isoformat(),
            "stats": self.get_registry_stats(),
        }

    def import_registry(self, registry_data: Dict[str, Any], overwrite: bool = False) -> int:
        """Import tools from a registry export.

        Args:
            registry_data: Dictionary containing registry data
            overwrite: Whether to overwrite existing tools

        Returns:
            Number of tools imported
        """
        tools_data = registry_data.get("tools", {})
        imported_count = 0

        for tool_name, tool_data in tools_data.items():
            try:
                tool_def = ToolDefinition.parse_obj(tool_data)
                self.register_tool(tool_def, validate_schema=True, overwrite_existing=overwrite)
                imported_count += 1
            except Exception as e:
                logger.warning("Failed to import tool '%s': %s", tool_name, str(e))

        logger.info("Imported %d tools from registry export", imported_count)
        return imported_count
