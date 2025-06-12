"""
Configuration management for KoboldCpp MCP Server

Handles settings from environment variables, JSON config files,
and provides defaults for all configuration options.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field


class KoboldCppConfig(BaseModel):
    """KoboldCpp connection configuration"""
    url: str = Field(default="http://localhost:5001", description="KoboldCpp server URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    # API endpoints
    generate_endpoint: str = Field(default="/api/v1/generate", description="Text generation endpoint")
    chat_endpoint: str = Field(default="/api/v1/chat/completions", description="Chat completion endpoint")
    model_endpoint: str = Field(default="/api/v1/model", description="Model info endpoint")
    status_endpoint: str = Field(default="/api/extra/generate/check", description="Status check endpoint")


class MCPServerConfig(BaseModel):
    """MCP server configuration"""
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8765, description="Server port")
    max_connections: int = Field(default=10, description="Maximum concurrent connections")
    ping_interval: Optional[int] = Field(default=20, description="WebSocket ping interval")
    ping_timeout: Optional[int] = Field(default=10, description="WebSocket ping timeout")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    audit_log: bool = Field(default=False, description="Enable audit logging for compliance")
    audit_file: str = Field(default="audit.log", description="Audit log file path")


class SecurityConfig(BaseModel):
    """Security and compliance configuration"""
    enable_auth: bool = Field(default=False, description="Enable authentication")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"], description="Allowed CORS origins")
    data_sanitization: bool = Field(default=True, description="Enable data sanitization")
    max_prompt_length: int = Field(default=8192, description="Maximum prompt length")
    max_response_length: int = Field(default=4096, description="Maximum response length")


class PerformanceConfig(BaseModel):
    """Performance and resource configuration"""
    max_concurrent_requests: int = Field(default=5, description="Maximum concurrent requests to KoboldCpp")
    request_queue_size: int = Field(default=100, description="Request queue size")
    memory_limit_mb: int = Field(default=500, description="Memory limit in MB")
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")


class Settings(BaseModel):
    """Complete application settings"""
    koboldcpp: KoboldCppConfig = Field(default_factory=KoboldCppConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)


class SettingsManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/mcp_server_config.json"
        self._settings: Optional[Settings] = None
    
    def load_settings(self) -> Settings:
        """Load settings from environment variables and config file"""
        if self._settings is not None:
            return self._settings
        
        # Start with defaults
        config_data = {}
        
        # Load from JSON config file if it exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load config file {self.config_path}: {e}")
        
        # Override with environment variables
        env_overrides = self._get_env_overrides()
        config_data = self._merge_config(config_data, env_overrides)
        
        # Create and validate settings
        self._settings = Settings(**config_data)
        return self._settings
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        env_mapping = {
            # KoboldCpp settings
            "KOBOLD_URL": ("koboldcpp", "url"),
            "KOBOLD_TIMEOUT": ("koboldcpp", "timeout"),
            "KOBOLD_MAX_RETRIES": ("koboldcpp", "max_retries"),
            
            # MCP Server settings
            "MCP_HOST": ("mcp_server", "host"),
            "MCP_PORT": ("mcp_server", "port"),
            "MCP_MAX_CONNECTIONS": ("mcp_server", "max_connections"),
            
            # Logging settings
            "LOG_LEVEL": ("logging", "level"),
            "AUDIT_LOG": ("logging", "audit_log"),
            "AUDIT_FILE": ("logging", "audit_file"),
            
            # Security settings
            "ENABLE_AUTH": ("security", "enable_auth"),
            "AUTH_TOKEN": ("security", "auth_token"),
            "MAX_PROMPT_LENGTH": ("security", "max_prompt_length"),
            
            # Performance settings
            "MAX_CONCURRENT_REQUESTS": ("performance", "max_concurrent_requests"),
            "MEMORY_LIMIT_MB": ("performance", "memory_limit_mb"),
        }
        
        overrides = {}
        for env_var, (section, key) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(value)
                if section not in overrides:
                    overrides[section] = {}
                overrides[section][key] = converted_value
        
        return overrides
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _merge_config(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration dictionaries"""
        result = base.copy()
        for section, values in overrides.items():
            if section not in result:
                result[section] = {}
            result[section].update(values)
        return result
    
    def save_settings(self, settings: Settings) -> None:
        """Save settings to config file"""
        config_dir = Path(self.config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(settings.model_dump(), f, indent=2)
    
    def reload_settings(self) -> Settings:
        """Reload settings from file and environment"""
        self._settings = None
        return self.load_settings()


# Global settings manager instance
settings_manager = SettingsManager()


def get_settings() -> Settings:
    """Get current application settings"""
    return settings_manager.load_settings()


def setup_logging(logging_config: LoggingConfig) -> None:
    """Setup logging configuration"""
    level = getattr(logging, logging_config.level.upper(), logging.INFO)
    
    # Configure basic logging
    logging.basicConfig(
        level=level,
        format=logging_config.format,
        handlers=[logging.StreamHandler()]
    )
    
    # Setup audit logging if enabled
    if logging_config.audit_log:
        audit_logger = logging.getLogger('audit')
        audit_handler = logging.FileHandler(logging_config.audit_file)
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s'
        ))
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)


def validate_koboldcpp_connection(config: KoboldCppConfig) -> bool:
    """Validate KoboldCpp connection configuration"""
    # Basic URL validation
    if not config.url.startswith(('http://', 'https://')):
        return False
    
    # Validate timeout and retry settings
    if config.timeout <= 0 or config.max_retries < 0:
        return False
    
    return True