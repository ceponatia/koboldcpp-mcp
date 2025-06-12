"""
KoboldCpp API Client

Handles communication with local KoboldCpp instance supporting both
OpenAI-compatible and native KoboldCpp endpoints for text generation,
chat completions, and model introspection.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass
import json
import time

from .config.settings import KoboldCppConfig, get_settings
from .protocol.message_types import (
    GenerateTextParams, ChatCompletionParams, ChatMessage,
    ModelInfo, GenerationResult, BatchRequest, BatchResult
)


@dataclass
class KoboldCppStatus:
    """KoboldCpp server status"""
    online: bool
    model_loaded: bool
    model_name: Optional[str] = None
    context_length: Optional[int] = None
    generation_active: bool = False


class KoboldCppClient:
    """Async client for KoboldCpp API communication"""
    
    def __init__(self, config: Optional[KoboldCppConfig] = None):
        self.config = config or get_settings().koboldcpp
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        self._request_semaphore = asyncio.Semaphore(get_settings().performance.max_concurrent_requests)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"Content-Type": "application/json"}
            )
            self.logger.info(f"Connected to KoboldCpp at {self.config.url}")
    
    async def disconnect(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("Disconnected from KoboldCpp")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.session:
            await self.connect()
        
        url = f"{self.config.url.rstrip('/')}{endpoint}"
        max_retries = retries if retries is not None else self.config.max_retries
        
        async with self._request_semaphore:
            for attempt in range(max_retries + 1):
                try:
                    async with self.session.request(method, url, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result
                        elif response.status in (502, 503, 504):  # Server errors, retry
                            if attempt < max_retries:
                                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                                continue
                        
                        # Non-retryable error
                        error_text = await response.text()
                        raise aiohttp.ClientError(
                            f"HTTP {response.status}: {error_text}"
                        )
                
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt < max_retries:
                        self.logger.warning(
                            f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                        continue
                    raise
        
        raise aiohttp.ClientError(f"Failed after {max_retries + 1} attempts")
    
    async def check_status(self) -> KoboldCppStatus:
        """Check KoboldCpp server status and model state"""
        try:
            # Try to get generation status
            status_data = await self._make_request("GET", self.config.status_endpoint)
            
            # Try to get model info
            model_data = None
            try:
                model_data = await self._make_request("GET", self.config.model_endpoint)
            except Exception:
                pass  # Model endpoint might not be available
            
            return KoboldCppStatus(
                online=True,
                model_loaded=status_data.get("ready", False),
                model_name=model_data.get("model_name") if model_data else None,
                context_length=model_data.get("max_context_length") if model_data else None,
                generation_active=status_data.get("generating", False)
            )
        
        except Exception as e:
            self.logger.error(f"Failed to check KoboldCpp status: {e}")
            return KoboldCppStatus(online=False, model_loaded=False)
    
    async def get_model_info(self) -> ModelInfo:
        """Get detailed model information"""
        try:
            data = await self._make_request("GET", self.config.model_endpoint)
            
            return ModelInfo(
                model_name=data.get("model_name", "unknown"),
                context_length=data.get("max_context_length", 2048),
                vocab_size=data.get("vocab_size"),
                parameters=data.get("parameters"),
                architecture=data.get("architecture"),
                format=data.get("format")
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get model info: {e}")
            raise
    
    async def generate_text(self, params: GenerateTextParams) -> GenerationResult:
        """Generate text using KoboldCpp native API"""
        start_time = time.time()
        
        # Prepare request data for KoboldCpp format
        request_data = {
            "prompt": params.prompt,
            "max_context_length": params.max_tokens,
            "max_length": params.max_tokens,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "top_k": params.top_k,
            "typical": params.typical_p,
            "rep_pen": params.rep_pen,
            "rep_pen_range": params.rep_pen_range,
            "sampler_order": [6, 0, 1, 3, 4, 2, 5],  # Default KoboldCpp sampler order
            "stop_sequence": params.stop_sequence or [],
            "stream": params.stream
        }
        
        try:
            # Handle non-streaming response
            response = await self._make_request("POST", self.config.generate_endpoint, request_data)
            
            generation_time = time.time() - start_time
            generated_text = response.get("results", [{}])[0].get("text", "")
            tokens_generated = len(generated_text.split())  # Rough estimate
            
            return GenerationResult(
                text=generated_text,
                tokens_generated=tokens_generated,
                generation_time=generation_time,
                tokens_per_second=tokens_generated / generation_time if generation_time > 0 else 0,
                finish_reason="stop"
            )
        
        except Exception as e:
            self.logger.error(f"Text generation failed: {e}")
            raise
    
    async def _stream_generate(self, request_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Handle streaming text generation"""
        if not self.session:
            await self.connect()
        
        url = f"{self.config.url.rstrip('/')}{self.config.generate_endpoint}"
        
        async with self.session.post(url, json=request_data) as response:
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode('utf-8').strip())
                        if "token" in data:
                            yield data["token"]
                    except json.JSONDecodeError:
                        continue
    
    async def chat_completion(self, params: ChatCompletionParams) -> GenerationResult:
        """Generate chat completion using OpenAI-compatible endpoint"""
        start_time = time.time()
        
        # Convert to OpenAI format
        request_data = {
            "model": "koboldcpp",  # Model name for compatibility
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in params.messages
            ],
            "max_tokens": params.max_tokens,
            "temperature": params.temperature,
            "top_p": params.top_p,
            "stream": params.stream
        }
        
        try:
            response = await self._make_request("POST", self.config.chat_endpoint, request_data)
            
            generation_time = time.time() - start_time
            
            # Extract response from OpenAI format
            choices = response.get("choices", [])
            if not choices:
                raise ValueError("No choices returned from chat completion")
            
            message = choices[0].get("message", {})
            generated_text = message.get("content", "")
            finish_reason = choices[0].get("finish_reason", "stop")
            
            # Estimate tokens (KoboldCpp might not return token count)
            tokens_generated = response.get("usage", {}).get("completion_tokens", len(generated_text.split()))
            
            return GenerationResult(
                text=generated_text,
                tokens_generated=tokens_generated,
                generation_time=generation_time,
                tokens_per_second=tokens_generated / generation_time if generation_time > 0 else 0,
                finish_reason=finish_reason
            )
        
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise
    
    async def batch_generate(self, batch_request: BatchRequest) -> BatchResult:
        """Process multiple prompts in batch with concurrency control"""
        start_time = time.time()
        results = []
        successful = 0
        failed = 0
        
        # Create semaphore for batch concurrency
        batch_semaphore = asyncio.Semaphore(batch_request.max_concurrent)
        
        async def process_single(prompt: str) -> Optional[GenerationResult]:
            """Process a single prompt with semaphore control"""
            async with batch_semaphore:
                try:
                    params = GenerateTextParams(prompt=prompt, **batch_request.parameters.model_dump())
                    result = await self.generate_text(params)
                    return result
                except Exception as e:
                    self.logger.error(f"Failed to process prompt: {e}")
                    return None
        
        # Process all prompts concurrently
        tasks = [process_single(prompt) for prompt in batch_request.prompts]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results and count successes/failures
        for result in batch_results:
            if isinstance(result, GenerationResult):
                results.append(result)
                successful += 1
            else:
                failed += 1
                # Add empty result for failed prompts to maintain order
                results.append(GenerationResult(
                    text="",
                    tokens_generated=0,
                    generation_time=0,
                    tokens_per_second=0,
                    finish_reason="error"
                ))
        
        total_time = time.time() - start_time
        
        return BatchResult(
            results=results,
            total_time=total_time,
            successful=successful,
            failed=failed
        )
    
    async def health_check(self) -> bool:
        """Simple health check for KoboldCpp server"""
        try:
            status = await self.check_status()
            return status.online
        except Exception:
            return False