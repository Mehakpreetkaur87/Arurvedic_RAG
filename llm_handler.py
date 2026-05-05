"""
================================================================================
LLM HANDLER - Google Gemini API + Ollama Local Fallback
================================================================================
Manages LLM interactions with primary (Gemini) and fallback (Ollama) models.

Features:
- Automatic fallback if primary LLM fails
- Streaming responses for real-time UI updates
- Rate limiting and error handling
- Response caching for similar queries
- Configurable parameters (temperature, max_tokens, etc.)

Architecture:
    Query + Context → LLM Selection → Fallback Strategy →
    Response Generation → Streaming → Response Storage

Support Versions:
- Google Gemini API (primary, cloud-based)
- Ollama Local (fallback, offline capability)

Author: RAG System
Version: 1.0
================================================================================
"""

import os
import requests
import json
import logging
from typing import Generator, Optional, Dict, Tuple
from datetime import datetime, timedelta
import time
from abc import ABC, abstractmethod

# LLM Libraries
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError

# Utilities
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
PRIMARY_LLM = os.getenv('PRIMARY_LLM', 'gemini')
FALLBACK_LLM = os.getenv('FALLBACK_LLM', 'ollama')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

MAX_TOKENS = int(os.getenv('MAX_TOKENS', 2000))
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
TOP_P = float(os.getenv('TOP_P', 0.9))

ENABLE_STREAMING = os.getenv('ENABLE_STREAMING', 'true').lower() == 'true'
STREAM_CHUNK_SIZE = int(os.getenv('STREAM_CHUNK_SIZE', 50))

GEMINI_RATE_LIMIT = int(os.getenv('GEMINI_REQUESTS_PER_MINUTE', 15))
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT_SECONDS', 120))

DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# ============================================================================
# RATE LIMITER - Manage API request limits
# ============================================================================

class RateLimiter:
    """
    Rate limiter for API calls.
    
    Purpose: Prevent hitting API rate limits
    
    Example:
        - Gemini free tier: 15 requests/minute
        - Rate limiter: Queue requests, add delays
    """
    
    def __init__(self, requests_per_minute: int = 15):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests = requests_per_minute
        self.window = 60  # seconds
        self.request_times = []
    
    def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        
        # Remove old requests outside the time window
        self.request_times = [t for t in self.request_times if now - t < self.window]
        
        # If at limit, wait
        if len(self.request_times) >= self.max_requests:
            sleep_time = self.window - (now - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        # Record this request
        self.request_times.append(time.time())


# ============================================================================
# ABSTRACT LLM BASE CLASS
# ============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: str = "",
        **kwargs
    ) -> str:
        """Generate response."""
        pass
    
    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        context: str = "",
        **kwargs
    ) -> Generator:
        """Generate response with streaming."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


# ============================================================================
# GOOGLE GEMINI LLM PROVIDER
# ============================================================================

class GeminiLLM(LLMProvider):
    """
    Google Gemini API Integration.
    
    What: Google's latest AI model API
    
    Model: gemini-2.0-flash
        - Free tier available
        - Fast response generation
        - Good quality answers
        - Rate limited (15 req/min free)
    
    Pros:
        - State-of-the-art quality
        - Free tier (15 req/min)
        - Fast responses
        - Good for production
    
    Cons:
        - Requires internet
        - Rate limited on free tier
        - API key required
        - May have cost for high usage
    
    Usage:
        1. Get API key from: https://makersuite.google.com/app/apikey
        2. Set GEMINI_API_KEY in .env
        3. Gemini is automatically tried first
    """
    
    def __init__(self):
        """Initialize Gemini LLM."""
        logger.info("Initializing Google Gemini API")
        
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. Gemini will not be available.")
            self.available = False
            return
        
        try:
            # Configure Gemini API
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Initialize model
            self.model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                )
            )
            
            # Rate limiter for Gemini
            self.rate_limiter = RateLimiter(GEMINI_RATE_LIMIT)
            
            # Test connection
            self._test_connection()
            
            self.available = True
            logger.info("Gemini LLM initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.available = False
    
    def _test_connection(self) -> bool:
        """Test if Gemini API is accessible."""
        try:
            response = self.model.generate_content(
                "Hello",
                stream=False
            )
            return response is not None
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return self.available
    
    def generate(
        self,
        prompt: str,
        context: str = "",
        **kwargs
    ) -> str:
        """
        Generate response using Gemini API.
        
        Args:
            prompt: User prompt/query
            context: Retrieved context from knowledge base
            
        Returns:
            Generated response string
        """
        if not self.available:
            raise RuntimeError("Gemini is not available")
        
        # Rate limit
        self.rate_limiter.acquire()
        
        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, context)
        
        logger.info(f"Generating response with Gemini ({len(full_prompt)} chars)")
        
        try:
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                stream=False
            )
            
            if response.text:
                return response.text
            else:
                logger.warning("Gemini returned empty response")
                return "Unable to generate response."
        
        except ResourceExhausted:
            logger.error("Gemini rate limit exceeded")
            raise
        except InternalServerError as e:
            logger.error(f"Gemini server error: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        context: str = "",
        **kwargs
    ) -> Generator:
        """
        Generate response with streaming (real-time chunks).
        
        Yields response text in chunks for real-time UI updates.
        
        Args:
            prompt: User prompt/query
            context: Retrieved context from knowledge base
            
        Yields:
            Text chunks as they're generated
        """
        if not self.available:
            raise RuntimeError("Gemini is not available")
        
        # Rate limit
        self.rate_limiter.acquire()
        
        # Build full prompt
        full_prompt = self._build_prompt(prompt, context)
        
        logger.info(f"Streaming response with Gemini ({len(full_prompt)} chars)")
        
        try:
            # Stream response
            response = self.model.generate_content(
                full_prompt,
                stream=True
            )
            
            # Yield text chunks
            accumulated = ""
            for chunk in response:
                if chunk.text:
                    accumulated += chunk.text
                    
                    # Yield every STREAM_CHUNK_SIZE characters
                    if len(accumulated) >= STREAM_CHUNK_SIZE:
                        yield accumulated
                        accumulated = ""
            
            # Yield remaining
            if accumulated:
                yield accumulated
        
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            yield f"Error during streaming: {str(e)}"
    
    @staticmethod
    def _build_prompt(prompt: str, context: str) -> str:
        """
        Build complete prompt for Gemini.
        
        Combines user prompt with retrieved context.
        
        Args:
            prompt: Original user query
            context: Retrieved documents context
            
        Returns:
            Full prompt for Gemini
        """
        system_prompt = """You are an Ayurveda (ancient Indian medicine) expert. 
Provide accurate, helpful information about Ayurvedic treatments, remedies, and health concepts.
Base your answers primarily on the provided context.
If the context doesn't contain relevant information, acknowledge this limitation.
Be respectful of cultural context while providing scientific explanations where applicable.
"""
        
        if context:
            prompt_text = f"""{system_prompt}

---CONTEXT FROM KNOWLEDGE BASE---
{context}
---END CONTEXT---

USER QUESTION:
{prompt}

ANSWER:"""
        else:
            prompt_text = f"""{system_prompt}

USER QUESTION:
{prompt}

ANSWER:"""
        
        return prompt_text


# ============================================================================
# OLLAMA LOCAL LLM PROVIDER
# ============================================================================

class OllamaLLM(LLMProvider):
    """
    Ollama Local LLM Integration.
    
    What: Run open-source LLMs locally on your machine
    
    Models Available:
    - llama2 (7B): Good balance, ~4GB VRAM
    - mistral (7B): Faster, good quality
    - neural-chat (7B): Optimized for chat
    - dolphin-mixtral (22B): Larger, better quality, needs ~16GB
    
    Pros:
        - Complete privacy (no data sent to cloud)
        - No rate limits
        - Works offline
        - Free (no API costs)
        - Customizable models
    
    Cons:
        - Slower responses (depends on hardware)
        - Lower quality than commercial APIs
        - Requires model download (~4-8GB)
        - Needs more system resources
    
    Setup:
        1. Install Ollama: https://ollama.ai
        2. Download model: ollama pull llama2
        3. Start service: ollama serve
        4. Verify: curl http://localhost:11434/api/tags
    
    Usage:
        - Automatic fallback when Gemini fails
        - Or set PRIMARY_LLM=ollama in .env
    """
    
    def __init__(self):
        """Initialize Ollama LLM."""
        logger.info(f"Initializing Ollama at {OLLAMA_BASE_URL}")
        
        self.base_url = OLLAMA_BASE_URL
        self.model = "llama2"  # Default model
        self.available = self._check_availability()
        
        if self.available:
            # Get available models
            models = self._get_available_models()
            if models:
                self.model = models[0]  # Use first available model
                logger.info(f"Using Ollama model: {self.model}")
            logger.info("Ollama LLM initialized successfully")
        else:
            logger.warning("Ollama is not available at the configured endpoint")
    
    def _check_availability(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def _get_available_models(self) -> list:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                models = [m['name'].split(':')[0] for m in data.get('models', [])]
                return models
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
        return []
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return self.available
    
    def generate(
        self,
        prompt: str,
        context: str = "",
        **kwargs
    ) -> str:
        """
        Generate response using Ollama.
        
        Args:
            prompt: User prompt/query
            context: Retrieved context from knowledge base
            
        Returns:
            Generated response string
        """
        if not self.available:
            raise RuntimeError("Ollama is not available")
        
        # Build full prompt
        full_prompt = self._build_prompt(prompt, context)
        
        logger.info(f"Generating response with Ollama ({self.model})")
        
        try:
            # Make request to Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": TEMPERATURE,
                        "top_p": TOP_P,
                        "num_predict": MAX_TOKENS,
                    }
                },
                timeout=OLLAMA_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', 'No response generated')
            else:
                logger.error(f"Ollama returned status {response.status_code}")
                raise RuntimeError(f"Ollama error: {response.status_code}")
        
        except requests.exceptions.Timeout:
            logger.error("Ollama request timeout")
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        context: str = "",
        **kwargs
    ) -> Generator:
        """
        Generate response with streaming (real-time chunks).
        
        Args:
            prompt: User prompt/query
            context: Retrieved context from knowledge base
            
        Yields:
            Text chunks as they're generated
        """
        if not self.available:
            raise RuntimeError("Ollama is not available")
        
        # Build full prompt
        full_prompt = self._build_prompt(prompt, context)
        
        logger.info(f"Streaming response with Ollama ({self.model})")
        
        try:
            # Make streaming request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "temperature": TEMPERATURE,
                        "top_p": TOP_P,
                        "num_predict": MAX_TOKENS,
                    }
                },
                stream=True,
                timeout=OLLAMA_TIMEOUT
            )
            
            # Yield chunks as they arrive
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            yield chunk['response']
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            yield f"Error during streaming: {str(e)}"
    
    @staticmethod
    def _build_prompt(prompt: str, context: str) -> str:
        """
        Build complete prompt for Ollama.
        
        Args:
            prompt: Original user query
            context: Retrieved documents context
            
        Returns:
            Full prompt for Ollama
        """
        system_prompt = """You are an Ayurveda (ancient Indian medicine) expert. 
Provide accurate, helpful information about Ayurvedic treatments, remedies, and health concepts.
Base your answers primarily on the provided context.
If the context doesn't contain relevant information, acknowledge this limitation."""
        
        if context:
            prompt_text = f"""{system_prompt}

CONTEXT:
{context}

QUESTION:
{prompt}

ANSWER:"""
        else:
            prompt_text = f"""{system_prompt}

QUESTION:
{prompt}

ANSWER:"""
        
        return prompt_text


# ============================================================================
# LLM MANAGER - Primary + Fallback Strategy
# ============================================================================

class LLMManager:
    """
    Manage LLM selection and fallback strategy.
    
    Strategy:
    1. Try primary LLM (configured in PRIMARY_LLM)
    2. If fails, automatically try fallback
    3. Log failures for monitoring
    4. Return response or error message
    
    Example:
        PRIMARY_LLM=gemini
        FALLBACK_LLM=ollama
        
        - Attempt: Gemini API
        - If fails (rate limit, no internet, etc.)
        - Fallback: Ollama local
        - Result: User gets answer either way
    """
    
    def __init__(self):
        """Initialize all LLM providers."""
        logger.info("Initializing LLM Manager")
        
        # Initialize providers
        self.gemini = GeminiLLM()
        self.ollama = OllamaLLM()
        
        # Get primary and fallback
        self.primary_name = PRIMARY_LLM.lower()
        self.fallback_name = FALLBACK_LLM.lower()
        
        # Map names to providers
        self.providers = {
            'gemini': self.gemini,
            'ollama': self.ollama
        }
        
        # Get actual provider objects
        try:
            self.primary = self.providers[self.primary_name]
        except KeyError:
            logger.error(f"Unknown primary LLM: {self.primary_name}")
            self.primary = self.gemini  # Default fallback
        
        try:
            self.fallback = self.providers[self.fallback_name]
        except KeyError:
            logger.error(f"Unknown fallback LLM: {self.fallback_name}")
            self.fallback = self.ollama  # Default fallback
        
        logger.info(
            f"Primary: {self.primary_name} ({self.primary.__class__.__name__})"
        )
        logger.info(
            f"Fallback: {self.fallback_name} ({self.fallback.__class__.__name__})"
        )
    
    def generate(
        self,
        prompt: str,
        context: str = ""
    ) -> Tuple[str, str]:
        """
        Generate response with fallback strategy.
        
        Tries primary LLM, falls back to secondary if needed.
        
        Args:
            prompt: User query
            context: Retrieved context
            
        Returns:
            Tuple of (response_text, llm_used)
        """
        # Try primary
        if self.primary.is_available():
            try:
                logger.info(f"Attempting with primary LLM: {self.primary_name}")
                response = self.primary.generate(prompt, context)
                logger.info(f"Successfully generated with {self.primary_name}")
                return response, self.primary_name
            except Exception as e:
                logger.warning(
                    f"Primary LLM ({self.primary_name}) failed: {e}\n"
                    f"Attempting fallback..."
                )
        else:
            logger.warning(f"Primary LLM ({self.primary_name}) not available")
        
        # Try fallback
        if self.fallback.is_available():
            try:
                logger.info(f"Attempting with fallback LLM: {self.fallback_name}")
                response = self.fallback.generate(prompt, context)
                logger.info(f"Successfully generated with {self.fallback_name}")
                return response, self.fallback_name
            except Exception as e:
                logger.error(f"Fallback LLM ({self.fallback_name}) also failed: {e}")
        else:
            logger.error(f"Fallback LLM ({self.fallback_name}) not available")
        
        # Both failed
        error_msg = (
            "Unable to generate response. Both primary and fallback LLMs are unavailable.\n"
            "Please check:\n"
            "1. GEMINI_API_KEY is set (for Google Gemini)\n"
            "2. Ollama is running (ollama serve)\n"
            "3. Internet connection (for Gemini)\n"
        )
        logger.error(error_msg)
        return error_msg, "error"
    
    def generate_stream(
        self,
        prompt: str,
        context: str = ""
    ) -> Generator:
        """
        Generate streaming response with fallback strategy.
        
        Args:
            prompt: User query
            context: Retrieved context
            
        Yields:
            Response chunks
        """
        # Try primary
        if self.primary.is_available():
            try:
                logger.info(f"Streaming with primary LLM: {self.primary_name}")
                for chunk in self.primary.generate_stream(prompt, context):
                    yield chunk
                return
            except Exception as e:
                logger.warning(
                    f"Primary LLM ({self.primary_name}) failed: {e}\n"
                    f"Attempting fallback..."
                )
        
        # Try fallback
        if self.fallback.is_available():
            try:
                logger.info(f"Streaming with fallback LLM: {self.fallback_name}")
                for chunk in self.fallback.generate_stream(prompt, context):
                    yield chunk
                return
            except Exception as e:
                logger.error(f"Fallback LLM ({self.fallback_name}) also failed: {e}")
        
        # Both failed
        yield (
            "Unable to generate response. Both primary and fallback LLMs are unavailable.\n"
            "Please check configuration and availability."
        )


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global LLM manager instance
_llm_manager: Optional[LLMManager] = None

def get_llm_manager() -> LLMManager:
    """Get or create global LLM manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


# ============================================================================
# MODULE TEST
# ============================================================================

if __name__ == "__main__":
    print("LLM Handler module loaded successfully")
    
    manager = get_llm_manager()
    
    # Test
    print("\nTesting LLM availability:")
    print(f"  Gemini available: {manager.gemini.is_available()}")
    print(f"  Ollama available: {manager.ollama.is_available()}")
    
    if manager.gemini.is_available() or manager.ollama.is_available():
        print("\nLLM systems ready for use")
    else:
        print("\nWarning: No LLM systems available")
        print("Please check:")
        print("  1. GEMINI_API_KEY in .env (for Google Gemini)")
        print("  2. ollama serve is running (for Ollama)")
