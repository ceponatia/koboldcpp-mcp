"""Version information for KoboldCpp MCP Server"""

__version__ = "1.0.0"
__version_info__ = tuple(map(int, __version__.split(".")))

# Version components
MAJOR = 1
MINOR = 0
PATCH = 0

# Build metadata
BUILD_DATE = "2024-12-06"
BUILD_TYPE = "release"

# Compatibility information
MIN_PYTHON_VERSION = (3, 8)
MCP_PROTOCOL_VERSION = "2024-11-05"
KOBOLDCPP_MIN_VERSION = "1.45.0"

# Package metadata
PACKAGE_NAME = "koboldcpp-mcp-server"
PACKAGE_DESCRIPTION = "MCP server for KoboldCpp integration with Claude Code"
PACKAGE_AUTHOR = "Brian"
PACKAGE_LICENSE = "MIT"