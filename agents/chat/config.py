"""Configuration management for the AutoGen Chat Application.

This module handles all configuration settings, environment variables,
and default values for the application.
"""

import os
from typing import Optional
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class AppConfig:
    """Configuration settings for the AutoGen Chat Application."""
    
    # OpenAI settings
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    
    # MCP server settings
    mcp_server_url: str = "http://127.0.0.1:8000/mcp"
    
    # Gradio interface settings
    gradio_host: str = "127.0.0.1"
    gradio_port: int = 7863
    gradio_share: bool = False
    
    # Agent settings
    agent_name: str = "assistant"
    agent_system_message: str = "You are a helpful AI assistant with access to various tools."
    
    # UI settings
    chat_height: int = 500
    app_title: str = "AutoGen Chat Application"
    
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
            mcp_server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp"),
            
            # Gradio interface settings
            gradio_host=os.getenv("GRADIO_SERVER_HOST", "127.0.0.1"),
            gradio_port=int(os.getenv("GRADIO_SERVER_PORT", "7863")),
            gradio_share=os.getenv("GRADIO_SHARE", "false").lower() == "true",
            
            # Agent settings
            agent_name=os.getenv("AGENT_NAME", "assistant"),
            agent_system_message=os.getenv(
                "AGENT_SYSTEM_MESSAGE", 
                "You are a helpful AI assistant with access to various tools."
            ),
            
            # UI settings
            chat_height=int(os.getenv("CHAT_HEIGHT", "500")),
            app_title=os.getenv("APP_TITLE", "AutoGen Chat Application"),
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
