"""
main.py

Command-line interface (CLI) entry point.
Usage:
  1) python main.py generate_setup
     - Prompts user for the topic and generates 'setup.json'
  2) python main.py run_conversation path/to/setup.json
     - Loads 'setup.json' and initiates the conversation loop
"""

import sys
import json
import os
import argparse
from cache_manager import init_cache  # Import this first

# Import other modules at the top level
from conversation_flow import generate_setup_data
from conversation_manager import ConversationManager
from data_structures import SetupData, ManagerConfig, Character, WorldContext, MeetingSetup, Location, Event, SeatingArrangement, RoomSetup, PurposeAndContext, Goal, BriefingMaterials, Document, ProtocolReminder, OpeningMessage, Logkeeper
from utils import write_json_to_file, get_timestamp
from dataclasses import asdict

def cli_generate_setup():
    """
    Asks the user for the meeting topic, then generates setup.json.
    """
    topic = input("What would you like the group conversation or meeting to be about? ")
    print(f"Debug: Received topic: {topic}")
    data = generate_setup_data(topic)
    
    if data is None:
        print("Failed to generate setup data. Please try again.")
        return
    
    # Convert dataclass to dictionary for JSON dumping
    setup_dict = {
        "topic": data.topic,
        "characters": [asdict(c) for c in data.characters],
        "world_or_simulation_context": asdict(data.world_or_simulation_context),
        "meeting_setup": asdict(data.meeting_setup)
    }

    output_file = "setup.json"
    write_json_to_file(setup_dict, output_file)
    print(f"Generated {output_file}. Please review/modify as needed before running the conversation.")

def cli_run_conversation(setup_file: str):
    """Run a conversation from a setup file"""
    try:
        # Load setup file
        with open(setup_file, 'r') as f:
            setup_dict = json.load(f)
        
        # Convert dictionary to SetupData object
        characters = [Character(**c) for c in setup_dict["characters"]]
        world_ctx = WorldContext(**setup_dict["world_or_simulation_context"])
        
        # Convert meeting setup nested objects
        meeting_dict = setup_dict["meeting_setup"]
        location = Location(**meeting_dict["location"])
        events = [Event(**e) for e in meeting_dict["recent_events"]]
        seating = [SeatingArrangement(**s) for s in meeting_dict["room_setup"]["seating_arrangement"]]
        room_setup = RoomSetup(
            description=meeting_dict["room_setup"]["description"],
            seating_arrangement=seating
        )
        purpose_ctx = PurposeAndContext(**meeting_dict["purpose_and_context"])
        goal = Goal(objectives=meeting_dict["goal"]["objectives"])
        docs = [Document(**d) for d in meeting_dict["briefing_materials"]["documents"]]
        briefing = BriefingMaterials(documents=docs)
        protocol = ProtocolReminder(**meeting_dict["protocol_reminder"])
        opening = OpeningMessage(**meeting_dict["opening_message"])
        
        meeting_setup = MeetingSetup(
            date=meeting_dict["date"],
            time=meeting_dict["time"],
            location=location,
            recent_events=events,
            summary_of_last_meetings=meeting_dict["summary_of_last_meetings"],
            tags_keywords=meeting_dict.get("tags_keywords", ["<not_ready>"]),
            category=meeting_dict.get("category", "<not_ready>"),
            room_setup=room_setup,
            purpose_and_context=purpose_ctx,
            goal=goal,
            briefing_materials=briefing,
            protocol_reminder=protocol,
            opening_message=opening,
            agenda_outline=meeting_dict["agenda_outline"]
        )
        
        # Create SetupData object
        setup_data = SetupData(
            id=setup_dict["id"],
            version=setup_dict["version"],
            name=setup_dict["name"],
            topic=setup_dict["topic"],
            logkeeper=Logkeeper(**setup_dict["logkeeper"]),
            simulation_time=setup_dict["simulation_time"],
            characters=characters,
            world_or_simulation_context=world_ctx,
            meeting_setup=meeting_setup
        )
        
        # Get manager model with improved prompt
        available_models = ["openai-gpt", "claude", "gemini", "deepseek", "ollama"]
        model_prompt = (
            "Enter a model name for the 'group chat manager'\n"
            f"Available models: {', '.join(available_models)}\n"
            "(leave blank for random): "
        )
        manager_model = input(model_prompt)
        if not manager_model:
            import random
            manager_model = random.choice(available_models)
        
        # Create manager config
        manager_config = ManagerConfig(manager_model=manager_model)
        
        # Create log file path
        timestamp = get_timestamp().replace(":", "").replace(" ", "_")
        log_file_path = f"meeting_log_{timestamp}.json"
        print(f"\nConversation log will be saved to: {log_file_path}")
        
        # Initialize conversation manager
        manager = ConversationManager(
            setup_data=setup_data,
            manager_config=manager_config,
            log_file_path=log_file_path
        )
        
        # Start conversation
        print(f"\nStarting conversation with manager model: {manager_model}")
        manager.run_conversation()
        
        print("\nConversation finished!")
        print(f"Log saved to: {log_file_path}")
        
    except FileNotFoundError:
        print(f"Error: Setup file '{setup_file}' not found")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in setup file '{setup_file}'")
    except Exception as e:
        print(f"Error running conversation: {e}")
        import traceback
        traceback.print_exc()  # Print full error trace for debugging

def main():
    # Initialize cache manager first
    init_cache()
    
    parser = argparse.ArgumentParser(description="AI Group Chat Simulator CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Generate setup command
    generate_parser = subparsers.add_parser("generate_setup", help="Generate a new conversation setup")
    
    # Run conversation command
    run_parser = subparsers.add_parser("run_conversation", help="Run a conversation from setup file")
    run_parser.add_argument("setup_file", help="Path to the setup.json file")
    
    # Clear cache command
    clear_cache_parser = subparsers.add_parser("clear-cache", help="Clear the response cache")

    args = parser.parse_args()

    if args.command == "generate_setup":
        cli_generate_setup()
    elif args.command == "run_conversation":
        cli_run_conversation(args.setup_file)
    elif args.command == "clear-cache":
        cli_clear_cache()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
