"""Tests for Tool Registry component."""

import pytest

from auto_pilot.tools.registry import SchemaValidator, ToolRegistry
from auto_pilot.tools.types.base import ToolDefinition, ToolMetadata, ToolSchema


class TestToolRegistry:
    """Test ToolRegistry class."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        assert registry is not None
        assert len(registry._tools) == 0

    def test_register_tool(self):
        """Test tool registration."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="A test tool",
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {"param1": {"type": "string"}},
                }
            ),
        )

        assert registry.register_tool(tool) is True
        assert tool.name in registry._tools

    def test_register_duplicate_tool(self):
        """Test registering duplicate tool raises error."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="A test tool",
                version="1.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool)

        with pytest.raises(ValueError):
            registry.register_tool(tool)

    def test_register_with_overwrite(self):
        """Test registering with overwrite flag."""
        registry = ToolRegistry()

        tool1 = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="Test tool 1",
                version="1.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        tool2 = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="Test tool 2",
                version="2.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool1)
        registry.register_tool(tool2, overwrite_existing=True)

        assert registry._tools["test_tool"].description == "Test tool 2"

    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="A test tool",
                version="1.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool)
        retrieved = registry.get_tool("test_tool")

        assert retrieved is not None
        assert retrieved.name == "test_tool"

    def test_get_nonexistent_tool(self):
        """Test getting a non-existent tool returns None."""
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None

    def test_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()

        tool1 = ToolDefinition(
            metadata=ToolMetadata(
                name="tool1",
                description="Test 1",
                version="1.0.0",
                category="cat1",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        tool2 = ToolDefinition(
            metadata=ToolMetadata(
                name="tool2",
                description="Test 2",
                version="1.0.0",
                category="cat2",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool1)
        registry.register_tool(tool2)

        tools = registry.list_tools()
        assert len(tools) == 2

    def test_list_tools_by_category(self):
        """Test listing tools by category."""
        registry = ToolRegistry()

        tool1 = ToolDefinition(
            metadata=ToolMetadata(
                name="tool1",
                description="Test 1",
                version="1.0.0",
                category="cat1",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        tool2 = ToolDefinition(
            metadata=ToolMetadata(
                name="tool2",
                description="Test 2",
                version="1.0.0",
                category="cat2",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool1)
        registry.register_tool(tool2)

        cat1_tools = registry.list_tools(category="cat1")
        assert len(cat1_tools) == 1
        assert cat1_tools[0].name == "tool1"

    def test_search_tools(self):
        """Test searching tools."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="searchable_tool",
                description="A tool for searching",
                version="1.0.0",
                tags=["search", "test"],
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool)

        results = registry.search_tools("search")
        assert len(results) == 1
        assert results[0].name == "searchable_tool"

    def test_deprecate_tool(self):
        """Test deprecating a tool."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="A test tool",
                version="1.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool)
        assert registry.deprecate_tool("test_tool", "Use new_tool instead") is True

        deprecated_tool = registry.get_tool("test_tool")
        assert deprecated_tool.metadata.deprecated is True
        assert deprecated_tool.metadata.deprecated_message == "Use new_tool instead"

    def test_remove_tool(self):
        """Test removing a tool."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="A test tool",
                version="1.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool)
        assert registry.remove_tool("test_tool") is True
        assert registry.get_tool("test_tool") is None

    def test_clear_registry(self):
        """Test clearing registry."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            metadata=ToolMetadata(
                name="test_tool",
                description="A test tool",
                version="1.0.0",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool)
        registry.clear_registry()

        assert len(registry._tools) == 0

    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        registry = ToolRegistry()

        tool1 = ToolDefinition(
            metadata=ToolMetadata(
                name="tool1",
                description="Test 1",
                version="1.0.0",
                category="cat1",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        tool2 = ToolDefinition(
            metadata=ToolMetadata(
                name="tool2",
                description="Test 2",
                version="2.0.0",
                category="cat2",
            ),
            parameters=ToolSchema(schema={"type": "object"}),
        )

        registry.register_tool(tool1)
        registry.register_tool(tool2)

        stats = registry.get_registry_stats()
        assert stats["total_tools"] == 2
        assert len(stats["categories"]) == 2


class TestSchemaValidator:
    """Test SchemaValidator class."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = SchemaValidator()
        assert validator is not None

    def test_validate_valid_schema(self):
        """Test validating a valid schema."""
        validator = SchemaValidator()

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

        assert validator.validate_tool_schema(schema) is True

    def test_validate_invalid_schema(self):
        """Test validating an invalid schema."""
        validator = SchemaValidator()

        schema = {
            "type": "invalid_type",
        }

        with pytest.raises(Exception):
            validator.validate_tool_schema(schema)

    def test_validate_parameters(self):
        """Test validating parameters against schema."""
        validator = SchemaValidator()

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }

        params = {"name": "John", "age": 30}
        assert validator.validate_parameters(schema, params) is True

    def test_validate_invalid_parameters(self):
        """Test validating invalid parameters."""
        validator = SchemaValidator()

        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "minimum": 0}},
        }

        params = {"age": -5}  # Invalid: negative age

        with pytest.raises(Exception):
            validator.validate_parameters(schema, params)

    def test_get_schema_errors(self):
        """Test getting schema validation errors."""
        validator = SchemaValidator()

        schema = {"type": 123}  # Invalid schema

        errors = validator.get_schema_errors(schema)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_get_parameter_errors(self):
        """Test getting parameter validation errors."""
        validator = SchemaValidator()

        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "minimum": 0}},
        }

        params = {"age": -5}

        errors = validator.get_parameter_errors(schema, params)
        assert isinstance(errors, list)
        assert len(errors) > 0
