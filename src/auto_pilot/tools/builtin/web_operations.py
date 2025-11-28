"""Built-in web operation tools."""

import logging
from typing import Any, Dict, Optional

import aiohttp

from ..types.base import ToolDefinition

logger = logging.getLogger(__name__)


class HttpGetTool:
    """Perform HTTP GET requests."""

    @staticmethod
    def get_definition() -> ToolDefinition:
        """Get tool definition for HTTP GET."""
        from ..types.base import ToolMetadata, ToolSchema

        return ToolDefinition(
            metadata=ToolMetadata(
                name="http_get",
                description="Perform an HTTP GET request to fetch data from a URL",
                category="web_operations",
                tags=["http", "get", "web", "api"],
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to send the GET request to",
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers to include in the request",
                            "additionalProperties": {"type": "string"},
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Request timeout in seconds",
                            "default": 30,
                        },
                    },
                    "required": ["url"],
                }
            ),
        )

    @staticmethod
    async def execute(
        url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute HTTP GET request.

        Args:
            url: URL to request
            headers: Optional HTTP headers
            timeout: Request timeout in seconds

        Returns:
            Dictionary with response data
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    content = await response.text()
                    return {
                        "success": True,
                        "status_code": response.status,
                        "content": content,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                    }
        except aiohttp.ClientError as e:
            logger.error("HTTP GET error for %s: %s", url, str(e))
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}",
                "error_type": "client_error",
            }
        except Exception as e:
            logger.error("Unexpected error in HTTP GET for %s: %s", url, str(e))
            return {"success": False, "error": str(e), "error_type": "unexpected_error"}


class HttpPostTool:
    """Perform HTTP POST requests."""

    @staticmethod
    def get_definition() -> ToolDefinition:
        """Get tool definition for HTTP POST."""
        from ..types.base import ToolMetadata, ToolSchema

        return ToolDefinition(
            metadata=ToolMetadata(
                name="http_post",
                description="Perform an HTTP POST request to send data to a URL",
                category="web_operations",
                tags=["http", "post", "web", "api"],
                version="1.0.0",
            ),
            parameters=ToolSchema(
                schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to send the POST request to",
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body data (will be sent as JSON)",
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers to include in the request",
                            "additionalProperties": {"type": "string"},
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Request timeout in seconds",
                            "default": 30,
                        },
                    },
                    "required": ["url", "body"],
                }
            ),
        )

    @staticmethod
    async def execute(
        url: str,
        body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute HTTP POST request.

        Args:
            url: URL to request
            body: Request body (JSON)
            headers: Optional HTTP headers
            timeout: Request timeout in seconds

        Returns:
            Dictionary with response data
        """
        try:
            # Set default content-type if not provided
            if headers is None:
                headers = {}
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    content = await response.text()
                    return {
                        "success": True,
                        "status_code": response.status,
                        "content": content,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                    }
        except aiohttp.ClientError as e:
            logger.error("HTTP POST error for %s: %s", url, str(e))
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}",
                "error_type": "client_error",
            }
        except Exception as e:
            logger.error("Unexpected error in HTTP POST for %s: %s", url, str(e))
            return {"success": False, "error": str(e), "error_type": "unexpected_error"}
