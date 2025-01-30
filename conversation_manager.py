"""
conversation_manager.py

Updated to:
 - Use the new (response_text, usage_info) from ai_connectors
 - Track tokens/usage in logs
 - Incorporate more advanced logic for next speaker selection
"""

import os
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

    def log_message(
        self, sender: str, message: str, model_used: Optional[str] = None, usage_info: Optional[dict] = None
    ):
        """
        Logs a message to in-memory and writes to a JSON file in real time.
        We also keep track of usage tokens if provided.
        """
        timestamp = get_timestamp()
        msg_log = MessageLog(
            timestamp=timestamp, sender=sender, message=message, model_used=model_used
        )
        self.conversation_log.messages.append(msg_log)

        # Prepare log entry for disk
        log_entry = {
            "timestamp": timestamp,
            "sender": sender,
            "message": message,
            "model_used": model_used or "",
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
        """
        Check if conversation should end:
         - If total_word_count > max_words
         - If approximate reading time > max_read_minutes
         - If an AI call determines goal is reached
        """
        read_minutes = approximate_reading_time_in_minutes(self.total_word_count)
        if self.total_word_count >= self.max_words or read_minutes >= self.max_read_minutes:
            return True

        # Additionally, ask an AI if the goal/purpose is met.
        # We pass in some details plus the conversation so far.
        conversation_text = self._get_conversation_text()
        prompt = (
            f"Conversation so far:\n{conversation_text}\n\n"
            f"Meeting goal: {self.setup_data.meeting_setup.goal}\n\n"
            "Have we met the goal or purpose? Reply YES or NO."
        )
        response_text, usage = call_ai_model(self.manager_config.manager_model, prompt)
        # Log the manager's analysis as well (optional, but might be helpful).
        self.log_message(
            sender="SystemCheck",
            message=f"[Goal Check] {response_text}",
            model_used=self.manager_config.manager_model,
            usage_info=usage
        )

        if "YES" in response_text.upper():
            return True

        return False

    def determine_closing_message(self) -> Optional[str]:
        """
        If a closing message is required, we ask the manager model.
        Returns the name of the character or None if no closing message is needed.
        """
        conversation_text = self._get_conversation_text()
        prompt = (
            "Based on the conversation, do we need a final closing message to wrap up?\n"
            "If yes, provide the EXACT name of who should speak. If no, just say 'NO'.\n\n"
            f"Conversation so far:\n{conversation_text}\n"
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
            conversation_text = self._get_conversation_text()
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

            # Pass setup_dict to decide_next_speaker
            next_speaker_name = decide_next_speaker(
                manager_model=self.manager_config.manager_model,
                conversation_so_far=conversation_text,
                character_names=character_names,
                setup_data=setup_dict
            )
            
            # Fallback if needed
            character = next(
                (c for c in self.setup_data.characters if c.name == next_speaker_name),
                self.setup_data.characters[0]
            )

            # Provide the context to that character
            last_message = (
                self.conversation_log.messages[-1].message if self.conversation_log.messages else ""
            )

            character_prompt = (
                f"You are {character.name}, a {character.position}.\n"
                f"Role: {character.role}.\n\n"
                f"Meeting context: {self.setup_data.meeting_setup.purpose_and_context}.\n"
                f"Recent events: {self.setup_data.meeting_setup.recent_events}.\n"
                f"Last message: {last_message}\n\n"
                "Please respond in-character."
            )

            reply_text, usage = call_ai_model(character.assigned_model, character_prompt)
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
            closing_prompt = (
                f"You are {closer_character.name}. "
                "Please provide a final closing message for this meeting."
            )
            closing_text, usage = call_ai_model(closer_character.assigned_model, closing_prompt)
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
