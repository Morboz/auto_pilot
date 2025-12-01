"""Schema validation utilities for tool definitions."""

from typing import Any, Dict

from jsonschema import Draft202012Validator, ValidationError, validate


class SchemaValidator:
    """JSON Schema validator for tool definitions."""

    def __init__(self):
        """Initialize the schema validator."""
        self.validator = Draft202012Validator

    def validate_tool_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate a tool schema against JSON Schema Draft 2020-12.

        Args:
            schema: The JSON schema to validate

        Returns:
            True if schema is valid

        Raises:
            ValidationError: If schema is invalid
        """
        try:
            # First, validate that the schema itself is a valid JSON Schema
            self.validator.check_schema(schema)
            return True
        except Exception as e:
            raise ValidationError(f"Invalid JSON Schema: {str(e)}")

    def validate_parameters(self, schema: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """Validate parameters against a tool schema.

        Args:
            schema: The JSON schema to validate against
            parameters: The parameters to validate

        Returns:
            True if parameters are valid

        Raises:
            ValidationError: If parameters are invalid
        """
        try:
            validate(instance=parameters, schema=schema, cls=self.validator)
            return True
        except ValidationError as e:
            raise ValidationError(f"Parameter validation failed: {str(e)}")

    def validate_schema_structure(self, schema: Dict[str, Any]) -> bool:
        """Validate basic schema structure.

        Args:
            schema: The schema to validate

        Returns:
            True if structure is valid

        Raises:
            ValidationError: If structure is invalid
        """
        if not isinstance(schema, dict):
            raise ValidationError("Schema must be a dictionary")

        # Check for required fields
        if "type" not in schema:
            raise ValidationError("Schema must have a 'type' field")

        if schema.get("type") == "object":
            if "properties" not in schema:
                raise ValidationError("Object schema must have 'properties' field")
            if not isinstance(schema["properties"], dict):
                raise ValidationError("Schema 'properties' must be a dictionary")

        return True

    def get_schema_errors(self, schema: Dict[str, Any]) -> list:
        """Get detailed schema validation errors.

        Args:
            schema: The schema to validate

        Returns:
            List of validation errors
        """
        errors = []
        try:
            self.validator.check_schema(schema)
        except Exception as e:
            errors.append(str(e))
        return errors

    def get_parameter_errors(self, schema: Dict[str, Any], parameters: Dict[str, Any]) -> list:
        """Get detailed parameter validation errors.

        Args:
            schema: The JSON schema to validate against
            parameters: The parameters to validate

        Returns:
            List of validation errors
        """
        errors = []
        validator = self.validator(schema)
        for error in validator.iter_errors(parameters):
            errors.append(f"{'.'.join(str(x) for x in error.path)}: {error.message}")
        return errors
