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
import json

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
    Call Anthropic's Claude API.
    Returns (response_text, usage_info).
    """
    try:
        # Start timing
        start_time = time.time()
        
        # Create Claude client
        client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY
        )
        
        # Make the API call
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Calculate TTFB
        ttfb = time.time() - start_time
        
        # Extract response text
        text = response.content[0].text
        
        # Build usage info
        usage_info = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            "ttfb_seconds": round(ttfb, 3)
        }
        
        return text, usage_info
        
    except Exception as e:
        print(f"Claude API Error: {str(e)}")
        return f"[claude ERROR]: {str(e)}", {
            "error": str(e),
            "ttfb_seconds": 0
        }

def call_gemini(prompt: str) -> Tuple[str, Dict]:
    """
    Call Google's Gemini API.
    Returns (response_text, usage_info).
    """
    try:
        # Start timing
        start_time = time.time()
        
        # Configure Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Initialize model
        model = genai.GenerativeModel('gemini-pro')
        
        # Make the API call
        response = model.generate_content(prompt)
        
        # Calculate TTFB
        ttfb = time.time() - start_time
        
        # Extract response text
        text = response.text
        
        # Build usage info (Note: Gemini doesn't provide token counts directly)
        usage_info = {
            "prompt_chars": len(prompt),
            "completion_chars": len(text),
            "total_chars": len(prompt) + len(text),
            "ttfb_seconds": round(ttfb, 3)
        }
        
        return text, usage_info
        
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return f"[gemini ERROR]: {str(e)}", {
            "error": str(e),
            "ttfb_seconds": 0
        }

def call_deepseek(prompt: str) -> Tuple[str, Dict]:
    """
    Call DeepSeek's API.
    Returns (response_text, usage_info).
    """
    try:
        # Start timing
        start_time = time.time()
        
        # Create headers with API key
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare the request payload
        payload = {
            "model": "deepseek-chat",  # or other available model
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        # Make the API call using requests
        import requests
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers=headers
        )
        
        # Calculate TTFB
        ttfb = time.time() - start_time
        
        # Handle response
        if response.status_code == 200:
            data = response.json()
            text = data['choices'][0]['message']['content']
            
            # Build usage info
            usage_info = {
                "prompt_tokens": data['usage']['prompt_tokens'],
                "completion_tokens": data['usage']['completion_tokens'],
                "total_tokens": data['usage']['total_tokens'],
                "ttfb_seconds": round(ttfb, 3)
            }
            
            return text, usage_info
        else:
            raise Exception(f"API returned status code {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"DeepSeek API Error: {str(e)}")
        return f"[deepseek ERROR]: {str(e)}", {
            "error": str(e),
            "ttfb_seconds": 0
        }

def call_ollama(prompt: str) -> Tuple[str, Dict]:
    """
    Call local Ollama instance.
    Returns (response_text, usage_info).
    """
    try:
        # Start timing
        start_time = time.time()
        
        # Prepare the request payload
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 1024,
            }
        }
        
        print(f"\nTrying to connect to Ollama at: {OLLAMA_API_BASE}")
        print(f"Using model: {OLLAMA_MODEL}")
        
        # Make the API call using requests with timeout
        import requests
        try:
            response = requests.post(
                f"{OLLAMA_API_BASE}/api/generate",
                json=payload,
                timeout=10  # Add 10 second timeout
            )
        except requests.exceptions.Timeout:
            raise Exception("Ollama API request timed out after 10 seconds. Is Ollama running?")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Could not connect to Ollama at {OLLAMA_API_BASE}. Is Ollama running?")
        
        # Calculate TTFB
        ttfb = time.time() - start_time
        
        # Handle response
        if response.status_code == 200:
            data = response.json()
            text = data['response']
            
            # Build usage info (Ollama provides different metrics)
            usage_info = {
                "eval_count": data.get('eval_count', 0),
                "eval_duration": data.get('eval_duration', 0),
                "load_duration": data.get('load_duration', 0),
                "prompt_chars": len(prompt),
                "completion_chars": len(text),
                "total_chars": len(prompt) + len(text),
                "ttfb_seconds": round(ttfb, 3)
            }
            
            return text, usage_info
        else:
            raise Exception(f"API returned status code {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"\nOllama API Error Details:")
        print(f"- Error Type: {type(e).__name__}")
        print(f"- Error Message: {str(e)}")
        print("- Troubleshooting steps:")
        print("  1. Check if Ollama is installed")
        print("  2. Check if Ollama service is running (run 'ollama serve')")
        print(f"  3. Check if model '{OLLAMA_MODEL}' is pulled (run 'ollama pull {OLLAMA_MODEL}')")
        print(f"  4. Verify API base URL: {OLLAMA_API_BASE}")
        
        return f"[ollama ERROR]: {str(e)}", {
            "error": str(e),
            "ttfb_seconds": 0
        }

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
            # Add model name to cached response
            usage_info['model'] = model_name
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
            return response_text, usage_info
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
    
    # Add model name to usage info
    usage_info['model'] = model_name
    
    # Only cache successful responses (no error messages)
    is_error = (
        response_text.startswith("[") and  # Error responses start with [model ERROR]
        "ERROR" in response_text or
        usage_info.get('error') is not None
    )
    
    # Cache the new response only if it's not an error
    if cache_manager and not is_error:
        print(f"\nCaching response with hash: {cache_manager._generate_hash(prompt, model_name)[:8]}...")
        cache_manager.set(prompt_content, model_name, response_text, usage_info)
        print("Response cached successfully")
    elif is_error:
        print("\nNot caching error response")
    
    # Debug the new response
    proceed, retry = debug_response(prompt, (response_text, usage_info))
    if retry:
        # Delete cached response and retry
        if cache_manager:
            cache_manager.delete(prompt_content, model_name)
            print("Cleared cached response for retry")
        return call_ai_model(model_name, prompt_content)
    elif not proceed:
        print("User rejected response")
        sys.exit(0)
    
    return response_text, usage_info

def decide_next_speaker(
    manager_model: str,
    conversation_so_far: str,
    character_names: list,
    setup_data: dict
) -> str:
    """
    Calls the 'manager_model' to decide who should speak next.
    Now includes the full setup data for better context.
    """
    # Filter out SystemCheck messages
    conversation_lines = conversation_so_far.split('\n')
    filtered_lines = [
        line for line in conversation_lines 
        if not line.startswith("SystemCheck:") and 
        not "[Goal Check]" in line and 
        not "[Closing Check]" in line
    ]
    filtered_conversation = '\n'.join(filtered_lines)

    prompt = (
        "You are the 'group chat manager', also the 'logkeeper' of the meeting.\n"
        
        "This is the meeting setup data in JSON format:\n"
        "----------------------\n"
        f"{json.dumps(setup_data, indent=2)}\n"  # Pretty print the setup data
        "----------------------\n"
        
        "Here is the conversation so far:\n"
        "----------------------\n"
        f"{filtered_conversation}\n"
        "----------------------\n"
        f"Available characters: {character_names}\n"
        f"For the most entertaining and logical outcome, \n"
        "which single character from the list of Available characters should speak next? Return just the name of the character (no explanation)"
    )

    response_text, _usage = call_ai_model(manager_model, prompt)
    chosen_name = response_text.strip()

    if chosen_name not in character_names:
        chosen_name = character_names[0]

    return chosen_name
