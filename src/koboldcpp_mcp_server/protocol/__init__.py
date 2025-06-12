"""
MCP Protocol Package

Implements Model Context Protocol version 2024-11-05 for WebSocket communication
between Claude Code and the KoboldCpp MCP server.
"""

from .message_types import *
from .mcp_handler import MCPHandler

__all__ = [
    'MCPHandler',
    'MCPRequest',
    'MCPResponse',
    'MCPNotification',
    'InitializeRequest',
    'InitializeResponse',
    'ToolDefinition',
    'CallToolRequest',
    'CallToolResponse',
    'ResourceDefinition',
    'ListToolsRequest',
    'ListToolsResponse',
    'ListResourcesRequest',
    'ListResourcesResponse'
]