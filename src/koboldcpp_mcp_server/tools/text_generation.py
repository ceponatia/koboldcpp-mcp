"""
Text Generation Tools

Implements MCP tools for text generation, chat completion, and prompt testing
using the KoboldCpp client for local AI inference.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import json

from ..kobold_client import KoboldCppClient
from ..protocol.message_types import (
    GenerateTextParams, ChatCompletionParams, ChatMessage,
    BatchRequest, ToolDefinition, GenerationResult
)
from ..config.settings import get_settings


class TextGenerationTools:
    """Collection of text generation tools for MCP"""
    
    def __init__(self, kobold_client: KoboldCppClient):
        self.client = kobold_client
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
    
    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions for MCP registration"""
        return [
            self._get_generate_tool_definition(),
            self._get_chat_tool_definition(),
            self._get_prompt_test_tool_definition(),
            self._get_batch_generate_tool_definition(),
        ]
    
    def _get_generate_tool_definition(self) -> ToolDefinition:
        """Tool definition for text generation"""
        return ToolDefinition(
            name="generate_text",
            description="Generate text using KoboldCpp with configurable parameters. Supports various sampling methods and stopping conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The text prompt to generate from"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum number of tokens to generate",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 4096
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0 to 2.0)",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 2.0
                    },
                    "top_p": {
                        "type": "number",
                        "description": "Nucleus sampling parameter",
                        "default": 0.9,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Top-k sampling parameter",
                        "default": 40,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "typical_p": {
                        "type": "number",
                        "description": "Typical sampling parameter",
                        "default": 1.0,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "rep_pen": {
                        "type": "number",
                        "description": "Repetition penalty",
                        "default": 1.1,
                        "minimum": 1.0,
                        "maximum": 2.0
                    },
                    "rep_pen_range": {
                        "type": "integer",
                        "description": "Repetition penalty range",
                        "default": 320,
                        "minimum": 0,
                        "maximum": 2048
                    },
                    "stop_sequence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of strings that will stop generation",
                        "default": []
                    }
                },
                "required": ["prompt"]
            }
        )
    
    def _get_chat_tool_definition(self) -> ToolDefinition:
        """Tool definition for chat completion"""
        return ToolDefinition(
            name="chat_completion",
            description="Generate chat completion using conversation format. Supports multi-turn conversations with system, user, and assistant messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["system", "user", "assistant"],
                                    "description": "The role of the message sender"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "The message content"
                                }
                            },
                            "required": ["role", "content"]
                        },
                        "description": "List of conversation messages"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 4096
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 2.0
                    },
                    "top_p": {
                        "type": "number",
                        "description": "Nucleus sampling parameter",
                        "default": 0.9,
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["messages"]
            }
        )
    
    def _get_prompt_test_tool_definition(self) -> ToolDefinition:
        """Tool definition for prompt testing"""
        return ToolDefinition(
            name="test_prompt",
            description="Test a prompt with multiple parameter variations to find optimal settings. Useful for prompt engineering and optimization.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to test"
                    },
                    "temperature_range": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of temperature values to test",
                        "default": [0.3, 0.7, 1.0]
                    },
                    "top_p_range": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of top_p values to test",
                        "default": [0.8, 0.9, 0.95]
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens per test",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 1024
                    }
                },
                "required": ["prompt"]
            }
        )
    
    def _get_batch_generate_tool_definition(self) -> ToolDefinition:
        """Tool definition for batch generation"""
        return ToolDefinition(
            name="batch_generate",
            description="Generate text for multiple prompts efficiently with controlled concurrency. Useful for processing large datasets or document analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of prompts to process"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens per generation",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 2048
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 2.0
                    },
                    "max_concurrent": {
                        "type": "integer",
                        "description": "Maximum concurrent requests",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["prompts"]
            }
        )
    
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        typical_p: float = 1.0,
        rep_pen: float = 1.1,
        rep_pen_range: int = 320,
        stop_sequence: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using KoboldCpp"""
        
        # Validate and sanitize input
        if self.settings.security.data_sanitization:
            prompt = self._sanitize_prompt(prompt)
        
        if len(prompt) > self.settings.security.max_prompt_length:
            raise ValueError(f"Prompt exceeds maximum length of {self.settings.security.max_prompt_length}")
        
        try:
            params = GenerateTextParams(
                prompt=prompt,
                max_tokens=min(max_tokens, self.settings.security.max_response_length),
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                typical_p=typical_p,
                rep_pen=rep_pen,
                rep_pen_range=rep_pen_range,
                stop_sequence=stop_sequence or []
            )
            
            result = await self.client.generate_text(params)
            
            return {
                "type": "text",
                "text": result.text,
                "metadata": {
                    "tokens_generated": result.tokens_generated,
                    "generation_time": result.generation_time,
                    "tokens_per_second": result.tokens_per_second,
                    "finish_reason": result.finish_reason,
                    "parameters_used": params.model_dump()
                }
            }
        
        except Exception as e:
            self.logger.error(f"Text generation failed: {e}")
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion"""
        
        try:
            # Convert message format
            chat_messages = []
            for msg in messages:
                if self.settings.security.data_sanitization:
                    content = self._sanitize_prompt(msg["content"])
                else:
                    content = msg["content"]
                
                chat_messages.append(ChatMessage(
                    role=msg["role"],
                    content=content
                ))
            
            params = ChatCompletionParams(
                messages=chat_messages,
                max_tokens=min(max_tokens, self.settings.security.max_response_length),
                temperature=temperature,
                top_p=top_p
            )
            
            result = await self.client.chat_completion(params)
            
            return {
                "type": "text",
                "text": result.text,
                "metadata": {
                    "tokens_generated": result.tokens_generated,
                    "generation_time": result.generation_time,
                    "tokens_per_second": result.tokens_per_second,
                    "finish_reason": result.finish_reason,
                    "conversation_length": len(messages)
                }
            }
        
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise
    
    async def test_prompt(
        self,
        prompt: str,
        temperature_range: List[float] = None,
        top_p_range: List[float] = None,
        max_tokens: int = 50,
        **kwargs
    ) -> Dict[str, Any]:
        """Test prompt with multiple parameter variations"""
        
        temperature_range = temperature_range or [0.3, 0.7, 1.0]
        top_p_range = top_p_range or [0.8, 0.9, 0.95]
        
        results = []
        
        try:
            for temp in temperature_range:
                for top_p in top_p_range:
                    params = GenerateTextParams(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temp,
                        top_p=top_p
                    )
                    
                    result = await self.client.generate_text(params)
                    
                    results.append({
                        "temperature": temp,
                        "top_p": top_p,
                        "generated_text": result.text,
                        "tokens_generated": result.tokens_generated,
                        "generation_time": result.generation_time,
                        "tokens_per_second": result.tokens_per_second
                    })
            
            # Find best result based on tokens per second and length
            best_result = max(results, key=lambda x: x["tokens_per_second"])
            
            return {
                "type": "text",
                "text": f"Prompt testing completed with {len(results)} variations",
                "metadata": {
                    "test_results": results,
                    "best_configuration": {
                        "temperature": best_result["temperature"],
                        "top_p": best_result["top_p"],
                        "performance": best_result["tokens_per_second"]
                    },
                    "total_tests": len(results)
                }
            }
        
        except Exception as e:
            self.logger.error(f"Prompt testing failed: {e}")
            raise
    
    async def batch_generate(
        self,
        prompts: List[str],
        max_tokens: int = 100,
        temperature: float = 0.7,
        max_concurrent: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text for multiple prompts in batch"""
        
        if len(prompts) > 50:  # Reasonable limit for batch processing
            raise ValueError("Too many prompts in batch (maximum 50)")
        
        try:
            # Sanitize prompts if enabled
            if self.settings.security.data_sanitization:
                prompts = [self._sanitize_prompt(p) for p in prompts]
            
            params = GenerateTextParams(
                prompt="",  # Will be overridden for each prompt
                max_tokens=min(max_tokens, self.settings.security.max_response_length),
                temperature=temperature
            )
            
            batch_request = BatchRequest(
                prompts=prompts,
                parameters=params,
                max_concurrent=min(max_concurrent, self.settings.performance.max_concurrent_requests)
            )
            
            batch_result = await self.client.batch_generate(batch_request)
            
            # Format results
            formatted_results = []
            for i, result in enumerate(batch_result.results):
                formatted_results.append({
                    "prompt_index": i,
                    "generated_text": result.text,
                    "tokens_generated": result.tokens_generated,
                    "generation_time": result.generation_time,
                    "success": result.finish_reason != "error"
                })
            
            return {
                "type": "text",
                "text": f"Batch generation completed: {batch_result.successful} successful, {batch_result.failed} failed",
                "metadata": {
                    "results": formatted_results,
                    "total_time": batch_result.total_time,
                    "successful": batch_result.successful,
                    "failed": batch_result.failed,
                    "total_prompts": len(prompts)
                }
            }
        
        except Exception as e:
            self.logger.error(f"Batch generation failed: {e}")
            raise
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize prompt for security and compliance"""
        # Remove potential injection patterns
        sanitized = prompt.replace("</s>", "").replace("<|endoftext|>", "")
        
        # Truncate if too long
        max_length = self.settings.security.max_prompt_length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized