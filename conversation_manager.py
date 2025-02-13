"""
conversation_manager.py

Updated to:
 - Use the new (response_text, usage_info) from ai_connectors
 - Track tokens/usage in logs
 - Incorporate more advanced logic for next speaker selection
"""

import os
import json
from typing import List, Optional
from dataclasses import asdict

from data_structures import (
    SetupData,
    Character,
    MessageLog,
    ConversationLog,
    ManagerConfig
)
from ai_connectors import call_ai_model, decide_next_speaker
from utils import (
    get_timestamp,
    approximate_word_count,
    approximate_reading_time_in_minutes,
    append_json_log,
)

class ConversationManager:
    def __init__(
        self,
        setup_data: SetupData,
        manager_config: ManagerConfig,
        log_file_path: str,
        max_words: int = 1500,
        max_read_minutes: float = 7.0,
    ):
        self.setup_data = setup_data
        self.manager_config = manager_config
        self.log_file_path = log_file_path
        self.max_words = max_words
        self.max_read_minutes = max_read_minutes

        # For tracking conversation content
        self.total_word_count = 0
        self.conversation_log = ConversationLog()

        # Additional: track total token usage or cost
        self.total_usage = {}

        # Add conversation time tracking
        self.current_conversation_time = 0  # in milliseconds

    def calculate_message_duration(self, message: str) -> int:
        """
        Calculate how long a message would take to say in milliseconds.
        Uses a rough approximation:
        - Base time per word (300ms)
        - Extra time for punctuation pauses
        - Random variation for natural feel
        """
        import random
        
        # Base calculation
        words = message.split()
        word_count = len(words)
        base_duration = word_count * 300  # 300ms per word
        
        # Add time for punctuation pauses
        punctuation_pauses = message.count('.') * 500  # 500ms pause for periods
        punctuation_pauses += message.count(',') * 200  # 200ms pause for commas
        
        # Add random variation (±15%)
        variation = random.uniform(0.85, 1.15)
        
        # Calculate total duration
        duration = int((base_duration + punctuation_pauses) * variation)
        
        # Ensure minimum duration
        return max(1000, duration)  # At least 1 second
        
    def calculate_speaker_pause(self) -> int:
        """Calculate natural pause between speakers"""
        import random
        return random.randint(500, 2000)  # 0.5 to 2 seconds

    def log_message(
        self, sender: str, message: str, model_used: Optional[str] = None, usage_info: Optional[dict] = None
    ):
        """
        Logs a message to in-memory and writes to a JSON file in real time.
        We also keep track of usage tokens if provided.
        """
        timestamp = get_timestamp()
        
        # Only advance conversation time for non-system messages
        if not sender.startswith("SystemCheck"):
            # Add pause if this isn't the first message
            if self.conversation_log.messages:
                self.current_conversation_time += self.calculate_speaker_pause()
            
            # Add message duration
            message_duration = self.calculate_message_duration(message)
            
            conversation_time = self.current_conversation_time
            self.current_conversation_time += message_duration
        else:
            conversation_time = None  # SystemCheck messages don't advance time

        msg_log = MessageLog(
            timestamp=timestamp,
            sender=sender,
            message=message,
            model_used=model_used
        )
        self.conversation_log.messages.append(msg_log)

        # Prepare log entry for disk
        log_entry = {
            "timestamp": timestamp,
            "sender": sender,
            "message": message,
            "model_used": model_used or "",
            "conversation_time": conversation_time  # Add conversation time to log
        }

        # If usage info is present, we store it
        if usage_info:
            log_entry["usage_info"] = usage_info
            self._accumulate_usage(usage_info)

        # Write to file
        append_json_log(log_entry, self.log_file_path)

        # Update word count
        self.total_word_count += approximate_word_count(message)

    def _accumulate_usage(self, usage_info: dict):
        """
        Accumulate total usage tokens (e.g., for OpenAI).
        usage_info might look like:
        {
            "prompt_tokens": 25,
            "completion_tokens": 50,
            "total_tokens": 75
        }
        We'll keep a rolling sum in self.total_usage.
        """
        for k, v in usage_info.items():
            if not isinstance(v, int):
                continue
            if k not in self.total_usage:
                self.total_usage[k] = 0
            self.total_usage[k] += v

    def check_end_conditions(self) -> bool:
        """Check if the conversation should end"""
        # Get and filter conversation text
        conversation_text = self._get_conversation_text()
        conversation_lines = conversation_text.split('\n')
        filtered_lines = [
            line for line in conversation_lines 
            if not line.startswith("SystemCheck:") and 
            not "[Goal Check]" in line and 
            not "[Closing Check]" in line
        ]
        filtered_conversation = '\n'.join(filtered_lines)

        # Convert setup_data to dict for JSON serialization
        setup_dict = {
            "id": self.setup_data.id,
            "version": self.setup_data.version,
            "name": self.setup_data.name,
            "topic": self.setup_data.topic,
            "logkeeper": asdict(self.setup_data.logkeeper),
            "simulation_time": self.setup_data.simulation_time,
            "characters": [asdict(c) for c in self.setup_data.characters],
            "world_or_simulation_context": asdict(self.setup_data.world_or_simulation_context),
            "meeting_setup": asdict(self.setup_data.meeting_setup)
        }

        # Convert to JSON
        setup_json = json.dumps(setup_dict, indent=2)

        # Create the prompt with filtered conversation
        prompt = (
            "This is the meeting setup data in JSON format:\n"
            "----------------------\n"
            f"{setup_json}\n"  # Pretty print the setup data
            "----------------------\n"
            f"Conversation so far:\n{filtered_conversation}\n\n"
            "----------------------\n"
            "Based on the conversation, have we achieved our meeting goals?\n"
            "Consider:\n"
            "1. Have all key points been discussed?\n"
            "2. Has a clear decision or conclusion been reached?\n"
            "3. Have all participants contributed meaningfully?\n\n"
            "Answer YES or NO only."
        )

        response_text, usage = call_ai_model(self.manager_config.manager_model, prompt)
        
        # Log the check
        self.log_message(
            sender="SystemCheck",
            message=f"[Goal Check] {response_text}",
            model_used=self.manager_config.manager_model,
            usage_info=usage
        )

        return "YES" in response_text.upper()

    def determine_closing_message(self) -> Optional[str]:
        """
        If a closing message is required, we ask the manager model.
        Returns the name of the character or None if no closing message is needed.
        """
        # Get and filter conversation text
        conversation_text = self._get_conversation_text()
        conversation_lines = conversation_text.split('\n')
        filtered_lines = [
            line for line in conversation_lines 
            if not line.startswith("SystemCheck:") and 
            not "[Goal Check]" in line and 
            not "[Closing Check]" in line
        ]
        filtered_conversation = '\n'.join(filtered_lines)

        prompt = (
            "Based on the conversation, do we need a final closing message to wrap up?\n"
            "If yes, provide the EXACT name of who should speak. If no, just say 'NO'.\n\n"
            f"Conversation so far:\n{filtered_conversation}\n"
            "If yes, reply just the EXACT name of who should speak. If no, just say 'NO'.\n\n"
        )
        
        response_text, usage = call_ai_model(self.manager_config.manager_model, prompt)
        self.log_message(
            sender="SystemCheck",
            message=f"[Closing Check] {response_text}",
            model_used=self.manager_config.manager_model,
            usage_info=usage
        )

        if "NO" in response_text.upper():
            return None
        # We attempt to parse out a name from the response
        chosen_speaker = response_text.strip()
        # If invalid, set None
        all_names = [c.name for c in self.setup_data.characters]
        if chosen_speaker not in all_names:
            return None
        return chosen_speaker

    def clean_closing_text(self, text: str) -> str:
        """Clean up closing text by removing quotes"""
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove opening/closing quotes if present
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        
        return text.strip()

    def run_conversation(self):
        """
        Main loop. 
        Starts with the opening message from meeting_setup,
        then continues until end conditions are met.
        """
        # Start with the opening message
        opening_message = self.setup_data.meeting_setup.opening_message
        print(f"\n{opening_message.speaker}: {opening_message.message}")
        
        # Add opening message to conversation log
        self.log_message(
            sender=opening_message.speaker,
            message=opening_message.message,
            model_used="None"  # Opening message doesn't use an AI model
        )
        
        # Normal conversation loop
        while True:
            # Get full conversation text and filter out system messages
            conversation_text = self._get_conversation_text()
            conversation_lines = conversation_text.split('\n')
            filtered_lines = [
                line for line in conversation_lines 
                if not line.startswith("SystemCheck:") and 
                not "[Goal Check]" in line and 
                not "[Closing Check]" in line
            ]
            filtered_conversation = '\n'.join(filtered_lines)

            character_names = [c.name for c in self.setup_data.characters]

            # Convert setup_data to dict for JSON serialization
            setup_dict = {
                "id": self.setup_data.id,
                "version": self.setup_data.version,
                "name": self.setup_data.name,
                "topic": self.setup_data.topic,
                "logkeeper": asdict(self.setup_data.logkeeper),
                "simulation_time": self.setup_data.simulation_time,
                "characters": [asdict(c) for c in self.setup_data.characters],
                "world_or_simulation_context": asdict(self.setup_data.world_or_simulation_context),
                "meeting_setup": asdict(self.setup_data.meeting_setup)
            }

            # First decide who speaks next
            next_speaker_name = decide_next_speaker(
                manager_model=self.manager_config.manager_model,
                conversation_so_far=filtered_conversation,
                character_names=character_names,
                setup_data=setup_dict
            )

            # Convert setup_data to JSON for the prompt
            setup_json = json.dumps(setup_dict, indent=2)

            # Get last message and sender
            last_message = ""
            last_message_sender = "None"
            if self.conversation_log.messages:
                # Filter out SystemCheck messages and get the last real message
                real_messages = [
                    msg for msg in self.conversation_log.messages 
                    if msg.sender != "SystemCheck"
                ]
                if real_messages:
                    last_msg = real_messages[-1]
                    last_message = last_msg.message
                    last_message_sender = last_msg.sender

            character = next(
                (c for c in self.setup_data.characters if c.name == next_speaker_name),
                self.setup_data.characters[0]
            )

            example_json = '''
    "message": {
      "speaker": "Khaleesi",
      "message": "Esteemed members of the council..."
    }
            '''

            character_prompt = (
                "This is the meeting setup data in JSON format:\n"
                "----------------------\n"
                f"{setup_json}\n"  # Pretty print the setup data
                "----------------------\n"
                "Here is the conversation so far:\n"
                "----------------------\n"
                f"{filtered_conversation}\n"  # Use filtered conversation instead
                "----------------------\n"
                #f"Last message from {last_message_sender}: {last_message}\n\n"
                f"You are {character.name}, a {character.position}.\n"
                "Please respond in-character. Keep your response concise and to the point, like a movie dialogue. Do not start your response with YOUR NAME:, no actions or descriptions, just respond with your message."
            )

            reply_text, usage = call_ai_model(character.assigned_model, character_prompt)
            
            # Clean the response text - remove surrounding quotes if present
            reply_text = reply_text.strip()
            if reply_text.startswith('"') and reply_text.endswith('"'):
                reply_text = reply_text[1:-1].strip()
            
            # Log the cleaned message
            self.log_message(character.name, reply_text, model_used=character.assigned_model, usage_info=usage)

            # Check if the meeting ends
            if self.check_end_conditions():
                break

        # 11. Potential closing message
        closer_name = self.determine_closing_message()
        if closer_name:
            closer_character = next(
                (c for c in self.setup_data.characters if c.name == closer_name),
                self.setup_data.characters[0]
            )
            print(
                f"\nGenerating closing message from {closer_character.name}..."
            )
            closing_prompt = (
                "This is the meeting setup data in JSON format:\n"
                "----------------------\n"
                f"{setup_json}\n"  # Pretty print the setup data
                "----------------------\n"
                "Here is the conversation so far:\n"
                "----------------------\n"
                f"{filtered_conversation}\n"  # Use filtered conversation instead
                "----------------------\n"          
                f"You are {closer_character.name}, a {closer_character.position}.\n"
                "Please respond in-character, provide a final closing message for this meeting like a movie dialogue. Do not start your response with YOUR NAME:, no actions or descriptions, just respond with your message."
            )
            closing_text, usage = call_ai_model(closer_character.assigned_model, closing_prompt)
            
            # Clean up closing text
            closing_text = self.clean_closing_text(closing_text)
            
            self.log_message(
                closer_character.name,
                closing_text,
                model_used=closer_character.assigned_model,
                usage_info=usage
            )

        # Final log of usage summary (optional)
        self._log_usage_summary()

    def _get_conversation_text(self) -> str:
        """
        Helper to return the conversation so far as a single string.
        """
        lines = []
        for msg in self.conversation_log.messages:
            lines.append(f"{msg.sender}: {msg.message}")
        return "\n".join(lines)

    def _log_usage_summary(self):
        """
        Optional: Log final usage info so the user can see total tokens used, etc.
        """
        summary_message = f"Token usage summary: {self.total_usage}"
        self.log_message("System", summary_message, model_used="None")
