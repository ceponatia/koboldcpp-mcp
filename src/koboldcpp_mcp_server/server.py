#!/usr/bin/env python3
"""
KoboldCpp MCP Server

Main WebSocket-based MCP server implementing Model Context Protocol version 2024-11-05
for enabling Claude Code to interact with local KoboldCpp instances.

Designed for government and legal environments requiring privacy, compliance, and audit logging.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional
import websockets
from websockets.server import WebSocketServerProtocol

from .config.settings import get_settings, setup_logging
from .protocol.mcp_handler import MCPHandler
from .protocol.message_types import ToolDefinition, ResourceDefinition
from .kobold_client import KoboldCppClient
from .tools.text_generation import TextGenerationTools


class MCPServer:
    """Main MCP server class"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.mcp_handler = MCPHandler()
        self.kobold_client: Optional[KoboldCppClient] = None
        self.text_tools: Optional[TextGenerationTools] = None
        self.server = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize server components"""
        # Setup logging
        setup_logging(self.settings.logging)
        self.logger.info("Initializing KoboldCpp MCP Server")
        
        # Initialize KoboldCpp client
        self.kobold_client = KoboldCppClient(self.settings.koboldcpp)
        await self.kobold_client.connect()
        
        # Check KoboldCpp connection
        if not await self.kobold_client.health_check():
            self.logger.warning(f"KoboldCpp server at {self.settings.koboldcpp.url} is not responding")
        else:
            self.logger.info(f"Connected to KoboldCpp at {self.settings.koboldcpp.url}")
        
        # Initialize tools
        self.text_tools = TextGenerationTools(self.kobold_client)
        
        # Register tools with MCP handler
        await self._register_tools()
        
        # Register resources with MCP handler
        await self._register_resources()
        
        self.logger.info("Server initialization complete")
    
    async def _register_tools(self) -> None:
        """Register all tools with the MCP handler"""
        if not self.text_tools:
            return
        
        tool_definitions = self.text_tools.get_tool_definitions()
        
        for tool_def in tool_definitions:
            if tool_def.name == "generate_text":
                self.mcp_handler.register_tool(
                    tool_def.name,
                    self.text_tools.generate_text,
                    tool_def
                )
            elif tool_def.name == "chat_completion":
                self.mcp_handler.register_tool(
                    tool_def.name,
                    self.text_tools.chat_completion,
                    tool_def
                )
            elif tool_def.name == "test_prompt":
                self.mcp_handler.register_tool(
                    tool_def.name,
                    self.text_tools.test_prompt,
                    tool_def
                )
            elif tool_def.name == "batch_generate":
                self.mcp_handler.register_tool(
                    tool_def.name,
                    self.text_tools.batch_generate,
                    tool_def
                )
        
        self.logger.info(f"Registered {len(tool_definitions)} tools")
    
    async def _register_resources(self) -> None:
        """Register resources with the MCP handler"""
        
        # Model info resource
        model_info_def = ResourceDefinition(
            uri="koboldcpp://model/info",
            name="Model Information",
            description="Current KoboldCpp model information and capabilities",
            mimeType="application/json"
        )
        
        self.mcp_handler.register_resource(
            model_info_def.uri,
            self._get_model_info,
            model_info_def
        )
        
        # Server status resource
        status_def = ResourceDefinition(
            uri="koboldcpp://server/status",
            name="Server Status",
            description="KoboldCpp server status and health information",
            mimeType="application/json"
        )
        
        self.mcp_handler.register_resource(
            status_def.uri,
            self._get_server_status,
            status_def
        )
        
        self.logger.info("Registered 2 resources")
    
    async def _get_model_info(self, uri: str) -> Dict[str, Any]:
        """Get model information resource"""
        try:
            if not self.kobold_client:
                raise RuntimeError("KoboldCpp client not initialized")
            
            model_info = await self.kobold_client.get_model_info()
            
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": model_info.model_dump_json(indent=2)
                }]
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get model info: {e}")
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": f'{{"error": "Failed to get model info: {str(e)}"}}'
                }]
            }
    
    async def _get_server_status(self, uri: str) -> Dict[str, Any]:
        """Get server status resource"""
        try:
            if not self.kobold_client:
                raise RuntimeError("KoboldCpp client not initialized")
            
            status = await self.kobold_client.check_status()
            
            status_data = {
                "online": status.online,
                "model_loaded": status.model_loaded,
                "model_name": status.model_name,
                "context_length": status.context_length,
                "generation_active": status.generation_active,
                "server_url": self.settings.koboldcpp.url
            }
            
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": str(status_data).replace("'", '"')  # Convert to JSON format
                }]
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get server status: {e}")
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": f'{{"error": "Failed to get server status: {str(e)}"}}'
                }]
            }
    
    async def start(self) -> None:
        """Start the MCP server"""
        await self.initialize()
        
        host = self.settings.mcp_server.host
        port = self.settings.mcp_server.port
        
        self.logger.info(f"Starting MCP server on {host}:{port}")
        
        # Create WebSocket server
        self.server = await websockets.serve(
            self.mcp_handler.handle_connection,
            host,
            port,
            ping_interval=self.settings.mcp_server.ping_interval,
            ping_timeout=self.settings.mcp_server.ping_timeout,
            max_size=2**20,  # 1MB max message size
            max_queue=self.settings.mcp_server.max_connections
        )
        
        self.logger.info(f"MCP server running on ws://{host}:{port}")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
    
    async def stop(self) -> None:
        """Stop the MCP server"""
        self.logger.info("Shutting down MCP server")
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        if self.kobold_client:
            await self.kobold_client.disconnect()
        
        self._shutdown_event.set()
        self.logger.info("MCP server stopped")
    
    def handle_signal(self, signame: str) -> None:
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signame}, shutting down")
        asyncio.create_task(self.stop())


async def main():
    """Main entry point"""
    server = MCPServer()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for signame in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda s=signame: server.handle_signal(s)
            )
        except NotImplementedError:
            # Signal handling not available on Windows
            pass
    
    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()
    except Exception as e:
        logging.error(f"Server error: {e}")
        await server.stop()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)