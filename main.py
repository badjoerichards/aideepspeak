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
from data_structures import SetupData, ManagerConfig
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

def cli_run_conversation(setup_path: str):
    """
    Loads setup.json, allows user to confirm or modify, then runs the conversation loop.
    """
    if not os.path.exists(setup_path):
        print(f"Error: Setup file {setup_path} not found.")
        return

    # Load the setup data
    with open(setup_path, "r", encoding="utf-8") as f:
        setup_dict = json.load(f)

    print("Current Setup Data (from JSON):")
    print(json.dumps(setup_dict, indent=2, ensure_ascii=False))

    confirmation = input("Would you like to edit this JSON? (y/n): ")
    if confirmation.lower() == "y":
        print("Edit the file externally, then press Enter when done.")
        input()

        # Reload
        with open(setup_path, "r", encoding="utf-8") as f:
            setup_dict = json.load(f)

    # Construct SetupData object from dict
    # For brevity, we skip robust validation. In a real app, use Pydantic or similar.
    from data_structures import Character, WorldContext, MeetingSetup, SetupData

    characters = []
    for cdata in setup_dict["characters"]:
        characters.append(
            Character(
                name=cdata["name"],
                position=cdata["position"],
                role=cdata["role"],
                hierarchy=cdata["hierarchy"],
                assigned_model=cdata["assigned_model"]
            )
        )
    wctx = setup_dict["world_or_simulation_context"]
    world_ctx = WorldContext(
        era=wctx["era"],
        year=wctx["year"],
        season=wctx["season"],
        technological_level=wctx["technological_level"],
        culture_and_society=wctx["culture_and_society"],
        religions=wctx["religions"],
        magic_and_myths=wctx["magic_and_myths"],
        political_climate=wctx["political_climate"]
    )
    mset = setup_dict["meeting_setup"]
    meeting_setup = MeetingSetup(
        date=mset["date"],
        time=mset["time"],
        meeting_location=mset["meeting_location"],
        meeting_location_description=mset["meeting_location_description"],
        recent_events=mset["recent_events"],
        summary_of_last_meetings=mset["summary_of_last_meetings"],
        tags_keywords=mset["tags_keywords"],
        category=mset["category"],
        room_setup=mset["room_setup"],
        purpose_and_context=mset["purpose_and_context"],
        goal=mset["goal"],
        briefing_materials=mset["briefing_materials"],
        protocol_reminder=mset["protocol_reminder"],
        customary_opening_message=mset["customary_opening_message"],
        agenda_outline=mset["agenda_outline"]
    )

    setup_data = SetupData(
        topic=setup_dict["topic"],
        characters=characters,
        world_or_simulation_context=world_ctx,
        meeting_setup=meeting_setup
    )

    # Let user pick or randomly choose the manager model
    manager_model = input("Enter a model name for the 'group chat manager' (leave blank for random): ")
    if not manager_model:
        import random
        manager_model = random.choice(["openai-gpt", "claude", "gemini", "deepseek", "ollama"])

    manager_config = ManagerConfig(manager_model=manager_model)

    # Prepare a log file
    timestamp = get_timestamp().replace(":", "").replace(" ", "_")
    log_file_path = f"meeting_log_{timestamp}.json"

    print(f"Conversation log will be saved to: {log_file_path}")

    # Run the conversation
    cm = ConversationManager(setup_data, manager_config, log_file_path)
    cm.run_conversation()

    print("\nConversation finished!")
    print(f"Log is saved in {log_file_path}.")
    print("Goodbye.")

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    # Generate setup command
    setup_parser = subparsers.add_parser("generate_setup")
    setup_parser.add_argument("--cache-seed", type=int, default=69,
                            help="Seed for response caching (default: 69)")
    
    # Clear cache command
    clear_cache_parser = subparsers.add_parser("clear-cache")
    
    args = parser.parse_args()
    
    # Initialize cache manager before anything else
    cache_seed = getattr(args, 'cache_seed', 69)
    cache_manager = init_cache(cache_seed)
    
    if args.command == "generate_setup":
        cli_generate_setup()
    elif args.command == "clear-cache":
        cache_manager.clear()
        print("Cache cleared successfully")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
