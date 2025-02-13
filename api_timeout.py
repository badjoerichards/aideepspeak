import os
import time
import threading
from typing import Optional, Callable, Any

def countdown_timer(seconds: int, stop_event: threading.Event, model_name: str):
    """Display countdown timer with model name"""
    while seconds > 0 and not stop_event.is_set():
        print(f"\rWaiting for {model_name} response... {seconds}s ", end="", flush=True)
        time.sleep(1)
        seconds -= 1
    if not stop_event.is_set():
        print(f"\r{model_name} API call timed out!                    ")

def call_with_timeout(func: Callable, *args, timeout: Optional[int] = None, model_name: str = None) -> Any:
    """Call function with timeout"""
    if not timeout:  # If timeout is 0 or None
        return func(*args)
        
    result = None
    stop_event = threading.Event()
    
    # Start countdown timer in separate thread
    timer_thread = threading.Thread(
        target=countdown_timer,
        args=(timeout, stop_event, model_name)
    )
    timer_thread.start()
    
    try:
        # Start API call with timeout
        result = func(*args)
        
        # Stop the timer
        stop_event.set()
        timer_thread.join()
        
        # Clear the countdown line
        print("\r" + " "*50 + "\r", end="", flush=True)
        
        return result
        
    except Exception as e:
        stop_event.set()
        timer_thread.join()
        raise TimeoutError(f"API call to {model_name} timed out after {timeout} seconds") from e 