# Parra-Glideator Chat Application

A specialized chat interface for testing the Parra-Glideator MCP (Model Context Protocol) server. This application uses AutoGen agents with paragliding-specific tools and data to help pilots plan flights, check weather conditions, and explore flying sites.

## Purpose

This chat application serves as a test client for the Parra-Glideator MCP server, allowing you to interact with paragliding data including:
- 🗺️ Site information and details
- 📊 Historical flight statistics  
- 🌤️ Weather forecasts and flyability predictions
- ✈️ Trip planning and recommendations

## Features

- 🤖 AI-powered paragliding assistant using AutoGen agents
- 🔧 Direct integration with Parra-Glideator MCP server tools
- 🎨 Modern Gradio web interface with real-time streaming
- 🎭 Multiple system prompt personalities (neutral, themed, generic)
- ⚙️ Dynamic model and prompt switching during conversations
- 🔄 Conversation reset functionality
- 🛡️ Comprehensive error handling and validation
- 📊 OpenTelemetry tracing for debugging and performance analysis

## Prerequisites

- Python 3.10 or higher
- OpenAI API key
- Access to the Parra-Glideator MCP server (default: `https://www.parra-glideator.com/mcp`)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd agents/chat
   ```

2. **Install dependencies:**
   ```bash 
   poetry install
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Optional: Enable tracing
   TRACING_ENABLED=true
   ```

## Usage

### Basic Usage

Run the application:
```bash
python app.py
```

The web interface will be available at `http://127.0.0.1:7863`

### Configuration

You can customize the application behavior using environment variables:

```env
# OpenAI settings
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
AVAILABLE_MODELS=gpt-4o-mini,gpt-4o,gpt-5-nano,gpt-5-mini,gpt-5

# MCP server settings
MCP_SERVER_URL=https://www.parra-glideator.com/mcp

# Agent settings
AGENT_NAME=ParraGlideator
AGENT_SYSTEM_PROMPT_NAME=parraglideator_neutral
MAX_TOOL_ITERATIONS=10
PARALLEL_TOOL_CALLS=false

# Gradio interface settings
GRADIO_SERVER_HOST=127.0.0.1
GRADIO_SERVER_PORT=7863
GRADIO_SHARE=false
CHAT_HEIGHT=500

# Tracing settings (optional)
TRACING_ENABLED=true
TRACING_OTLP_ENDPOINT=http://localhost:4317
TRACING_CONSOLE_OUTPUT=false
TRACING_SERVICE_NAME=parra-glideator-chat
```

### Available System Prompts

The application includes several pre-configured system prompts:

- **`parraglideator_neutral`** - Casual, pilot-friendly tone with practical advice
- **`parraglideator_themed`** - Themed Roman gladiator parrot character 
- **`generic_assistant`** - Generic AI assistant without paragliding specialization

You can switch between prompts using the web interface or by setting `AGENT_SYSTEM_PROMPT_NAME`.

### Tracing and Observability (Optional)

The application supports OpenTelemetry tracing for debugging and performance analysis. To enable tracing:

1. **Set environment variables:**
   ```env
   TRACING_ENABLED=true
   TRACING_OTLP_ENDPOINT=http://localhost:4317
   ```

2. **Set up Jaeger for trace visualization (optional):**
   ```bash
   # Run Jaeger using Docker
   docker run -d --name jaeger \
     -e COLLECTOR_OTLP_ENABLED=true \
     -p 16686:16686 \
     -p 4317:4317 \
     -p 4318:4318 \
     jaegertracing/all-in-one:latest
   ```

3. **View traces:**
   - Open http://localhost:16686 in your browser
   - Select "parra-glideator-chat" service to view traces

**Tracing Environment Variables:**
- `TRACING_ENABLED`: Enable/disable tracing (default: false)
- `TRACING_OTLP_ENDPOINT`: OTLP endpoint URL (default: http://localhost:4317)
- `TRACING_CONSOLE_OUTPUT`: Output traces to console (default: false)
- `TRACING_SERVICE_NAME`: Service name in traces (default: parra-glideator-chat)

### Advanced Configuration

You can also modify the `config.py` file to change default settings or add new configuration options.

## Project Structure

```
agents/chat/
├── app.py              # Main Gradio application with streaming UI
├── agent.py            # AutoGen agent logic and MCP integration  
├── config.py           # Configuration management and prompt loading
├── tracing.py          # OpenTelemetry tracing setup
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Poetry configuration  
├── README.md          # This file
├── prompts/           # System prompt templates
│   ├── parraglideator_neutral.md
│   ├── parraglideator_themed.md
│   └── generic_assistant.md
├── static/            # Static assets
│   └── logo192.png
└── notebooks/         # Original development notebooks
    └── client.ipynb
```

