"""
ai_connectors.py

Updated file showing how to integrate with OpenAI GPT,
while keeping placeholders for Claude, Gemini, DeepSeek, and Ollama.
"""

import os
from typing import Tuple, Dict, Any
from utils import debug_prompt, debug_response
import time  # Add this import at the top
from cache_manager import cache_manager, init_cache
import sys

# Try importing required packages with helpful error messages
try:
    import openai
except ImportError:
    print("Error: openai package not found. Please install it with: pip install openai")
    openai = None

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not found. Please install it with: pip install anthropic")
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai package not found. Please install it with: pip install google-generativeai")
    genai = None

# Get API keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROMPT_DEBUG = os.getenv("PROMPT_DEBUG")
print(f"AI Connectors: PROMPT_DEBUG from env: {PROMPT_DEBUG}")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# After loading the API keys
if OPENAI_API_KEY and openai:
    openai.api_key = OPENAI_API_KEY

def validate_api_keys(model_name: str) -> bool:
    """Validate that required API keys and packages are present for the selected model"""
    if model_name == "openai-gpt":
        if not openai:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in .env file")
        print(f"Debug: Using OpenAI with key starting with: {OPENAI_API_KEY[:8]}...")
    elif model_name == "claude":
        if not anthropic:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        if not ANTHROPIC_API_KEY:
            raise ValueError("Anthropic API key not found in .env file")
    elif model_name == "gemini":
        if not genai:
            raise ImportError("Google Generative AI package not installed. Run: pip install google-generativeai")
        if not GOOGLE_API_KEY:
            raise ValueError("Google API key not found in .env file")
    elif model_name == "deepseek" and not DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API key not found in .env file")
    return True

def call_openai_gpt(prompt: str, model_name: str = "gpt-3.5-turbo") -> Tuple[str, Dict]:
    """
    Calls the OpenAI ChatCompletion API with a given prompt.
    Returns (response_text, usage_info), where usage_info is a dict containing tokens used, etc.
    """
    try:
        # Start timing
        start_time = time.time()
        
        # New OpenAI API format
        response = openai.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful AI participant in a meeting."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7
        )
        
        # Calculate TTFB
        ttfb = time.time() - start_time
        
        # New response format
        text = response.choices[0].message.content
        usage_info = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "ttfb_seconds": round(ttfb, 3)  # Round to 3 decimal places
        }
        return text, usage_info
    except Exception as e:
        # In production, handle errors more gracefully
        return f"[openai-gpt ERROR]: {e}", {}

def call_claude(prompt: str) -> Tuple[str, Dict]:
    """
    Placeholder for Anthropic's Claude API call or similar.
    Should return (text, usage_info).
    """
    # Pseudo-code or real API call
    # ...
    mock_text = f"[claude Mock Response]: I'm Claude, responding to: {prompt[:50]}..."
    usage_info = {}
    return mock_text, usage_info

def call_gemini(prompt: str) -> Tuple[str, Dict]:
    """
    Placeholder for Google Gemini.
    """
    mock_text = f"[gemini Mock Response]: I'm Gemini, responding to: {prompt[:50]}..."
    usage_info = {}
    return mock_text, usage_info

def call_deepseek(prompt: str) -> Tuple[str, Dict]:
    """
    Placeholder for a hypothetical 'DeepSeek' model.
    """
    mock_text = f"[deepseek Mock Response]: I'm DeepSeek, responding to: {prompt[:50]}..."
    usage_info = {}
    return mock_text, usage_info

def call_ollama(prompt: str) -> Tuple[str, Dict]:
    """
    Placeholder for Ollama-based local LLM calls.
    """
    mock_text = f"[ollama Mock Response]: I'm Ollama, responding to: {prompt[:50]}..."
    usage_info = {}
    return mock_text, usage_info

def call_ai_model(model_name: str, prompt_content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Generic function to call different AI models based on model_name.
    Returns (response_text, usage_info)
    """
    validate_api_keys(model_name)
    
    # Create prompt dict with content and model info
    prompt = {
        'content': prompt_content,
        'model': model_name
    }
    
    # Always show prompt debug first
    print(f"\nSending prompt to {model_name} API...")
    proceed = debug_prompt(prompt)
    if not proceed:
        print("User chose not to proceed with prompt")
        sys.exit(0)
    
    # Check cache after prompt is approved
    from cache_manager import cache_manager
    if cache_manager is not None:
        print(f"\nChecking cache for {model_name} response...")
        cached = cache_manager.get(prompt_content, model_name)  # Use prompt_content for cache
        if cached:
            response_text, usage_info = cached
            print(f"✓ Found cached response from {model_name}")
            print(f"Usage Info (cached): {usage_info}")
            # Show debug for cached response
            proceed, retry = debug_response(prompt, (response_text, usage_info))
            if retry:
                cache_manager.delete(prompt_content, model_name)  # Use prompt_content for cache
                print("Cleared cached response for retry")
                return call_ai_model(model_name, prompt_content)
            elif not proceed:
                print("User rejected cached response")
                sys.exit(0)
            return cached
        print("✗ No cached response found")
    else:
        print("✗ Cache manager not available - responses won't be cached")
    
    print("Making API call...")
    # Make the API call based on model
    if model_name == "openai-gpt":
        response = call_openai_gpt(prompt_content)
    elif model_name == "claude":
        response = call_claude(prompt_content)
    elif model_name == "gemini":
        response = call_gemini(prompt_content)
    elif model_name == "deepseek":
        response = call_deepseek(prompt_content)
    elif model_name == "ollama":
        response = call_ollama(prompt_content)
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    response_text, usage_info = response
    
    # Cache the new response
    if cache_manager:
        print(f"\nCaching response with hash: {cache_manager._generate_hash(prompt, model_name)[:8]}...")
        cache_manager.set(prompt_content, model_name, response_text, usage_info)
        print("Response cached successfully")
    
    # Debug the new response
    proceed, retry = debug_response(prompt, response)
    if retry:
        # Delete cached response and retry
        if cache_manager:
            cache_manager.delete(prompt_content, model_name)
            print("Cleared cached response for retry")
        return call_ai_model(model_name, prompt_content)
    elif not proceed:
        print("User rejected response")
        sys.exit(0)
    
    # Include model in usage info
    usage_info['model'] = model_name
    
    return response_text, usage_info

def decide_next_speaker(
    manager_model: str,
    conversation_so_far: str,
    character_names: list
) -> str:
    """
    Calls the 'manager_model' to decide who should speak next
    based on the entire conversation_so-far and the list of character names.
    This is an example of "additional logic" using AI. 
    We send the conversation text to the manager model so it can decide.
    Returns just the character name as a string.
    """
    prompt = (
        "You are the 'group chat manager' AI.\n"
        "Here is the conversation so far:\n"
        "----------------------\n"
        f"{conversation_so_far}\n"
        "----------------------\n"
        f"Available characters: {character_names}\n"
        "Which single character should speak next? Return just the name (no explanation)."
    )

    response_text, _usage = call_ai_model(manager_model, prompt)
    # In a real scenario, you'd parse the response carefully.
    # For simplicity, let's assume the AI just returns the exact character name or we fallback.
    chosen_name = response_text.strip()

    if chosen_name not in character_names:
        # Fallback if the AI gave an invalid name
        chosen_name = character_names[0]

    return chosen_name
