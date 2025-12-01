"""Built-in tools loader for automatic registration at startup."""

import importlib
import inspect
import logging
import pkgutil
from types import ModuleType
from typing import Any, List, Type

from auto_pilot.tools.executor import ToolExecutor
from auto_pilot.tools.registry import ToolRegistry
from auto_pilot.tools.types.base import ToolDefinition

logger = logging.getLogger(__name__)


class BuiltinToolLoader:
    """Loader for built-in tools that are pre-registered with the system."""

    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor,
    ):
        """Initialize the built-in tool loader.

        Args:
            registry: Tool registry to register definitions
            executor: Tool executor to register implementations
        """
        self.registry = registry
        self.executor = executor
        self._loaded_tools: List[str] = []

    def load_builtin_tools(self) -> int:
        """Load all built-in tools by scanning the builtin package.

        Returns:
            Number of tools loaded
        """
        from .. import builtin

        package_path = builtin.__path__
        package_name = builtin.__name__

        loaded_count = 0

        # Iterate over all modules in the builtin package
        for _, name, _ in pkgutil.iter_modules(package_path, package_name + "."):
            try:
                module = importlib.import_module(name)
                loaded_count += self._load_tools_from_module(module)
            except Exception as e:
                logger.error("Failed to load module %s: %s", name, e, exc_info=True)

        logger.info("Loaded %d built-in tools", loaded_count)
        return loaded_count

    def _load_tools_from_module(self, module: ModuleType) -> int:
        """Scan a module for tool classes and register them.

        Args:
            module: The module to scan

        Returns:
            Number of tools registered from this module
        """
        count = 0
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and self._is_tool_class(obj):
                # Only register tools defined in this module to avoid duplicates
                if obj.__module__ == module.__name__:
                    try:
                        self._register_tool_class(obj)
                        count += 1
                    except ValueError as e:
                        # Skip if already registered or invalid
                        if "already exists" not in str(e):
                            logger.warning("Skipping tool %s: %s", name, e)
                    except Exception as e:
                        logger.error("Failed to register tool %s: %s", name, e)
        return count

    def _is_tool_class(self, cls: Type[Any]) -> bool:
        """Check if a class looks like a tool class.

        Args:
            cls: The class to check

        Returns:
            True if the class has required tool methods
        """
        # Check for required methods
        return hasattr(cls, "get_definition") and hasattr(cls, "execute")

    def _register_tool_class(self, tool_class: Type[Any]) -> None:
        """Register a tool class with the registry and executor.

        Args:
            tool_class: Tool class with get_definition() and execute() methods
        """
        # Get tool definition
        if not hasattr(tool_class, "get_definition"):
            raise ValueError(
                f"Tool class {tool_class.__name__} missing get_definition()"
            )

        definition = tool_class.get_definition()
        if not isinstance(definition, ToolDefinition):
            raise ValueError(
                f"get_definition() must return ToolDefinition, got {type(definition)}"
            )

        # Get tool implementation
        if not hasattr(tool_class, "execute"):
            raise ValueError(f"Tool class {tool_class.__name__} missing execute()")

        execute_method = tool_class.execute
        if not (
            inspect.iscoroutinefunction(execute_method)
            or inspect.ismethod(execute_method)
        ):
            raise ValueError("execute() must be an async method or static method")

        # Register with registry
        self.registry.register_tool(
            tool_definition=definition,
            validate_schema=True,
            overwrite_existing=False,
        )

        # Register with executor
        self.executor.register_tool_implementation(
            tool_name=definition.name,
            implementation=execute_method,
        )

        self._loaded_tools.append(definition.name)
        logger.info("Registered built-in tool: %s", definition.name)

    def get_loaded_tools(self) -> List[str]:
        """Get list of loaded tool names.

        Returns:
            List of tool names
        """
        return self._loaded_tools.copy()

    def is_tool_loaded(self, tool_name: str) -> bool:
        """Check if a tool is loaded.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is loaded
        """
        return tool_name in self._loaded_tools
