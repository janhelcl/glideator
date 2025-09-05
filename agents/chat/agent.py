"""Agent logic for the AutoGen Chat Application.

This module contains the agent initialization, management, and interaction logic
separated from the UI components.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import (
    StreamableHttpServerParams,
    mcp_server_tools,
)

from config import AppConfig

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Response from a chat interaction."""
    content: str
    error: Optional[str] = None
    success: bool = True


class AutoGenAgent:
    """Manages the AutoGen agent and its interactions."""
    
    def __init__(self, config: AppConfig):
        """Initialize the AutoGen agent.
        
        Args:
            config: Application configuration.
        """
        self.config = config
        self.agent: Optional[AssistantAgent] = None
        self.tools: List[Any] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the agent with MCP tools and model client.
        
        Raises:
            Exception: If initialization fails.
        """
        if self._initialized:
            logger.warning("Agent already initialized")
            return
            
        try:
            logger.info("Initializing AutoGen agent...")
            
            # Set up MCP server connection
            server = StreamableHttpServerParams(
                url=self.config.mcp_server_url,
            )
            
            # Get tools from MCP server
            logger.info(f"Connecting to MCP server at {self.config.mcp_server_url}")
            self.tools = await mcp_server_tools(server)
            logger.info(f"Loaded {len(self.tools)} tools from MCP server")
            
            # Create OpenAI model client
            model = OpenAIChatCompletionClient(
                model=self.config.openai_model,
                api_key=self.config.openai_api_key
            )
            
            # Create the assistant agent
            self.agent = AssistantAgent(
                name=self.config.agent_name,
                model_client=model,
                tools=self.tools,
                system_message=self.config.agent_system_message,
                reflect_on_tool_use=True
            )
            
            self._initialized = True
            logger.info("Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            self._initialized = False
            raise Exception(f"Agent initialization failed: {str(e)}")
    
    async def chat(self, message: str) -> ChatResponse:
        """Process a chat message and return the agent's response.
        
        Args:
            message: User message to process.
            
        Returns:
            ChatResponse: The agent's response or error information.
        """
        if not self._initialized or not self.agent:
            return ChatResponse(
                content="",
                error="Agent not initialized. Please restart the application.",
                success=False
            )
        
        try:
            logger.info(f"Processing message: {message[:100]}...")
            
            # Run the agent with the user message
            result = await self.agent.run(task=message)
            
            # Extract the agent's reply from the messages
            reply = ""
            for m in reversed(result.messages):
                if isinstance(m, TextMessage) and m.source == self.agent.name:
                    reply = m.content
                    break
            
            if not reply:
                reply = "I'm sorry, I couldn't process your request."
                
            logger.info("Message processed successfully")
            return ChatResponse(content=reply)
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            return ChatResponse(
                content="",
                error=error_msg,
                success=False
            )
    
    async def reset(self) -> bool:
        """Reset the agent's conversation state.
        
        Returns:
            bool: True if reset was successful, False otherwise.
        """
        if not self._initialized or not self.agent:
            logger.warning("Cannot reset: Agent not initialized")
            return False
            
        try:
            logger.info("Resetting agent conversation state")
            await self.agent.on_reset(CancellationToken())
            logger.info("Agent reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting agent: {str(e)}")
            return False
    
    def get_tools_info(self) -> Dict[str, Any]:
        """Get information about available tools.
        
        Returns:
            Dict containing tools information.
        """
        return {
            "total_tools": len(self.tools),
            "initialized": self._initialized,
            "agent_name": self.config.agent_name,
            "model": self.config.openai_model,
            "mcp_server": self.config.mcp_server_url
        }
    
    def is_initialized(self) -> bool:
        """Check if the agent is initialized and ready.
        
        Returns:
            bool: True if agent is ready, False otherwise.
        """
        return self._initialized and self.agent is not None


class AgentManager:
    """High-level manager for agent operations."""
    
    def __init__(self, config: AppConfig):
        """Initialize the agent manager.
        
        Args:
            config: Application configuration.
        """
        self.config = config
        self.agent = AutoGenAgent(config)
    
    async def start(self) -> None:
        """Start the agent manager and initialize the agent.
        
        Raises:
            Exception: If agent initialization fails.
        """
        await self.agent.initialize()
    
    async def process_message(self, message: str) -> ChatResponse:
        """Process a user message through the agent.
        
        Args:
            message: User message to process.
            
        Returns:
            ChatResponse: The agent's response.
        """
        if not message or not message.strip():
            return ChatResponse(
                content="",
                error="Please enter a message.",
                success=False
            )
        
        return await self.agent.chat(message.strip())
    
    async def reset_conversation(self) -> bool:
        """Reset the agent's conversation state.
        
        Returns:
            bool: True if reset was successful, False otherwise.
        """
        return await self.agent.reset()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent.
        
        Returns:
            Dict containing status information.
        """
        return {
            "ready": self.agent.is_initialized(),
            "tools_info": self.agent.get_tools_info(),
            "config": {
                "model": self.config.openai_model,
                "agent_name": self.config.agent_name,
                "mcp_server": self.config.mcp_server_url
            }
        }
