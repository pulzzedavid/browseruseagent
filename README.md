# Browser Use Agent (BUA)

A sophisticated browser automation agent that can understand natural language instructions and automatically execute browser actions.

## Features

- **Natural Language Understanding**: Takes human language prompts and converts them to actionable browser tasks
- **Intelligent Planning**: Uses LLMs to break down complex tasks into executable steps
- **Browser Automation**: Built on Playwright for robust browser interaction
- **Modular Architecture**: Easy to extend with custom tools and integrations
- **State Management**: Maintains context and memory across sessions
- **Error Recovery**: Self-correcting capabilities when actions fail

## Architecture

The BUA follows the Observe-Reason-Act loop:

1. **Observe**: Captures current browser state (DOM, screenshots)
2. **Reason**: Analyzes state and plans next actions using LLM
3. **Act**: Executes planned actions and updates environment

## Project Structure

```
browseruseagent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database setup
│   │   └── security.py        # Security utilities
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent.py           # Agent state models
│   │   └── browser.py         # Browser interaction models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py   # Main agent logic
│   │   ├── browser_service.py # Browser automation
│   │   ├── llm_service.py     # LLM integration
│   │   └── tool_service.py    # Tool management
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── browser_tools.py   # Browser-specific tools
│   │   ├── system_tools.py    # System interaction tools
│   │   └── custom_tools.py    # Custom automation tools
│   └── api/
│       ├── __init__.py
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── agent.py       # Agent API endpoints
│       │   └── browser.py     # Browser control endpoints
│       └── dependencies.py    # API dependencies
├── tests/                     # Test suite
├── docker/                    # Docker configuration
├── alembic/                   # Database migrations
├── .env.example              # Environment variables template
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access the API**:
   - API documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Usage

### Basic Agent Request

```python
import requests

# Start a new agent session
response = requests.post("http://localhost:8000/agent/start", json={
    "task": "Go to Google and search for 'Python programming'",
    "url": "https://www.google.com"
})

session_id = response.json()["session_id"]

# Check status
status = requests.get(f"http://localhost:8000/agent/{session_id}/status")
print(status.json())
```

### Custom Tools

The BUA supports custom tools that can be registered at runtime:

```python
from app.tools.custom_tools import CustomTool

# Register a custom tool
tool = CustomTool(
    name="custom_action",
    description="Performs a custom action",
    function=your_custom_function
)
```

## Configuration

Key configuration options in `.env`:

- `OPENAI_API_KEY`: OpenAI API key for GPT models
- `GOOGLE_API_KEY`: Google API key for Gemini models
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection for task queue
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Development

### Running Tests

```bash
pytest tests/
```

### Database Migrations

```bash
alembic upgrade head
```

### Code Formatting

```bash
black app/ tests/
isort app/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
