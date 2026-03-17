"""
LLM-based crime information extraction with Cerebras API and Ollama fallback
"""
import json
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import httpx
import ollama
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter for Cerebras API"""
    
    def __init__(self):
        # Track requests for both models
        self.gpt_oss_requests = []  # (timestamp, tokens)
        self.llama_requests = []    # (timestamp, tokens)
        
        # Limits per minute
        self.gpt_oss_rpm = 30
        self.gpt_oss_tpm = 64000
        self.llama_rpm = 30
        self.llama_tpm = 60000
        
        # Current model
        self.current_model = "llama3.1-8b"  # Start with smaller model
        self.fallback_to_ollama = False
    
    def _clean_old_requests(self, requests_list):
        """Remove requests older than 1 minute"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        return [(ts, tokens) for ts, tokens in requests_list if ts > cutoff]
    
    def _get_current_usage(self, requests_list):
        """Get current minute usage"""
        requests_list = self._clean_old_requests(requests_list)
        request_count = len(requests_list)
        token_count = sum(tokens for _, tokens in requests_list)
        return request_count, token_count
    
    async def wait_if_needed(self, estimated_tokens: int = 2000):
        """Wait if rate limit would be exceeded"""
        if self.fallback_to_ollama:
            return "ollama"
        
        # Clean old requests
        self.gpt_oss_requests = self._clean_old_requests(self.gpt_oss_requests)
        self.llama_requests = self._clean_old_requests(self.llama_requests)
        
        # Check current model
        if self.current_model == "llama3.1-8b":
            req_count, token_count = self._get_current_usage(self.llama_requests)
            
            # Check if we can use llama
            if req_count < self.llama_rpm and (token_count + estimated_tokens) < self.llama_tpm:
                self.llama_requests.append((datetime.now(), estimated_tokens))
                return "llama3.1-8b"
            
            # Try switching to gpt-oss
            req_count, token_count = self._get_current_usage(self.gpt_oss_requests)
            if req_count < self.gpt_oss_rpm and (token_count + estimated_tokens) < self.gpt_oss_tpm:
                self.current_model = "gpt-oss-120b"
                self.gpt_oss_requests.append((datetime.now(), estimated_tokens))
                logger.info("switched_to_gpt_oss", reason="llama_rate_limit")
                return "gpt-oss-120b"
            
            # Both at limit, fallback to ollama
            logger.warning("cerebras_rate_limit_reached", fallback="ollama")
            self.fallback_to_ollama = True
            return "ollama"
        
        else:  # gpt-oss-120b
            req_count, token_count = self._get_current_usage(self.gpt_oss_requests)
            
            # Check if we can use gpt-oss
            if req_count < self.gpt_oss_rpm and (token_count + estimated_tokens) < self.gpt_oss_tpm:
                self.gpt_oss_requests.append((datetime.now(), estimated_tokens))
                return "gpt-oss-120b"
            
            # Try switching to llama
            req_count, token_count = self._get_current_usage(self.llama_requests)
            if req_count < self.llama_rpm and (token_count + estimated_tokens) < self.llama_tpm:
                self.current_model = "llama3.1-8b"
                self.llama_requests.append((datetime.now(), estimated_tokens))
                logger.info("switched_to_llama", reason="gpt_oss_rate_limit")
                return "llama3.1-8b"
            
            # Both at limit, fallback to ollama
            logger.warning("cerebras_rate_limit_reached", fallback="ollama")
            self.fallback_to_ollama = True
            return "ollama"


class LLMExtractor:
    """LLM-based crime information extractor with Cerebras and Ollama"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_extraction_prompt(self) -> str:
        """Get the extraction prompt with schema definition"""
        return """Extract structured crime information from the article text.

OUTPUT SCHEMA (return ONLY valid JSON):
{
  "crime_type": "string or null (murder/robbery/assault/theft/kidnapping/rape/burglary)",
  "description": "string or null (brief crime description)",
  "location": {
    "city": "string or null",
    "state": "string or null", 
    "country": "string or null",
    "address": "string or null"
  },
  "date_time": "ISO 8601 datetime or null (YYYY-MM-DDTHH:MM:SS)",
  "victim_count": "integer or null",
  "suspect_count": "integer or null",
  "weapon_used": "string or null"
}

RULES:
1. Return ONLY the JSON object, no other text
2. Use null for missing information
3. Do NOT hallucinate or infer
4. Extract date_time in ISO 8601 format if mentioned
5. If no crime found, return all fields as null"""

    async def _extract_with_cerebras(self, article_text: str, model: str) -> Optional[dict]:
        """Extract using Cerebras API"""
        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": self._get_extraction_prompt()
                    },
                    {
                        "role": "user",
                        "content": f"Extract crime information:\n\n{article_text[:4000]}"
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 1000
            }
            
            response = await self.client.post(
                settings.cerebras_api_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.cerebras_api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 429:
                logger.warning("cerebras_rate_limit_hit", model=model)
                return None
            
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", model=model, error=str(e))
            return None
        except Exception as e:
            logger.error("cerebras_error", model=model, error=str(e))
            return None
    
    async def _extract_with_ollama(self, article_text: str) -> Optional[dict]:
        """Extract using local Ollama"""
        try:
            response = ollama.chat(
                model=settings.ollama_model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_extraction_prompt()
                    },
                    {
                        "role": "user",
                        "content": f"Extract crime information:\n\n{article_text[:4000]}"
                    }
                ],
                options={
                    "temperature": 0.0,
                    "num_predict": 1000
                }
            )
            
            content = response["message"]["content"]
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            logger.error("ollama_json_parse_error", error=str(e))
            return None
        except Exception as e:
            logger.error("ollama_error", error=str(e))
            return None
    
    async def extract_crime_info(self, article_text: str) -> Optional[dict]:
        """
        Extract crime information from article text
        
        Uses Cerebras API with automatic model switching and Ollama fallback
        """
        if not article_text or not article_text.strip():
            logger.warning("empty_article_text")
            return None
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(article_text) // 4 + 500  # +500 for response
        
        # Check rate limits and get model to use
        model = await self.rate_limiter.wait_if_needed(estimated_tokens)
        
        logger.info(
            "extraction_started",
            model=model,
            text_length=len(article_text),
            estimated_tokens=estimated_tokens
        )
        
        # Extract based on model
        if model == "ollama":
            data = await self._extract_with_ollama(article_text)
        else:
            data = await self._extract_with_cerebras(article_text, model)
            
            # If Cerebras fails, try Ollama
            if data is None:
                logger.info("fallback_to_ollama", reason="cerebras_failed")
                data = await self._extract_with_ollama(article_text)
        
        if data:
            logger.info(
                "extraction_success",
                model=model,
                has_crime_type=bool(data.get("crime_type"))
            )
        else:
            logger.warning("extraction_failed", model=model)
        
        return data
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
