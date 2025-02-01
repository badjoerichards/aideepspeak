# AI Conversations/Meetings/Group Chat Simulation

## Creator's Note

I believe that conversation and dialogue are the best ways for any entity — human or AI — to learn.

This project is an attempt to create a sophisticated AI-powered group chat simulator that can create and manage multi-character conversations using various AI models. The system supports both CLI and API interfaces for generating conversation setups and running interactive discussions.

Currently, the following AI models are supported:
- OpenAI GPT
- Anthropic Claude
- Google Gemini
- DeepSeek
- Ollama

My initial experiments revolved around a King’s meeting with characters from Game of Thrones, where the stakes are undeniably high. From there, the simulator can evolve to real-world office meetings or even covert backdoor/backroom gatherings between AIs.

Be warned, this is work in progress.

- Mr. J

## Features

- Generate detailed conversation setups with characters, world context, and meeting parameters
- Support for multiple AI models (OpenAI GPT, Claude, Gemini, DeepSeek, Ollama)
- CLI interface for interactive usage
- FastAPI-based REST API for integration
- Detailed conversation logging with usage tracking
- Customizable character roles and hierarchies
- Flexible meeting contexts and scenarios


## What can this be used for?

- Real-world profession and meeting simulation
- AI-powered role-playing games
- Storytelling
- You are the artist, be creative. You set up the meeting, then let it run.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-group-chat-simulator.git
cd ai-group-chat-simulator
```

2. Set up a virtual environment (choose either A or B):

### A. Using venv (Python's built-in virtual environment)
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Unix or MacOS
source venv/bin/activate
```

### B. Using Conda
```bash
# Create a new conda environment
conda create -n ai-chat python=3.11.2

# Activate the conda environment
conda activate ai-chat

# Optional: if you need additional conda packages
conda install -c conda-forge fastapi uvicorn
```

3. Install required packages:
```bash
# If using venv or conda
pip install -r requirements.txt
```

## Configuration

1. Create a .env file from the template:
```bash
# Copy the example env file
cp .env.example .env

# Edit the .env file with your API keys
nano .env  # or use your preferred editor
```

2. Add your API keys to the .env file:
```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_key_here

# Anthropic API Configuration
ANTHROPIC_API_KEY=your_anthropic_key_here

# Google (Gemini) API Configuration
GOOGLE_API_KEY=your_google_key_here

# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_key_here

# Ollama Configuration (if needed)
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=llama2
```

Note: Keep your .env file secure and never commit it to version control.

## Usage

### CLI Interface (main.py)

The CLI supports two main operations:

1. Generate a setup configuration:
```bash
python main.py generate_setup
```

This will:
- Prompt you for a conversation topic
- Generate a `setup.json` file with characters and context
- Allow you to review and modify the setup
- Create a setup.json file with:
  - Unique conversation ID
  - Version tracking
  - Simulation metrics
  - Character definitions
  - World context
  - Meeting parameters
  - Logkeeper configuration

2. Run a conversation:
```bash
python main.py run_conversation setup.json
```

This will:
- Load the specified setup file
- Allow you to choose or randomly assign an AI manager
- Start the interactive conversation
- Save the conversation log to a timestamped JSON file

### FastAPI Interface (fastapi_app.py)

1. Start the API server:
```bash
uvicorn fastapi_app:app --reload
```

2. Available endpoints:

- Generate Setup:
```bash
POST /generate_setup
Content-Type: application/json

{
    "topic": "Your conversation topic"
}
```

- Run Conversation:
```bash
POST /run_conversation
Content-Type: application/json

{
    "setup": {
        // Your setup JSON structure
    },
    "manager_model": "optional-model-name"
}
```

- Chat Endpoint:
```bash
POST /chat
Content-Type: application/json

{
    "message": "Your message",
    "conversation_id": "unique_conversation_id"
}
```

## Response Format

The chat endpoint returns responses in the following format:
```json
{
    "response": "AI response text",
    "usage": {
        "prompt_tokens": 123,
        "completion_tokens": 456,
        "total_tokens": 579
    },
    "status": "success"
}
```


## Caching System

The project includes a sophisticated caching system that:
- Caches AI responses with configurable expiry
- Uses SHA-256 hashing for cache keys
- Supports seeding for reproducible results
- Automatically prunes expired entries
- Provides debug information for cache operations

## Output Files

- setup.json: Contains the conversation configuration
- meeting_log_*.json: Detailed conversation logs
- cache/ai_responses_cache.json: Cached AI responses

## Project Structure

- `main.py`: CLI interface
- `fastapi_app.py`: REST API interface
- `conversation_manager.py`: Core conversation logic
- `conversation_flow.py`: Conversation flow and setup generation
- `data_structures.py`: Data models and structures
- `ai_connectors.py`: AI model integration
- `utils.py`: Utility functions

## Logging

Conversation logs are saved in JSON format with timestamps:
- CLI: `meeting_log_YYYYMMDD_HHMMSS.json`
- API: Accessible through the response payload

## Troubleshooting

Common issues and solutions:

1. Conda environment not found:
```bash
# List all conda environments
conda env list

# Recreate environment if needed
conda env remove -n ai-chat
conda create -n ai-chat python=3.9
```

2. Package conflicts:
```bash
# Clean conda cache
conda clean --all

# Update conda
conda update -n base -c defaults conda
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to the various AI model providers
- Contributors and testers
- Open source community
