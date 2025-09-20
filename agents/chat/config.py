"""Configuration management for the AutoGen Chat Application.

This module handles all configuration settings, environment variables,
and default values for the application.
"""

import os
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv


load_dotenv()


def load_system_prompt() -> str:
    """Load the system prompt from the markdown file and inject current date.
    
    Returns:
        str: The system prompt content with current date included.
        
    Raises:
        FileNotFoundError: If the prompt file is not found.
        IOError: If there's an error reading the file.
    """
    prompt_file_path = os.path.join(
        os.path.dirname(__file__), 
        "prompts", 
        "parra_glideator_system_prompt.md"
    )
    
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            prompt_content = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"System prompt file not found at {prompt_file_path}. "
            "Please ensure the file exists."
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
    agent_system_message: str
    max_tool_iterations: int
    parallel_tool_calls: bool
    # UI settings
    chat_height: int
    
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
        
        return cls(
            # OpenAI settings
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            
            # MCP server settings  
            mcp_server_url=os.getenv("MCP_SERVER_URL", "https://www.parra-glideator.com/mcp"), # "http://127.0.0.1:8000/mcp"
            
            # Gradio interface settings
            gradio_host=os.getenv("GRADIO_SERVER_HOST", "127.0.0.1"),
            gradio_port=int(os.getenv("GRADIO_SERVER_PORT", "7863")),
            gradio_share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
            
            # Agent settings
            agent_name=os.getenv("AGENT_NAME", "ParraGlideator"),
            agent_system_message=os.getenv("AGENT_SYSTEM_MESSAGE", load_system_prompt()),
            max_tool_iterations=int(os.getenv("MAX_TOOL_ITERATIONS", "10")),
            parallel_tool_calls=os.getenv("PARALLEL_TOOL_CALLS", "false").lower() == "true",
            # UI settings
            chat_height=int(os.getenv("CHAT_HEIGHT", "500")),
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
