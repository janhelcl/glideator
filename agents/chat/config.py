"""Configuration management for the AutoGen Chat Application.

This module handles all configuration settings, environment variables,
and default values for the application.
"""

import os
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv


load_dotenv()


def _prompts_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "prompts")


def list_available_prompts() -> List[str]:
    """List available prompt names (without extension) from the prompts directory."""
    directory = _prompts_dir()
    if not os.path.isdir(directory):
        return []
    names: List[str] = []
    for fname in os.listdir(directory):
        if fname.lower().endswith(".md"):
            names.append(os.path.splitext(fname)[0])
    names.sort()
    return names


def load_prompt_by_name(name: str) -> str:
    """Load a system prompt by its base filename (without extension) and inject current date.
    
    Args:
        name: Base filename of the prompt (without .md)
    
    Returns:
        The prompt content with current date context appended.
    """
    prompt_file_path = os.path.join(_prompts_dir(), f"{name}.md")
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            prompt_content = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"System prompt file not found at {prompt_file_path}. Please ensure the file exists."
        )
    except IOError as e:
        raise IOError(f"Error reading system prompt file: {str(e)}")

    # Add current date information
    current_date = datetime.now()
    date_info = f"""

## Current Context
**Today's Date**: {current_date.strftime("%A, %B %d, %Y")} ({current_date.strftime("%Y-%m-%d")})
**Current Time**: {current_date.strftime("%H:%M")} (local time)

*Note: Weather forecasts are typically available for the next 7 days from today. Historical statistics show patterns across multiple years of flight data.*
"""

    return prompt_content + date_info


def load_system_prompt() -> str:
    """Backward-compatible loader for the default system prompt file."""
    # Default to the original file name without extension
    return load_prompt_by_name("parra_glideator_system_prompt")


@dataclass
class AppConfig:
    """Configuration settings for the AutoGen Chat Application."""
    
    # OpenAI settings
    openai_api_key: str
    openai_model: str
    
    # MCP server settings
    mcp_server_url: str
    
    # Gradio interface settings
    gradio_host: str
    gradio_port: int
    gradio_share: bool
    
    # Agent settings
    agent_name: str
    agent_system_prompt_name: str
    agent_system_message: str
    max_tool_iterations: int
    parallel_tool_calls: bool
    # Selection lists
    available_models: List[str]
    available_prompts: List[str]
    # UI settings
    chat_height: int
    
    # Tracing settings
    tracing_enabled: bool
    tracing_otlp_endpoint: str
    tracing_console_output: bool
    tracing_service_name: str
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables.
        
        Returns:
            AppConfig: Configuration instance with values from environment variables.
            
        Raises:
            ValueError: If required environment variables are not set.
        """
        # Required environment variables
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        # Parse available models (comma-separated) and ensure current model is present
        default_models = "gpt-4o-mini,gpt-4o,gpt-5-nano,gpt-5-mini,gpt-5"
        available_models = [m.strip() for m in os.getenv("AVAILABLE_MODELS", default_models).split(",") if m.strip()]
        openai_model_env = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if openai_model_env not in available_models:
            available_models.append(openai_model_env)

        # Prompts list from directory
        available_prompts = list_available_prompts()
        default_prompt_name = os.getenv("AGENT_SYSTEM_PROMPT_NAME", "parraglideator_neutral")
        if available_prompts and default_prompt_name not in available_prompts:
            # If the specified default isn't found, fall back to first available
            default_prompt_name = available_prompts[0]

        return cls(
            # OpenAI settings
            openai_api_key=openai_api_key,
            openai_model=openai_model_env,
            
            # MCP server settings  
            mcp_server_url=os.getenv("MCP_SERVER_URL", "https://www.parra-glideator.com/mcp"), # "http://127.0.0.1:8000/mcp"
            
            # Gradio interface settings
            gradio_host=os.getenv("GRADIO_SERVER_HOST", "127.0.0.1"),
            gradio_port=int(os.getenv("GRADIO_SERVER_PORT", "7863")),
            gradio_share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
            
            # Agent settings
            agent_name=os.getenv("AGENT_NAME", "ParraGlideator"),
            agent_system_prompt_name=default_prompt_name,
            agent_system_message=os.getenv("AGENT_SYSTEM_MESSAGE", load_prompt_by_name(default_prompt_name) if default_prompt_name else load_system_prompt()),
            max_tool_iterations=int(os.getenv("MAX_TOOL_ITERATIONS", "10")),
            parallel_tool_calls=os.getenv("PARALLEL_TOOL_CALLS", "false").lower() == "true",
            available_models=available_models,
            available_prompts=available_prompts,
            # UI settings
            chat_height=int(os.getenv("CHAT_HEIGHT", "500")),
            
            # Tracing settings
            tracing_enabled=os.getenv("TRACING_ENABLED", "false").lower() == "true",
            tracing_otlp_endpoint=os.getenv("TRACING_OTLP_ENDPOINT", "http://localhost:4317"),
            tracing_console_output=os.getenv("TRACING_CONSOLE_OUTPUT", "false").lower() == "true",
            tracing_service_name=os.getenv("TRACING_SERVICE_NAME", "parra-glideator-chat"),
        )

    def validate(self) -> None:
        """Validate configuration settings.
        
        Raises:
            ValueError: If any configuration setting is invalid.
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        if not self.mcp_server_url:
            raise ValueError("MCP server URL is required")
            
        if not (1000 <= self.gradio_port <= 65535):
            raise ValueError("Gradio port must be between 1000 and 65535")
            
        if self.chat_height < 200:
            raise ValueError("Chat height must be at least 200 pixels")
            
        if self.max_tool_iterations < 1:
            raise ValueError("Max tool iterations must be at least 1")


def load_config() -> AppConfig:
    """Load and validate application configuration.
    
    Returns:
        AppConfig: Validated configuration instance.
        
    Raises:
        ValueError: If configuration is invalid or required values are missing.
    """
    config = AppConfig.from_env()
    config.validate()
    return config
