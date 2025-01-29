"""
fastapi_app.py

A simple FastAPI application providing endpoints to:
 1) Generate setup JSON
 2) Run the conversation (or retrieve logs)
"""

import os
import json
import random
from typing import Optional
from fastapi_app import FastAPI, Body

from conversation_flow import generate_setup_data
from data_structures import SetupData, ManagerConfig
from conversation_manager import ConversationManager
from utils import get_timestamp
from cache_manager import init_cache, DEFAULT_CACHE_SEED

app = FastAPI()

@app.post("/generate_setup")
def api_generate_setup(
    request: dict = Body(...),  # {"topic": "...", "cache_seed": 42}
):
    topic = request["topic"]
    cache_seed = request.get("cache_seed", DEFAULT_CACHE_SEED)
    
    init_cache(cache_seed)
    data = generate_setup_data(topic)
    return data

@app.post("/run_conversation")
def api_run_conversation(
    setup: dict = Body(...),
    manager_model: Optional[str] = None
):
    """
    Run the AI-driven conversation given the setup JSON object (same format as SetupData).
    'manager_model' can be optionally provided, otherwise chosen randomly.
    """
    # Convert dict to SetupData object
    from data_structures import Character, WorldContext, MeetingSetup

    characters = []
    for cdata in setup["characters"]:
        characters.append(
            Character(
                name=cdata["name"],
                position=cdata["position"],
                role=cdata["role"],
                hierarchy=cdata["hierarchy"],
                assigned_model=cdata["assigned_model"]
            )
        )
    wctx = setup["world_or_simulation_context"]
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
    mset = setup["meeting_setup"]
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
        topic=setup["topic"],
        characters=characters,
        world_or_simulation_context=world_ctx,
        meeting_setup=meeting_setup
    )

    # Manager model
    if not manager_model:
        manager_model = random.choice(["openai-gpt", "claude", "gemini", "deepseek", "ollama"])

    manager_config = ManagerConfig(manager_model=manager_model)

    # Log file path
    timestamp = get_timestamp().replace(":", "").replace(" ", "_")
    log_file_path = f"meeting_log_{timestamp}.json"

    cm = ConversationManager(setup_data, manager_config, log_file_path)
    cm.run_conversation()

    # Now read the entire log and return
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            conversation_log = json.load(f)
    except FileNotFoundError:
        conversation_log = []

    return {
        "success": True,
        "log_file": log_file_path,
        "conversation_log": conversation_log
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response_text, usage_info = process_message(request.message, request.conversation_id)
        return {
            "response": response_text,
            "usage": usage_info,
            "status": "success"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
