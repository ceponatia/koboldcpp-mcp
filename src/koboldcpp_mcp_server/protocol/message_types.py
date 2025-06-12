"""
MCP Protocol Message Type Definitions

Implements the Model Context Protocol version 2024-11-05 message types
for communication between Claude Code and the KoboldCpp MCP server.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """MCP message types"""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    LIST_TOOLS = "list_tools"
    CALL_TOOL = "call_tool"
    LIST_RESOURCES = "list_resources"
    READ_RESOURCE = "read_resource"
    NOTIFICATION = "notification"
    ERROR = "error"


class MCPError(BaseModel):
    """MCP error structure"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPRequest(BaseModel):
    """Base MCP request message"""
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Base MCP response message"""
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None


class MCPNotification(BaseModel):
    """MCP notification message"""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


class ClientCapabilities(BaseModel):
    """Client capabilities for initialization"""
    experimental: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class ServerCapabilities(BaseModel):
    """Server capabilities declaration"""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    experimental: Optional[Dict[str, Any]] = None


class InitializeRequest(MCPRequest):
    """Initialize request from client"""
    method: Literal["initialize"] = "initialize"
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "claude-code",
            "version": "1.0.0"
        }
    })


class InitializeResponse(MCPResponse):
    """Initialize response from server"""
    result: Dict[str, Any] = Field(default_factory=lambda: {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True}
        },
        "serverInfo": {
            "name": "koboldcpp-mcp-server",
            "version": "1.0.0"
        }
    })


class ToolDefinition(BaseModel):
    """Tool definition for MCP"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class ToolCall(BaseModel):
    """Tool call parameters"""
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Tool execution result"""
    content: List[Dict[str, Any]]
    isError: bool = False


class ListToolsRequest(MCPRequest):
    """List available tools request"""
    method: Literal["tools/list"] = "tools/list"


class ListToolsResponse(MCPResponse):
    """List tools response"""
    result: Dict[str, List[ToolDefinition]]


class CallToolRequest(MCPRequest):
    """Call tool request"""
    method: Literal["tools/call"] = "tools/call"
    params: ToolCall


class CallToolResponse(MCPResponse):
    """Call tool response"""
    result: ToolResult


class ResourceDefinition(BaseModel):
    """Resource definition for MCP"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ListResourcesRequest(MCPRequest):
    """List available resources request"""
    method: Literal["resources/list"] = "resources/list"


class ListResourcesResponse(MCPResponse):
    """List resources response"""
    result: Dict[str, List[ResourceDefinition]]


class ReadResourceRequest(MCPRequest):
    """Read resource request"""
    method: Literal["resources/read"] = "resources/read"
    params: Dict[str, str]  # Contains "uri"


class ReadResourceResponse(MCPResponse):
    """Read resource response"""
    result: Dict[str, Any]


# KoboldCpp-specific message types

class GenerateTextParams(BaseModel):
    """Parameters for text generation"""
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    typical_p: float = 1.0
    rep_pen: float = 1.1
    rep_pen_range: int = 320
    stop_sequence: Optional[List[str]] = None
    stream: bool = False


class ChatMessage(BaseModel):
    """Chat message structure"""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatCompletionParams(BaseModel):
    """Parameters for chat completion"""
    messages: List[ChatMessage]
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False


class ModelInfo(BaseModel):
    """Model information structure"""
    model_name: str
    context_length: int
    vocab_size: Optional[int] = None
    parameters: Optional[str] = None
    architecture: Optional[str] = None
    format: Optional[str] = None


class GenerationResult(BaseModel):
    """Text generation result"""
    text: str
    tokens_generated: int
    generation_time: float
    tokens_per_second: float
    finish_reason: str


class BatchRequest(BaseModel):
    """Batch processing request"""
    prompts: List[str]
    parameters: GenerateTextParams
    max_concurrent: int = 3


class BatchResult(BaseModel):
    """Batch processing result"""
    results: List[GenerationResult]
    total_time: float
    successful: int
    failed: int