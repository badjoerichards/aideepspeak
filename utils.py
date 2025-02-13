"""
utils.py

Utility functions for random model selection, time stamps, logging, etc.
"""

import json
import random
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import os
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()
print(f"Utils: Environment loaded, PROMPT_DEBUG = {os.getenv('PROMPT_DEBUG')}")

# Add these color constants at the top of utils.py
class Colors:
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RESET = '\033[0m'

def get_timestamp() -> str:
    """Return current timestamp as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def write_json_to_file(data: dict, filename: str):
    """Write dictionary to JSON file with proper formatting"""
    try:
        # Ensure the data is ordered the way we want, but preserve input values
        ordered_data = {
            "id": data["id"],  # Use data values directly
            "version": data["version"],
            "name": data["name"],
            "topic": data["topic"],
            "logkeeper": data["logkeeper"],
            "simulation_time": data["simulation_time"],
            "characters": data["characters"],
            "world_or_simulation_context": data["world_or_simulation_context"],
            "meeting_setup": data["meeting_setup"]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(ordered_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error writing to {filename}: {e}")
        print("Data was:", json.dumps(data, indent=2))

def append_json_log(log_entry, file_path: str):
    """
    Append a single log entry to an existing JSON array in the file.
    If the file does not exist, create a new JSON file with an array.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        if not isinstance(existing_data, list):
            existing_data = []
    except FileNotFoundError:
        existing_data = []

    existing_data.append(log_entry)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

def get_random_ai_model() -> str:
    """
    Return a random AI model name from the predefined set.
    e.g., ["OpenAI GPT", "Claude", "Gemini", "DeepSeek", "Ollama"]
    """
    models = ["openai-gpt", "claude", "gemini", "deepseek", "ollama"]
    return random.choice(models)

def approximate_word_count(text: str) -> int:
    """Approximate the word count of a text."""
    return len(text.split())

def approximate_reading_time_in_minutes(word_count: int, wpm: int = 200) -> float:
    """Approximate reading time by dividing word_count by the reading speed (words per minute)."""
    return word_count / wpm

def update_conversation(conversation_id: str, response_text: str, usage_info: Dict[str, Any]):
    conversation = get_conversation(conversation_id)
    conversation.add_message(
        text=response_text,
        role="assistant",
        usage_info=usage_info
    )
    save_conversation(conversation_id, conversation)

def get_conversation_stats(conversation_id: str) -> Dict[str, Any]:
    conversation = get_conversation(conversation_id)
    return {
        "message_count": len(conversation.messages),
        "usage": conversation.total_usage
    }

class DebugPromptManager:
    def __init__(self):
        # Load both debug settings
        debug_env = os.getenv("PROMPT_DEBUG", "false").lower()
        show_only_env = os.getenv("DEBUG_SHOW_PROMPTS_AND_RESPONSES", "false").lower()
        
        # Convert to boolean
        self.debug_enabled = debug_env in ['true', '1', 'yes', 'on']
        self.show_only = show_only_env in ['true', '1', 'yes', 'on']
        
        print(f"Debug Manager Initialized - Interactive Debug: {self.debug_enabled}, Show Only: {self.show_only}")
        self.skip_debug = False
    
    def should_debug(self) -> bool:
        return (self.debug_enabled or self.show_only) and not self.skip_debug
    
    def should_prompt(self) -> bool:
        """Determine if we should prompt the user for input"""
        return self.debug_enabled and not self.skip_debug and not self.show_only
    
    def prompt_user(self, prompt: str, response: Optional[Tuple[str, dict]] = None) -> str:
        """
        Handles debug prompting with colored output and model information.
        """
        should_show = self.should_debug()
        if not should_show:
            return 'y'
        
        if response is None:
            # Prompt validation - Yellow color
            print("\n=== DEBUG: AI Prompt ===")
            print(f"{Colors.YELLOW}Prompt Content (Sending to: {prompt.get('model', 'unknown')}):") 
            print("---------------")
            print(f"{prompt['content']}")
            print(f"---------------{Colors.RESET}")
            
            # Only ask for input if interactive debug is enabled
            if self.should_prompt():
                print("\nSend this prompt? [y]es/[n]o/[s]kip debug for session: ", end="", flush=True)
                choice = input().lower()
                if choice == 's':
                    self.skip_debug = True
                    return 'y'
                return choice
            return 'y'  # Auto-continue if show-only mode
            
        else:
            # Response validation - Green color
            print("\n=== DEBUG: AI Response ===")
            print(f"{Colors.GREEN}Response Content (From: {response[1].get('model', 'unknown')}):")
            print("---------------")
            print(f"{response[0]}")
            print(f"---------------{Colors.RESET}")
            ttfb = response[1].get('ttfb_seconds', 'N/A')
            print(f"Usage Info: {response[1]} (Time to first byte: {ttfb}s)")
            
            # Only ask for input if interactive debug is enabled
            if self.should_prompt():
                print("\nProceed with this response? [y]es/[n]o/[r]etry/[s]kip debug for session: ", end="", flush=True)
                choice = input().lower()
                if choice == 's':
                    self.skip_debug = True
                    return 'y'
                return choice
            return 'y'  # Auto-continue if show-only mode

# Global debug manager instance
debug_manager = DebugPromptManager()

def debug_prompt(prompt: str) -> bool:
    """Returns True to proceed, False to exit"""
    print(f"Debug: PROMPT_DEBUG is set to: {os.getenv('PROMPT_DEBUG')}")
    choice = debug_manager.prompt_user(prompt)
    if choice == 'n':
        print("Debug: Exiting program due to prompt rejection")
        exit(0)
    return True

def debug_response(prompt: str, response: Tuple[str, dict]) -> Tuple[bool, bool]:
    """Returns (proceed, retry)"""
    response_text, usage_info = response
    
    # Check if this is a cached response
    is_cached = usage_info.get('cached', False)  # We'll add this flag
    model_name = "cache" if is_cached else usage_info.get('model', 'unknown')
    
    choice = debug_manager.prompt_user(prompt, (response_text, {
        **usage_info,
        'model': model_name
    }))
    
    if choice == 'n':
        print("Debug: Exiting program due to response rejection")
        exit(0)
    return choice != 'r', choice == 'r'
