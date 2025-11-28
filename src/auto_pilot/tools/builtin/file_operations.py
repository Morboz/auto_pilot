"""Built-in file operation tools."""

import logging
from pathlib import Path
from typing import Any, Dict

from ..types.base import ToolDefinition

logger = logging.getLogger(__name__)


class FileReadTool:
    """Read content from a file."""

    @staticmethod
    def get_definition() -> ToolDefinition:
        """Get tool definition for file reading."""
        from ..types.base import ToolMetadata, ToolSchema

        return ToolDefinition(
            metadata=ToolMetadata(
                name="file_read",
                description="Read the content of a file from the filesystem",
                category="file_operations",
                tags=["file", "read", "io"],
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read",
                        }
                    },
                    "required": ["file_path"],
                }
            ),
        )

    @staticmethod
    async def execute(file_path: str) -> Dict[str, Any]:
        """Execute file read operation.

        Args:
            file_path: Path to the file to read

        Returns:
            Dictionary with file content and metadata
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            content = path.read_text(encoding="utf-8")
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "path": str(path.absolute()),
            }
        except Exception as e:
            logger.error("Error reading file %s: %s", file_path, str(e))
            return {"success": False, "error": str(e)}


class FileWriteTool:
    """Write content to a file."""

    @staticmethod
    def get_definition() -> ToolDefinition:
        """Get tool definition for file writing."""
        from ..types.base import ToolMetadata, ToolSchema

        return ToolDefinition(
            metadata=ToolMetadata(
                name="file_write",
                description="Write content to a file on the filesystem",
                category="file_operations",
                tags=["file", "write", "io"],
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to write",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                        "create_dirs": {
                            "type": "boolean",
                            "description": "Create parent directories if they don't exist",
                            "default": True,
                        },
                    },
                    "required": ["file_path", "content"],
                }
            ),
        )

    @staticmethod
    async def execute(
        file_path: str, content: str, create_dirs: bool = True
    ) -> Dict[str, Any]:
        """Execute file write operation.

        Args:
            file_path: Path to the file to write
            content: Content to write
            create_dirs: Whether to create parent directories

        Returns:
            Dictionary with operation result
        """
        try:
            path = Path(file_path)

            # Create parent directories if needed
            if create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(path.absolute()),
                "bytes_written": len(content.encode("utf-8")),
            }
        except Exception as e:
            logger.error("Error writing file %s: %s", file_path, str(e))
            return {"success": False, "error": str(e)}


class FileListTool:
    """List files in a directory."""

    @staticmethod
    def get_definition() -> ToolDefinition:
        """Get tool definition for file listing."""
        from ..types.base import ToolMetadata, ToolSchema

        return ToolDefinition(
            metadata=ToolMetadata(
                name="file_list",
                description="List files and directories in a given path",
                category="file_operations",
                tags=["file", "list", "directory"],
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory path to list",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Optional glob pattern to filter files (e.g., '*.py')",
                            "default": "*",
                        },
                    },
                    "required": ["directory"],
                }
            ),
        )

    @staticmethod
    async def execute(directory: str, pattern: str = "*") -> Dict[str, Any]:
        """Execute directory listing operation.

        Args:
            directory: Directory path to list
            pattern: Glob pattern to filter files

        Returns:
            Dictionary with list of files
        """
        try:
            path = Path(directory)
            if not path.exists():
                return {"success": False, "error": f"Directory not found: {directory}"}

            if not path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {directory}",
                }

            # List files matching pattern
            files = []
            for item in path.glob(pattern):
                files.append(
                    {
                        "name": item.name,
                        "path": str(item.absolute()),
                        "is_file": item.is_file(),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )

            return {
                "success": True,
                "directory": str(path.absolute()),
                "pattern": pattern,
                "count": len(files),
                "files": files,
            }
        except Exception as e:
            logger.error("Error listing directory %s: %s", directory, str(e))
            return {"success": False, "error": str(e)}
