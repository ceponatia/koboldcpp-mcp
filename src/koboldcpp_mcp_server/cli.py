#!/usr/bin/env python3
"""
Command Line Interface for KoboldCpp MCP Server

Provides command-line tools for managing and running the MCP server,
including configuration validation, health checks, and server management.
"""

import argparse
import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional

from .__version__ import __version__, MCP_PROTOCOL_VERSION
from .config.settings import get_settings, setup_logging, validate_koboldcpp_connection
from .server import MCPServer
from .kobold_client import KoboldCppClient


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        prog="koboldcpp-mcp",
        description="KoboldCpp MCP Server - Connect Claude Code to local KoboldCpp instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  koboldcpp-mcp server                    # Start the MCP server
  koboldcpp-mcp check                     # Check KoboldCpp connection
  koboldcpp-mcp config validate          # Validate configuration
  koboldcpp-mcp config show              # Show current configuration
  koboldcpp-mcp --version                # Show version information

Environment Variables:
  KOBOLD_URL                   KoboldCpp server URL (default: http://localhost:5001)
  MCP_HOST                     MCP server host (default: localhost)
  MCP_PORT                     MCP server port (default: 8765)
  LOG_LEVEL                    Logging level (default: INFO)
  AUDIT_LOG                    Enable audit logging (default: false)

For detailed documentation, visit:
https://github.com/ceponatia/koboldcpp-mcp
        """
    )
    
    # Global options
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"KoboldCpp MCP Server {__version__} (MCP Protocol {MCP_PROTOCOL_VERSION})"
    )
    parser.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Server command
    server_parser = subparsers.add_parser(
        "server",
        help="Start the MCP server",
        description="Start the KoboldCpp MCP server for Claude Code integration"
    )
    server_parser.add_argument(
        "--host",
        type=str,
        metavar="HOST",
        help="Server host (overrides config)"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        metavar="PORT",
        help="Server port (overrides config)"
    )
    server_parser.add_argument(
        "--kobold-url",
        type=str,
        metavar="URL",
        help="KoboldCpp server URL (overrides config)"
    )
    
    # Check command
    check_parser = subparsers.add_parser(
        "check",
        help="Check KoboldCpp connection",
        description="Verify connection to KoboldCpp server and check status"
    )
    check_parser.add_argument(
        "--url",
        type=str,
        metavar="URL",
        help="KoboldCpp server URL to check"
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="Manage server configuration"
    )
    config_subparsers = config_parser.add_subparsers(dest="config_action", help="Config actions")
    
    # Config validate
    config_subparsers.add_parser(
        "validate",
        help="Validate configuration",
        description="Validate current configuration settings"
    )
    
    # Config show
    config_subparsers.add_parser(
        "show",
        help="Show configuration",
        description="Display current configuration settings"
    )
    
    # Config init
    init_parser = config_subparsers.add_parser(
        "init",
        help="Initialize configuration",
        description="Create default configuration files"
    )
    init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing configuration files"
    )
    
    return parser


async def cmd_server(args: argparse.Namespace) -> int:
    """Start the MCP server"""
    try:
        # Override settings with command line arguments
        settings = get_settings()
        
        if args.host:
            settings.mcp_server.host = args.host
        if args.port:
            settings.mcp_server.port = args.port
        if args.kobold_url:
            settings.koboldcpp.url = args.kobold_url
        
        server = MCPServer()
        await server.start()
        return 0
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1


async def cmd_check(args: argparse.Namespace) -> int:
    """Check KoboldCpp connection"""
    try:
        settings = get_settings()
        if args.url:
            settings.koboldcpp.url = args.url
        
        # Validate configuration
        if not validate_koboldcpp_connection(settings.koboldcpp):
            print("❌ Invalid KoboldCpp configuration", file=sys.stderr)
            return 1
        
        print(f"Checking KoboldCpp connection to {settings.koboldcpp.url}...")
        
        # Test connection
        async with KoboldCppClient(settings.koboldcpp) as client:
            status = await client.check_status()
            
            if status.online:
                print("✅ KoboldCpp server is online")
                
                if status.model_loaded:
                    print(f"✅ Model loaded: {status.model_name or 'Unknown'}")
                    if status.context_length:
                        print(f"   Context length: {status.context_length}")
                else:
                    print("⚠️  No model loaded")
                
                if status.generation_active:
                    print("ℹ️  Generation currently active")
                
                # Try to get detailed model info
                try:
                    model_info = await client.get_model_info()
                    print(f"   Architecture: {model_info.architecture or 'Unknown'}")
                    print(f"   Format: {model_info.format or 'Unknown'}")
                    if model_info.parameters:
                        print(f"   Parameters: {model_info.parameters}")
                except Exception:
                    pass  # Model info endpoint might not be available
                
                return 0
            else:
                print("❌ KoboldCpp server is not responding")
                return 1
                
    except Exception as e:
        print(f"❌ Connection check failed: {e}", file=sys.stderr)
        return 1


def cmd_config_validate(args: argparse.Namespace) -> int:
    """Validate configuration"""
    try:
        settings = get_settings()
        
        print("Validating configuration...")
        
        # Validate KoboldCpp settings
        if validate_koboldcpp_connection(settings.koboldcpp):
            print("✅ KoboldCpp configuration is valid")
        else:
            print("❌ Invalid KoboldCpp configuration")
            return 1
        
        # Validate MCP server settings
        if settings.mcp_server.port < 1 or settings.mcp_server.port > 65535:
            print("❌ Invalid MCP server port")
            return 1
        print("✅ MCP server configuration is valid")
        
        # Validate security settings
        if settings.security.max_prompt_length <= 0:
            print("❌ Invalid security settings")
            return 1
        print("✅ Security configuration is valid")
        
        print("✅ All configuration is valid")
        return 0
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}", file=sys.stderr)
        return 1


def cmd_config_show(args: argparse.Namespace) -> int:
    """Show current configuration"""
    try:
        settings = get_settings()
        
        print("Current Configuration:")
        print("=" * 50)
        
        config_dict = settings.model_dump()
        print(json.dumps(config_dict, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to show configuration: {e}", file=sys.stderr)
        return 1


def cmd_config_init(args: argparse.Namespace) -> int:
    """Initialize configuration files"""
    try:
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # Create default config file
        config_file = config_dir / "mcp_server_config.json"
        
        if config_file.exists() and not args.overwrite:
            print(f"Configuration file already exists: {config_file}")
            print("Use --overwrite to replace it")
            return 1
        
        # Get default settings and save them
        settings = get_settings()
        with open(config_file, 'w') as f:
            json.dump(settings.model_dump(), f, indent=2)
        
        print(f"✅ Created configuration file: {config_file}")
        
        # Create Claude Code config template
        claude_config = config_dir / "claude_code_config.json"
        claude_template = {
            "mcpServers": {
                "koboldcpp": {
                    "command": "python3",
                    "args": [str(Path.cwd() / "src" / "server.py")],
                    "env": {
                        "KOBOLD_URL": "http://localhost:5001",
                        "LOG_LEVEL": "INFO",
                        "AUDIT_LOG": "false"
                    }
                }
            }
        }
        
        if not claude_config.exists() or args.overwrite:
            with open(claude_config, 'w') as f:
                json.dump(claude_template, f, indent=2)
            print(f"✅ Created Claude Code config template: {claude_config}")
        
        print("\nNext steps:")
        print("1. Start KoboldCpp: koboldcpp --model your_model.gguf --port 5001")
        print("2. Configure Claude Code with the generated config file")
        print("3. Start the MCP server: koboldcpp-mcp server")
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to initialize configuration: {e}", file=sys.stderr)
        return 1


async def async_main() -> int:
    """Async main function"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Setup logging based on verbosity
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Handle config file override
    if args.config:
        os.environ["MCP_CONFIG_FILE"] = args.config
    
    # Route to appropriate command
    if args.command == "server":
        return await cmd_server(args)
    elif args.command == "check":
        return await cmd_check(args)
    elif args.command == "config":
        if args.config_action == "validate":
            return cmd_config_validate(args)
        elif args.config_action == "show":
            return cmd_config_show(args)
        elif args.config_action == "init":
            return cmd_config_init(args)
        else:
            parser.print_help()
            return 1
    else:
        # Default to server if no command specified
        return await cmd_server(args)


def main() -> int:
    """Main entry point"""
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())