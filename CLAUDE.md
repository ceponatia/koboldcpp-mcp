# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that enables Claude Code to interact with local KoboldCpp instances. The primary goal is to provide AI capabilities through local model inference while maintaining complete data privacy and control, specifically designed for government and legal environments.

## Reference
Koboldcpp wiki at https://github.com/LostRuins/koboldcpp/wiki should be referenced for usage

## Architecture

### Core Components

1. **MCP Server** (`src/server.py`) - Main WebSocket-based server implementing MCP protocol version 2024-11-05
2. **KoboldCpp Client** (`src/kobold_client.py`) - API client for communicating with local KoboldCpp instance (default: http://localhost:5001)
3. **Protocol Layer** (`src/protocol/`) - MCP protocol implementation and message type definitions
4. **Tools Layer** (`src/tools/`) - Text generation, model introspection, and batch processing capabilities
5. **Configuration** (`src/config/`) - Settings management for server and integration configuration

### Data Flow

```
Claude Code → MCP Protocol → Server → KoboldCpp Client → Local KoboldCpp Instance
```

All processing remains local with no external API calls for privacy/compliance requirements.

### Key Integration Points

- **KoboldCpp API**: Supports both OpenAI-compatible and native KoboldCpp endpoints
- **Claude Code**: Configured via `config/claude_code_config.json` with environment variables for KOBOLD_URL, LOG_LEVEL, and AUDIT_LOG
- **Government Systems**: Designed for integration with Axon Evidence and Karpel PbK systems

## Development Commands

### Running the Server
```bash
# Basic server startup
python3 src/server.py

# With environment configuration
KOBOLD_URL=http://localhost:5001 LOG_LEVEL=INFO AUDIT_LOG=true python3 src/server.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python -m pytest tests/test_mcp_protocol.py
python -m pytest tests/test_kobold_client.py
python -m pytest tests/test_integration.py

# Run single test
python -m pytest tests/test_mcp_protocol.py::TestMCPProtocol::test_specific_function
```

### KoboldCpp Setup
```bash
# Start KoboldCpp for development/testing
koboldcpp --model your_model.gguf --port 5001 --threads 8
```

## Implementation Priorities

### Phase 1: Core MCP Server
- WebSocket-based MCP protocol implementation in `src/protocol/mcp_handler.py`
- Basic KoboldCpp API integration in `src/kobold_client.py`
- Text generation and chat completion tools in `src/tools/text_generation.py`
- Configuration management in `src/config/settings.py`

### Phase 2: Advanced Features
- Model introspection and format detection in `src/tools/model_info.py`
- Batch processing capabilities in `src/tools/batch_processing.py`
- Performance monitoring and error handling enhancements

### Phase 3: Government Integration
- Audit logging for compliance requirements
- Security enhancements and authentication
- Integration hooks for external systems

## Configuration

### MCP Server Config (`config/mcp_server_config.json`)
- Server port and WebSocket settings
- KoboldCpp connection parameters
- Logging and audit configuration

### Claude Code Integration (`config/claude_code_config.json`)
- MCP server command and arguments
- Environment variables for runtime configuration
- Integration-specific settings

## Performance Requirements

- Response time < 2 seconds for typical requests
- Memory usage under 500MB for server process
- Support for models up to 13B parameters
- 99%+ uptime during business hours

## Security Considerations

- All processing remains local (no external API calls)
- Audit logging for government compliance
- Data sanitization for sensitive information
- Configurable authentication mechanisms