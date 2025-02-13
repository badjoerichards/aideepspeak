"""
conversation_flow.py

Contains functions for generating the initial setup JSON (characters, world context, meeting_setup)
and any relevant prompts or logic for building 'SetupData'.
"""

import random
from dataclasses import asdict
import json
import os

from data_structures import (
    Character,
    WorldContext,
    MeetingSetup,
    SetupData,
    Location,
    Event,
    SeatingArrangement,
    RoomSetup,
    PurposeAndContext,
    Goal,
    BriefingMaterials,
    ProtocolReminder,
    OpeningMessage,
    Document
)
from ai_connectors import call_ai_model
from utils import get_random_ai_model, write_json_to_file
from cache_manager import cache_manager  # Only import the instance, not init_cache

def clean_json_response(response_text: str) -> str:
    """Clean the response text to get valid JSON"""
    try:
        # Remove markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1]
        if "```" in response_text:
            response_text = response_text.split("```")[0]
        
        # First try to parse as-is
        try:
            json.loads(response_text)
            return response_text
        except json.JSONDecodeError:
            pass
            
        # Clean up whitespace and newlines
        lines = [line.strip() for line in response_text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        
        # Remove trailing commas
        cleaned_lines = []
        for i, line in enumerate(lines):
            # Skip empty lines
            if not line:
                continue
                
            # Check if this line ends with a comma and next line starts a closing bracket
            next_line = lines[i+1].strip() if i+1 < len(lines) else ''
            if line.endswith(',') and (next_line.startswith('}') or next_line.startswith(']')):
                line = line.rstrip(',')
            cleaned_lines.append(line)
        
        # Join back together
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove any remaining problematic commas
        cleaned_text = cleaned_text.replace(',}', '}')
        cleaned_text = cleaned_text.replace(',]', ']')
        
        # Verify the cleaned JSON is valid
        try:
            json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to clean JSON: {e}")
            print("Original response:", response_text)
            print("Cleaned response:", cleaned_text)
            
        return cleaned_text
        
    except Exception as e:
        print(f"Error cleaning JSON response: {e}")
        return response_text

def parse_meeting_setup_response(response_text: str) -> MeetingSetup:
    """Parse the JSON response from AI into MeetingSetup object"""
    try:
        # Clean the response first
        cleaned_response = clean_json_response(response_text)
        
        # Parse the cleaned JSON
        data = json.loads(cleaned_response)
        
        # Extract meeting_setup from root if needed
        setup_data = data.get('meeting_setup', data)
        
        # Parse nested objects
        location = Location(**setup_data["location"])
        events = [Event(**e) for e in setup_data["recent_events"]]
        seating = [SeatingArrangement(**s) for s in setup_data["room_setup"]["seating_arrangement"]]
        room_setup = RoomSetup(
            description=setup_data["room_setup"]["description"],
            seating_arrangement=seating
        )
        purpose_ctx = PurposeAndContext(**setup_data["purpose_and_context"])
        goal = Goal(objectives=setup_data["goal"]["objectives"])
        docs = [Document(**d) for d in setup_data["briefing_materials"]["documents"]]
        briefing = BriefingMaterials(documents=docs)
        protocol = ProtocolReminder(**setup_data["protocol_reminder"])
        opening = OpeningMessage(**setup_data["opening_message"])
        
        return MeetingSetup(
            date=setup_data["date"],
            time=setup_data["time"],
            location=location,
            recent_events=events,
            summary_of_last_meetings=setup_data["summary_of_last_meetings"],
            tags_keywords=setup_data.get("tags_keywords", ["<not_ready>"]),
            category=setup_data.get("category", "<not_ready>"),
            room_setup=room_setup,
            purpose_and_context=purpose_ctx,
            goal=goal,
            briefing_materials=briefing,
            protocol_reminder=protocol,
            opening_message=opening,
            agenda_outline=setup_data["agenda_outline"]
        )
        
    except Exception as e:
        print(f"Error parsing meeting setup: {e}")
        print("Response was:", response_text)
        return None

def parse_world_context_response(response_text: str) -> WorldContext:
    """Parse the JSON response from AI into WorldContext object"""
    try:
        cleaned_response = clean_json_response(response_text)
        data = json.loads(cleaned_response)
        
        # Extract world_context from root if needed
        context_data = data.get('world_or_simulation_context', data)
        
        # Ensure religions is a list
        religions = context_data.get('religions', [])
        if isinstance(religions, str):
            religions = [religions]
        
        return WorldContext(
            era=context_data.get('era', ''),
            year=context_data.get('year', ''),
            season=context_data.get('season', ''),
            technological_level=context_data.get('technological_level', ''),
            culture_and_society=context_data.get('culture_and_society', ''),
            religions=religions,
            magic_and_myths=context_data.get('magic_and_myths', ''),
            political_climate=context_data.get('political_climate', '')
        )
    except Exception as e:
        print(f"Error parsing world context: {e}")
        print("Response was:", response_text)
        return None

def generate_setup_data(topic: str) -> SetupData:
    """
    Generate the JSON structure based on the user-provided topic.
    Uses AI to generate characters, world context, and meeting setup.
    """
    total_ttfb = 0  # Track total time to first byte
    
    print("\nGenerating characters...")
    
    # Generate characters
    example_json = '''{
        "characters": [
            {
                "name": "Khal",
                "position": "Queen",
                "role": "Ruler and Leader of the Dothraki",
                "hierarchy_level": 1
            },
            {
                "name": "Tyrion Lann",
                "position": "Hand of the Queen",
                "role": "Chief Advisor and Strategist",
                "hierarchy_level": 2
            },
            {
                "name": "Jon Melt",
                "position": "King in the North",
                "role": "Leader of the Northern forces",
                "hierarchy_level": 3
            },
            {
                "name": "Arya Stalker",
                "position": "Assassin",
                "role": "Stealth operative and assassin",
                "hierarchy_level": 4
            },
            {
                "name": "Blade",
                "position": "Master of Whisperers",
                "role": "Spymaster and intelligence gatherer",
                "hierarchy_level": 5
            },
            {
                "name": "Annie of Tarth",
                "position": "Knight",
                "role": "Protector and warrior",
                "hierarchy_level": 6
            }
        ]
    }'''
    
    characters_prompt = f"""Topic: {topic}
    Please generate a list of 4-6 characters for this meeting/conversation.
    For each character include:
    - name
    - position/title
    - role/responsibility
    - hierarchy level (1-10, where 1 is highest)
    
    Format the response as a clear list with all these details for each character.
    Example:
    {example_json}

    Requirements: your response MUST be in valid JSON format
    """
    
    print("\nCalling AI for characters...")  # Add debug print
    characters_response, usage = call_ai_model("openai-gpt", characters_prompt)
    total_ttfb += float(usage.get('ttfb_seconds', 0))
    print(f"\nReceived character response with usage: {usage}")  # Add debug print
    
    # Parse characters response with error handling
    try:
        cleaned_response = clean_json_response(characters_response)
        char_data = json.loads(cleaned_response)
        characters = []
        for char in char_data["characters"]:
            characters.append(Character(
                name=char["name"],
                position=char["position"],
                role=char["role"],
                hierarchy=char["hierarchy_level"],
                assigned_model=get_random_ai_model()
            ))
    except Exception as e:
        print(f"Error parsing characters: {e}")
        print("Response was:", characters_response)
        return None

    # Generate world context
    example_json = '''{
  "world_or_simulation_context": {
    "era": "Medieval Fantasy",
    "year": "300 AC (After Conquest)",
    "season": "Late Summer",
    "technological_level": "Medieval with elements of magic",
    "culture_and_society": "Feudal society with noble houses, knights, and smallfolk",
    "religions": ["Faith of the Seven", "Old Gods of the Forest", "Lord of Light"],
    "political_climate": "Feudal system with power struggles among noble families",
    "magic_and_myths": "Magic exists in the world, with dragons, White Walkers, and prophecies playing significant roles"
  }
}'''   
    
    # Generate world context
    world_context_prompt = f"""Topic: {topic}
    Generate a detailed world context that includes:
    - Current era/time period
    - Year
    - Season
    - Technological level
    - Culture and society
    - Religions
    - Political climate
    - Magic and myths
    
    Format as a clear list of these contextual elements.
    Example:
    {example_json}

    Requirements: your response MUST be in valid JSON format
    """
    
    # Generate world context with error handling
    try:
        world_context_response, usage = call_ai_model("openai-gpt", world_context_prompt)
        total_ttfb += float(usage.get('ttfb_seconds', 0))
        cleaned_response = clean_json_response(world_context_response)
        ctx_data = json.loads(cleaned_response)
        ctx = ctx_data["world_or_simulation_context"]
        
        world_ctx = WorldContext(
            era=ctx["era"],
            year=ctx["year"],
            season=ctx["season"],
            technological_level=ctx["technological_level"],
            culture_and_society=ctx["culture_and_society"],
            religions=ctx["religions"],
            magic_and_myths=ctx["magic_and_myths"],
            political_climate=ctx["political_climate"]
        )
    except Exception as e:
        print(f"Error parsing world context: {e}")
        print("Response was:", world_context_response)
        return None

    example_json = '''{
  "meeting_setup": {
    "date": "1234/11/23",
    "time": "15:00 <time should be in military time>",

    "location": {
        "name": "Warehouse in San Diego",
        "coordinates": "35.6762° N, 139.6503° E",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "description": "Ultra-secure quantum computing facility hidden beneath the neon-lit streets"
    },

    "recent_events": [
        {
            "event_description": "The Lannisters have been ruling the Seven Kingdoms with an iron fist, causing unrest and discontent among the people. Khaleesi has gathered her council to strategize on reclaiming the throne."
        },        
        {
            "event_description": "The Lannisters have been facing internal strife, weakening their hold on the throne.."
        }
    ],

    "summary_of_last_meetings": "Previous meetings focused on strategizing alliances and assessing military strengths.",

    "room_setup": {
        "description": "The meeting room is arranged in a circular fashion to symbolize unity and equal importance",
        "seating_arrangement": [
            {"position": 0 (0 means Head), "name": "Khaleesi", "role": "Final authority and chairperson"},
            {"position": 1 (odd numbers are to the left of Head, the larger the number, the further left), "name": "Tyrion Lannister", "role": "Present arguments and insights"},
            {"position": 2 (even numbers are to the right of Head, the larger the number, the further right), "name": "Grand Maester Pycelle", "role": "Announce outcomes, if necessary"},
            {"position": -1 (-1 means Foot), "name": "Petyr Baelish", "role": "The treasurer of the realm, managing the royal treasury and economic policies"}
        ]
    },

    "purpose_and_context": {
        "purpose": "To strategize and plan the reclamation of the throne",
        "context": "In a world where the political climate is in turmoil, with various noble houses vying for power"
    },

    "goal": {
        "objectives": [
            "Develop a comprehensive strategy for reclaiming the throne.",
            "Address and resolve any immediate threats to the realm."
        ]
    },
    
    "briefing_materials": {
        "documents": [
            {
                "title": "Current Political Landscape", 
                "description": "A detailed report on the current alliances and conflicts among the noble houses."
            },
            {
                "title": "Economic Status Report", 
                "description": "An analysis of the realm's treasury, including debts, assets, and potential revenue streams."
            },
        ]
    },

    "protocol_reminder": {
        "speaking_order": [
            "Khaleesi opens the meeting and sets the agenda.",
            "Tyrion Lannister presents arguments and insights.",
            "Petyr Baelish discusses economic policies and treasury management.",
            "Grand Maester Pycelle summarizes discussions and announces outcomes.",
            "Khaleesi concludes the meeting with final decisions and directives."
        ],
        "customs": [
            "Address Khaleesi as 'Your Grace'",
            "Wait for Khaleesi to speak before voicing opinions",
            "Maintain decorum and respect towards all council members"
        ]    
    },

    "opening_message": {
        "speaker": "Khaleesi",
        "message": "Esteemed members of the council, we gather today under the shadow of uncertainty but with the light of hope. "
    },

    "agenda_outline": {
        "1": "Opening remarks by Queen Khaleesi",
        "2": "Update on Lannister military movements",
        "3": "Alliance proposals and considerations",
        "4": "Discussion on strategic battle plans",
        "5": "Next steps and assignments"
    }    
    

    

  }
}'''   

    # todo: - Tags, keywords and category of this meeting and its content
    # add a new summary to generate the above data later.
    
    # Generate meeting setup
    meeting_setup_prompt = f"""Topic: {topic}
    Generate meeting/conversation setup details including:
    - Date and time
    - Meeting location and its description
    - Recent events leading to this meeting
    - Summary of last meetings
    - Room setup and seating arrangement
    - Meeting purpose and goals
    - Briefing materials (documents, reports, etc.)
    - Protocol, speaking order and customs
    - Opening message and its speaker
    - Agenda outline (briefly outline the order of discussions)
        
    Format as a clear list of these meeting elements and respond as a valid JSON object, example:
    {example_json}

    Requirements: your response MUST be in valid JSON format.
    """
    
    meeting_setup_response, usage = call_ai_model("openai-gpt", meeting_setup_prompt)
    total_ttfb += float(usage.get('ttfb_seconds', 0))
    
    # Parse meeting setup
    try:
        meeting_setup = parse_meeting_setup_response(meeting_setup_response)
    except Exception as e:
        print(f"Error parsing meeting setup: {e}")
        print("Response was:", meeting_setup_response)
        return None

    # Handle None returns from parsing
    if not characters or not world_ctx or not meeting_setup:
        print("Error: Failed to parse one or more required components")
        return None

    # Create SetupData with all fields
    setup_data = SetupData(
        topic=topic,
        characters=characters,
        world_or_simulation_context=world_ctx,
        meeting_setup=meeting_setup,
        id="<not_ready>",
        version=os.getenv("VERSION", "2.0"),
        name="<not_ready>",
        simulation_time=int(total_ttfb * 1000)  # Convert to milliseconds
    )
    
    # Add debug prints
    print("\nDebug - Setup Data Values:")
    print(f"ID: {setup_data.id}")
    print(f"Version: {setup_data.version}")
    print(f"Name: {setup_data.name}")
    print(f"Simulation Time: {setup_data.simulation_time}")
    print(f"Logkeeper: {asdict(setup_data.logkeeper)}")
    
    # Convert to dictionary and save
    setup_dict = {
        "id": setup_data.id,
        "version": setup_data.version,
        "name": setup_data.name,
        "topic": setup_data.topic,
        "logkeeper": asdict(setup_data.logkeeper),
        "simulation_time": setup_data.simulation_time,
        "characters": [asdict(c) for c in setup_data.characters],
        "world_or_simulation_context": asdict(setup_data.world_or_simulation_context),
        "meeting_setup": asdict(setup_data.meeting_setup)
    }
    
    # Add debug print of final dict
    print("\nDebug - Final Setup Dict:")
    print(json.dumps(setup_dict, indent=2))
    
    write_json_to_file(setup_dict, "setup.json")
    print("Generated setup.json. Please review/modify as needed before running the conversation.")
    
    return setup_data

def handle_conversation_step(conversation_id: str, user_input: str):
    # ... existing code ...
    response_text, usage_info = call_ai_model(selected_model, formatted_prompt)
    
    # Store both response and usage info
    conversation_history.add_message(
        text=response_text,
        role="assistant",
        usage_info=usage_info
    )
    
    return response_text, usage_info
