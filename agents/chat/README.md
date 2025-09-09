# AutoGen Chat Application

A simple chat interface using AutoGen agents with MCP (Model Context Protocol) tools, refactored from the original Jupyter notebook.

## Features

- 🤖 AI-powered chat interface using AutoGen agents
- 🔧 Integration with MCP tools for extended functionality
- 🎨 Modern Gradio web interface
- ⚙️ Configurable settings via environment variables
- 🔄 Conversation reset functionality
- 🛡️ Error handling and validation

## Prerequisites

- Python 3.13 or higher
- OpenAI API key
- MCP server running on `http://127.0.0.1:8000/mcp`

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd agents/chat
   ```

2. **Install dependencies:**
   ```bash
   # Using pip
   pip install -r requirements.txt
   
   # Or using poetry (if you have the pyproject.toml)
   poetry install
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
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

# MCP server settings
MCP_SERVER_URL=http://127.0.0.1:8000/mcp

# Agent settings
MAX_TOOL_ITERATIONS=10

# Gradio interface settings
GRADIO_SERVER_HOST=127.0.0.1
GRADIO_SERVER_PORT=7863
```

### Advanced Configuration

You can also modify the `config.py` file to change default settings or add new configuration options.

## Project Structure

```
agents/chat/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Poetry configuration
├── README.md          # This file
└── notebooks/
    └── client.ipynb   # Original notebook
```

## Key Improvements from Notebook

1. **Modular Structure**: Code is organized into classes and functions
2. **Error Handling**: Comprehensive error handling and validation
3. **Configuration Management**: Centralized configuration with environment variable support
4. **Type Hints**: Added type annotations for better code clarity
5. **Documentation**: Comprehensive docstrings and comments
6. **Modern Gradio**: Updated to use the latest Gradio message format
7. **Better UI**: Improved interface with better layout and styling

## Troubleshooting

### Common Issues

1. **"OpenAI API key not set"**
   - Make sure you have set the `OPENAI_API_KEY` environment variable
   - Check that your `.env` file is in the correct location

2. **"MCP server connection failed"**
   - Ensure your MCP server is running on the configured URL
   - Check the `MCP_SERVER_URL` configuration

3. **"Module not found" errors**
   - Install all dependencies: `pip install -r requirements.txt`
   - Make sure you're using Python 3.13+

4. **Gradio interface warnings or errors**
   - The application uses the latest Gradio message format
   - Older Gradio versions may show deprecation warnings (these are safe to ignore)
   - For auto-refresh functionality, use the "🔄 Refresh Status" button

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Verify your environment variables are set correctly
3. Ensure all dependencies are installed
4. Check that the MCP server is running

## Development

To modify the application:

1. **Add new features**: Extend the `AutoGenChatApp` class
2. **Change configuration**: Modify `config.py` or use environment variables
3. **Update UI**: Modify the `create_interface()` method in `app.py`
4. **Add new tools**: Update the MCP server configuration

## License

This project is part of the Glideator repository.
