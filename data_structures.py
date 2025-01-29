"""
data_structures.py

Defines data structures (using Python 'dataclasses' or 'pydantic' if needed)
for the conversation setup JSON and logs.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import os

@dataclass
class Character:
    name: str
    position: str
    role: str
    hierarchy: int
    assigned_model: str

@dataclass
class WorldContext:
    era: str
    year: str
    season: str
    technological_level: str
    culture_and_society: str
    religions: List[str]
    magic_and_myths: str
    political_climate: str

@dataclass
class Location:
    name: str
    coordinates: str
    latitude: float
    longitude: float
    description: str

@dataclass
class Event:
    event_description: str

@dataclass
class Document:
    title: str
    description: str

@dataclass
class SeatingArrangement:
    position: int
    name: str
    role: str

@dataclass
class RoomSetup:
    description: str
    seating_arrangement: List[SeatingArrangement]

@dataclass
class PurposeAndContext:
    purpose: str
    context: str

@dataclass
class Goal:
    objectives: List[str]

@dataclass
class BriefingMaterials:
    documents: List[Document]

@dataclass
class ProtocolReminder:
    speaking_order: List[str]
    customs: List[str]

@dataclass
class OpeningMessage:
    speaker: str
    message: str

@dataclass
class MeetingSetup:
    date: str
    time: str
    location: Location
    recent_events: List[Event]
    summary_of_last_meetings: str
    tags_keywords: List[str]
    category: str
    room_setup: RoomSetup
    purpose_and_context: PurposeAndContext
    goal: Goal
    briefing_materials: BriefingMaterials
    protocol_reminder: ProtocolReminder
    opening_message: OpeningMessage
    agenda_outline: Dict[str, str]

@dataclass
class Logkeeper:
    name: str = "The Logkeeper"
    position: str = "Logkeeper"
    role: str = "Group chat manager. Logs the meeting and provides a summary of the meeting"
    assigned_model: str = "openai"

@dataclass
class SetupData:
    """
    This combines everything needed for the conversation.
    """
    topic: str  # Non-default argument must come first
    characters: List[Character]
    world_or_simulation_context: WorldContext
    meeting_setup: MeetingSetup
    id: str = "<not_ready>"
    version: str = os.getenv("VERSION", "2.0")
    name: str = "<not_ready>"
    logkeeper: Logkeeper = field(default_factory=Logkeeper)
    simulation_time: int = 0  # Will be updated with total ttfb_seconds

@dataclass
class MessageLog:
    timestamp: str
    sender: str
    message: str
    # You can add more fields like "model_used", "role", etc.
    model_used: Optional[str] = None

@dataclass
class ConversationLog:
    messages: List[MessageLog] = field(default_factory=list)

@dataclass
class ManagerConfig:
    """
    Configuration for the 'group chat manager' AI model or selection method.
    """
    manager_model: str

class MessageData:
    def __init__(self, text: str, role: str, usage_info: Optional[Dict[str, Any]] = None):
        self.text = text
        self.role = role
        self.usage_info = usage_info or {}

class ConversationHistory:
    def __init__(self):
        self.messages = []
        self.total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    
    def add_message(self, text: str, role: str, usage_info: Optional[Dict[str, Any]] = None):
        message = MessageData(text, role, usage_info)
        self.messages.append(message)
        
        if usage_info:
            self.update_usage(usage_info)
    
    def update_usage(self, usage_info: Dict[str, Any]):
        for key in self.total_usage:
            if key in usage_info:
                self.total_usage[key] += usage_info[key]
