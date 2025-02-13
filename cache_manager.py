"""
Cache manager for AI responses with expiry and seeding.
"""

import json
import os
import time
import hashlib
from typing import Dict, Optional, Tuple, Union
from datetime import datetime, timedelta

CACHE_DIR = "cache"
CACHE_FILE = "ai_responses_cache.json"
DEFAULT_CACHE_SEED = 69
DEFAULT_EXPIRY_DAYS = 3

class CacheManager:
    def __init__(self, cache_seed: int = DEFAULT_CACHE_SEED):
        self.cache_seed = cache_seed
        self.cache_file = os.path.join(CACHE_DIR, CACHE_FILE)
        os.makedirs(CACHE_DIR, exist_ok=True)
        print(f"\nInitializing cache manager with seed: {cache_seed}")
        expired_count = self._prune_expired()
        if expired_count > 0:
            print(f"Pruned {expired_count} expired cache entries")
    
    def _normalize_prompt(self, prompt: Union[str, Dict]) -> str:
        """Normalize the prompt for consistent hashing"""
        if isinstance(prompt, dict):
            # If prompt is a dict, use the content field
            prompt_str = prompt.get('content', '')
        else:
            # If prompt is already a string, use it directly
            prompt_str = str(prompt)
        
        return "\n".join(line.strip() for line in prompt_str.split("\n")).strip()
    
    def _generate_hash(self, prompt: str, model_name: str) -> str:
        """Generate a unique hash for the prompt + model + seed combination"""
        normalized_prompt = self._normalize_prompt(prompt)
        content = f"{normalized_prompt}:{model_name}:{self.cache_seed}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        print(f"Generated hash for cache: {hash_value[:8]}...")
        return hash_value
    
    def _load_cache(self) -> Dict:
        """Load the cache file or create new if not exists"""
        try:
            if os.path.exists(self.cache_file):
                print(f"Loading existing cache from: {self.cache_file}")
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"Loaded cache with {len(data.get('entries', {}))} entries")
                    return data
            else:
                print(f"No existing cache file at: {self.cache_file}")
                return {"cache_seed": self.cache_seed, "entries": {}}
        except Exception as e:
            print(f"Error loading cache: {str(e)}")
            return {"cache_seed": self.cache_seed, "entries": {}}
    
    def _save_cache(self, cache_data: Dict):
        """Save the cache data to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def _prune_expired(self) -> int:
        """Remove expired entries and error responses from cache. Returns count of pruned entries."""
        cache_data = self._load_cache()
        current_time = datetime.now().timestamp()
        expired_count = 0
        
        # Create new dict for valid entries
        valid_entries = {}
        
        for key, entry in cache_data["entries"].items():
            # Check if entry is expired
            is_expired = entry["expires_at"] <= current_time
            
            # Check if entry is an error response
            response_text = entry["response"]
            usage_info = entry["usage_info"]
            is_error = (
                (isinstance(response_text, str) and response_text.startswith("[") and "ERROR" in response_text) or
                usage_info.get('error') is not None
            )
            
            # Keep only valid, non-expired, non-error entries
            if not is_expired and not is_error:
                valid_entries[key] = entry
            else:
                expired_count += 1
        
        if expired_count > 0:
            cache_data["entries"] = valid_entries
            self._save_cache(cache_data)
            
        return expired_count
    
    def get(self, prompt: str, model_name: str) -> Optional[Tuple[str, Dict]]:
        """Get cached response if exists and not expired"""
        cache_data = self._load_cache()
        prompt_hash = self._generate_hash(prompt, model_name)
        
        #print(f"Looking for hash {prompt_hash[:8]}... in cache")
        #print(f"Available cache entries: {list(cache_data['entries'].keys())[:8]}")
        
        if prompt_hash in cache_data["entries"]:
            entry = cache_data["entries"][prompt_hash]
            if entry["expires_at"] > datetime.now().timestamp():
                expires_in = datetime.fromtimestamp(entry["expires_at"]) - datetime.now()
                print(f"Cache hit! Entry expires in {expires_in.days} days")
                usage_info = {**entry["usage_info"], 'cached': True}
                return entry["response"], usage_info
            else:
                print("Found expired cache entry, will make new API call")
        return None
    
    def set(self, prompt: str, model_name: str, response: str, usage_info: Dict):
        """Cache a new response"""
        try:
            cache_data = self._load_cache()
            prompt_hash = self._generate_hash(prompt, model_name)
            
            print(f"\nAttempting to cache response...")
            print(f"Cache file location: {self.cache_file}")
            
            cache_data["entries"][prompt_hash] = {
                "prompt": prompt,
                "model": model_name,
                "response": response,
                "usage_info": usage_info,
                "created_at": datetime.now().timestamp(),
                "expires_at": (datetime.now() + timedelta(days=DEFAULT_EXPIRY_DAYS)).timestamp()
            }
            
            # Debug print before saving
            #print(f"Cache data to write: {json.dumps(cache_data, indent=2)[:200]}...")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            # Write with explicit encoding
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Verify the file was written
            if os.path.exists(self.cache_file):
                file_size = os.path.getsize(self.cache_file)
                print(f"Cache file written successfully. Size: {file_size} bytes")
            else:
                print("Warning: Cache file not found after writing!")
            
        except Exception as e:
            print(f"Error caching response: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def clear(self):
        """Clear all cache entries"""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
    
    def delete(self, prompt: str, model_name: str):
        """Delete a specific cache entry"""
        cache_data = self._load_cache()
        prompt_hash = self._generate_hash(prompt, model_name)
        
        if prompt_hash in cache_data["entries"]:
            del cache_data["entries"][prompt_hash]
            self._save_cache(cache_data)
            print(f"Deleted cache entry with hash: {prompt_hash[:8]}...")

# Global cache manager instance
cache_manager = None

def init_cache(cache_seed: int = DEFAULT_CACHE_SEED) -> CacheManager:
    """Initialize the global cache manager"""
    global cache_manager
    if cache_manager is None:
        print(f"\nInitializing global cache manager with seed: {cache_seed}")
        cache_manager = CacheManager(cache_seed)
    else:
        print("\nUsing existing cache manager")
    return cache_manager 