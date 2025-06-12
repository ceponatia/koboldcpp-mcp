"""
MCP Protocol Handler

Implements the Model Context Protocol version 2024-11-05 for handling
WebSocket communication between Claude Code and the KoboldCpp MCP server.
"""

import asyncio
import json
import logging
import traceback
from typing import Dict, Any, Optional, List, Callable, Union
import websockets
from websockets.server import WebSocketServerProtocol

from .message_types import (
    MCPRequest, MCPResponse, MCPNotification, MCPError,
    InitializeRequest, InitializeResponse,
    ListToolsRequest, ListToolsResponse, ToolDefinition,
    CallToolRequest, CallToolResponse, ToolResult,
    ListResourcesRequest, ListResourcesResponse, ResourceDefinition,
    ReadResourceRequest, ReadResourceResponse,
    MessageType
)
from ..config.settings import get_settings


class MCPHandler:
    """Handles MCP protocol communication and message routing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        self.tools: Dict[str, Callable] = {}
        self.resources: Dict[str, Callable] = {}
        self.initialized = False
        self.client_capabilities: Dict[str, Any] = {}
    
    def register_tool(self, name: str, handler: Callable, definition: ToolDefinition) -> None:
        """Register a tool handler"""
        self.tools[name] = {
            "handler": handler,
            "definition": definition
        }
        self.logger.info(f"Registered tool: {name}")
    
    def register_resource(self, uri: str, handler: Callable, definition: ResourceDefinition) -> None:
        """Register a resource handler"""
        self.resources[uri] = {
            "handler": handler,
            "definition": definition
        }
        self.logger.info(f"Registered resource: {uri}")
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle new WebSocket connection"""
        client_addr = websocket.remote_address
        self.logger.info(f"New MCP connection from {client_addr}")
        
        try:
            async for message in websocket:
                try:
                    await self._process_message(websocket, message)
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    error_response = self._create_error_response(
                        None, -32603, f"Internal error: {str(e)}"
                    )
                    await websocket.send(json.dumps(error_response.model_dump()))
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"MCP connection closed: {client_addr}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            self.initialized = False
    
    async def _process_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """Process incoming MCP message"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            error_response = self._create_error_response(
                None, -32700, f"Parse error: {str(e)}"
            )
            await websocket.send(json.dumps(error_response.model_dump()))
            return
        
        # Handle notifications (no response expected)
        if "id" not in data:
            await self._handle_notification(websocket, data)
            return
        
        # Handle requests (response expected)
        try:
            request = MCPRequest(**data)
            response = await self._handle_request(request)
            await websocket.send(json.dumps(response.model_dump()))
        
        except Exception as e:
            self.logger.error(f"Request handling error: {e}")
            error_response = self._create_error_response(
                data.get("id"), -32603, f"Internal error: {str(e)}"
            )
            await websocket.send(json.dumps(error_response.model_dump()))
    
    async def _handle_notification(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle MCP notifications"""
        try:
            notification = MCPNotification(**data)
            method = notification.method
            
            if method == "notifications/initialized":
                self.logger.info("Client initialization complete")
            else:
                self.logger.warning(f"Unknown notification method: {method}")
        
        except Exception as e:
            self.logger.error(f"Notification handling error: {e}")
    
    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Route and handle MCP requests"""
        method = request.method
        request_id = request.id
        
        try:
            if method == "initialize":
                return await self._handle_initialize(request)
            elif method == "tools/list":
                return await self._handle_list_tools(request)
            elif method == "tools/call":
                return await self._handle_call_tool(request)
            elif method == "resources/list":
                return await self._handle_list_resources(request)
            elif method == "resources/read":
                return await self._handle_read_resource(request)
            else:
                return self._create_error_response(
                    request_id, -32601, f"Method not found: {method}"
                )
        
        except Exception as e:
            self.logger.error(f"Request handler error for {method}: {e}")
            return self._create_error_response(
                request_id, -32603, f"Internal error: {str(e)}"
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialization request"""
        params = request.params or {}
        
        # Validate protocol version
        protocol_version = params.get("protocolVersion")
        if protocol_version != "2024-11-05":
            return self._create_error_response(
                request.id, -32602, 
                f"Unsupported protocol version: {protocol_version}"
            )
        
        # Store client capabilities
        self.client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        self.logger.info(f"Initializing MCP session with {client_info.get('name', 'unknown')} v{client_info.get('version', 'unknown')}")
        
        # Mark as initialized
        self.initialized = True
        
        # Return server capabilities
        response = InitializeResponse(id=request.id)
        return response
    
    async def _handle_list_tools(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list request"""
        if not self.initialized:
            return self._create_error_response(
                request.id, -32002, "Server not initialized"
            )
        
        tool_definitions = [
            tool_info["definition"] for tool_info in self.tools.values()
        ]
        
        response = ListToolsResponse(
            id=request.id,
            result={"tools": tool_definitions}
        )
        return response
    
    async def _handle_call_tool(self, request: CallToolRequest) -> MCPResponse:
        """Handle tools/call request"""
        if not self.initialized:
            return self._create_error_response(
                request.id, -32002, "Server not initialized"
            )
        
        tool_name = request.params.name
        arguments = request.params.arguments
        
        if tool_name not in self.tools:
            return self._create_error_response(
                request.id, -32601, f"Tool not found: {tool_name}"
            )
        
        try:
            # Call the tool handler
            tool_info = self.tools[tool_name]
            handler = tool_info["handler"]
            
            # Execute tool with audit logging if enabled
            if self.settings.logging.audit_log:
                audit_logger = logging.getLogger('audit')
                audit_logger.info(f"TOOL_CALL: {tool_name} with args: {arguments}")
            
            result = await handler(**arguments)
            
            # Ensure result is in correct format
            if isinstance(result, dict):
                tool_result = ToolResult(content=[result])
            elif isinstance(result, list):
                tool_result = ToolResult(content=result)
            else:
                tool_result = ToolResult(content=[{"type": "text", "text": str(result)}])
            
            response = CallToolResponse(
                id=request.id,
                result=tool_result
            )
            return response
        
        except Exception as e:
            self.logger.error(f"Tool execution error for {tool_name}: {e}")
            error_result = ToolResult(
                content=[{"type": "text", "text": f"Tool execution failed: {str(e)}"}],
                isError=True
            )
            response = CallToolResponse(
                id=request.id,
                result=error_result
            )
            return response
    
    async def _handle_list_resources(self, request: MCPRequest) -> MCPResponse:
        """Handle resources/list request"""
        if not self.initialized:
            return self._create_error_response(
                request.id, -32002, "Server not initialized"
            )
        
        resource_definitions = [
            resource_info["definition"] for resource_info in self.resources.values()
        ]
        
        response = ListResourcesResponse(
            id=request.id,
            result={"resources": resource_definitions}
        )
        return response
    
    async def _handle_read_resource(self, request: ReadResourceRequest) -> MCPResponse:
        """Handle resources/read request"""
        if not self.initialized:
            return self._create_error_response(
                request.id, -32002, "Server not initialized"
            )
        
        uri = request.params.get("uri")
        if not uri:
            return self._create_error_response(
                request.id, -32602, "Missing required parameter: uri"
            )
        
        if uri not in self.resources:
            return self._create_error_response(
                request.id, -32601, f"Resource not found: {uri}"
            )
        
        try:
            # Call the resource handler
            resource_info = self.resources[uri]
            handler = resource_info["handler"]
            
            result = await handler(uri)
            
            response = ReadResourceResponse(
                id=request.id,
                result=result
            )
            return response
        
        except Exception as e:
            self.logger.error(f"Resource read error for {uri}: {e}")
            return self._create_error_response(
                request.id, -32603, f"Resource read failed: {str(e)}"
            )
    
    def _create_error_response(
        self, 
        request_id: Optional[Union[str, int]], 
        code: int, 
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """Create an error response"""
        error = MCPError(code=code, message=message, data=data)
        return MCPResponse(id=request_id, error=error)
    
    def get_server_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities for initialization"""
        return {
            "tools": {"listChanged": True},
            "resources": {"listChanged": True},
            "experimental": {}
        }
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": "koboldcpp-mcp-server",
            "version": "1.0.0",
            "description": "MCP server for KoboldCpp integration"
        }