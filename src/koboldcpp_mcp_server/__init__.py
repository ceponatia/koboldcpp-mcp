"""
KoboldCpp MCP Server

A Model Context Protocol (MCP) server that enables Claude Code to interact
with local KoboldCpp instances for AI capabilities while maintaining complete
data privacy and control.

This package provides:
- WebSocket-based MCP server implementation
- KoboldCpp API client for text generation and chat completions
- Configuration management and security features
- Command-line interface for server management

Designed specifically for government and legal environments requiring
privacy, compliance, and audit logging capabilities.
"""

from .__version__ import (
    __version__,
    __version_info__,
    MCP_PROTOCOL_VERSION,
    KOBOLDCPP_MIN_VERSION,
    PACKAGE_NAME,
    PACKAGE_DESCRIPTION,
)

from .server import MCPServer
from .kobold_client import KoboldCppClient, KoboldCppStatus
from .config.settings import get_settings, setup_logging

__all__ = [
    "__version__",
    "__version_info__",
    "MCP_PROTOCOL_VERSION",
    "KOBOLDCPP_MIN_VERSION",
    "PACKAGE_NAME", 
    "PACKAGE_DESCRIPTION",
    "MCPServer",
    "KoboldCppClient",
    "KoboldCppStatus",
    "get_settings",
    "setup_logging",
]

# Package metadata
__author__ = "Brian"
__license__ = "MIT"
__maintainer__ = "Brian"
__email__ = ""
__status__ = "Production"