"""Agent logic for the AutoGen Chat Application.

This module contains the agent initialization, management, and interaction logic
separated from the UI components.
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, ModelClientStreamingChunkEvent
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import FunctionExecutionResult, FunctionExecutionResultMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import (
    StreamableHttpServerParams,
    # mcp_server_tools,
    McpWorkbench
)

from config import AppConfig, load_prompt_by_name

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """Response from a chat interaction."""
    content: str
    error: Optional[str] = None
    success: bool = True
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    intermediate_steps: Optional[List[Dict[str, Any]]] = None


class AutoGenAgent:
    """Manages the AutoGen agent and its interactions."""
    
    def __init__(self, config: AppConfig):
        """Initialize the AutoGen agent.
        
        Args:
            config: Application configuration.
        """
        self.config = config
        self.agent: Optional[AssistantAgent] = None
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
            server_params = StreamableHttpServerParams(
                url=self.config.mcp_server_url,
            )
            
            # Create OpenAI model client
            model = OpenAIChatCompletionClient(
                model=self.config.openai_model,
                api_key=self.config.openai_api_key,
                parallel_tool_calls=self.config.parallel_tool_calls
            )
            async with McpWorkbench(server_params) as mcp:
            # Create the assistant agent
                self.agent = AssistantAgent(
                    name=self.config.agent_name,
                    model_client=model,
                    workbench=mcp,
                    system_message=self.config.agent_system_message,
                    reflect_on_tool_use=True,
                    max_tool_iterations=self.config.max_tool_iterations,
                    model_client_stream=True
                )
            
            self._initialized = True
            logger.info("Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            self._initialized = False
            raise Exception(f"Agent initialization failed: {str(e)}")
    
    async def chat_stream(self, message: str):
        """Process a chat message and yield intermediate responses in real-time.
        
        Args:
            message: User message to process.
            
        Yields:
            ChatResponse: Intermediate responses including tool calls and thinking steps.
        """
        if not self._initialized or not self.agent:
            yield ChatResponse(
                content="",
                error="Agent not initialized. Please restart the application.",
                success=False
            )
            return
        
        try:
            logger.info(f"Processing message with streaming: {message[:100]}...")

            # Use the agent's streaming API so events are available immediately
            reply: str = ""
            accumulated_text: str = ""
            last_emitted_text: str = ""
            async for event in self.agent.run_stream(task=message):
                # Normalize event(s) to a list of messages
                events = event if isinstance(event, list) else [event]

                tool_calls = []
                tool_results = []
                intermediate_steps = []

                for msg in events:
                    # Token chunks from the model client (if enabled)
                    if isinstance(msg, ModelClientStreamingChunkEvent) and getattr(msg, 'source', None) == self.agent.name:
                        try:
                            chunk = str(getattr(msg, 'content', ''))
                        except Exception:
                            chunk = ""
                        if chunk:
                            accumulated_text += chunk
                        # Continue to next message to avoid misclassifying chunk as intermediate
                        continue
                    # Direct FunctionCall object
                    if isinstance(msg, FunctionCall):
                        pretty_args = None
                        try:
                            pretty_args = json.dumps(json.loads(msg.arguments), indent=2, ensure_ascii=False)
                        except Exception:
                            pretty_args = str(msg.arguments)
                        tool_calls.append({
                            "name": msg.name,
                            "content": f"**Tool:** {msg.name}\n\n**Arguments:**\n```json\n{pretty_args}\n```",
                            "type": "tool_call"
                        })
                    # Messages whose content is a list that may include FunctionCall-like items
                    elif hasattr(msg, 'content') and isinstance(getattr(msg, 'content'), list):
                        for item in msg.content:
                            if isinstance(item, FunctionCall) or (hasattr(item, 'name') and hasattr(item, 'arguments')):
                                name = getattr(item, 'name', 'unknown')
                                args_val = getattr(item, 'arguments', '')
                                try:
                                    pretty_args = json.dumps(json.loads(args_val), indent=2, ensure_ascii=False)
                                except Exception:
                                    pretty_args = str(args_val)
                                tool_calls.append({
                                    "name": name,
                                    "content": f"**Tool:** {name}\n\n**Arguments:**\n```json\n{pretty_args}\n```",
                                    "type": "tool_call"
                                })
                            # Detect FunctionExecutionResult-like items
                            elif isinstance(item, FunctionExecutionResult) or (
                                hasattr(item, 'name') and hasattr(item, 'content') and hasattr(item, 'is_error')
                            ):
                                name = getattr(item, 'name', 'unknown')
                                content_val = getattr(item, 'content', '')
                                is_error = bool(getattr(item, 'is_error', False))
                                tool_results.append({
                                    "name": name,
                                    "content": str(content_val),
                                    "is_error": is_error,
                                    "type": "tool_result"
                                })
                    # Direct FunctionExecutionResult or wrapper message
                    elif isinstance(msg, FunctionExecutionResult):
                        tool_results.append({
                            "name": msg.name,
                            "content": str(msg.content),
                            "is_error": bool(msg.is_error),
                            "type": "tool_result"
                        })
                    elif isinstance(msg, FunctionExecutionResultMessage) and isinstance(getattr(msg, 'content', None), list):
                        for item in msg.content:
                            if isinstance(item, FunctionExecutionResult) or (
                                hasattr(item, 'name') and hasattr(item, 'content')
                            ):
                                tool_results.append({
                                    "name": getattr(item, 'name', 'unknown'),
                                    "content": str(getattr(item, 'content', '')),
                                    "is_error": bool(getattr(item, 'is_error', False)),
                                    "type": "tool_result"
                                })
                    
                    # Other messages: treat as intermediate or assistant text
                    if hasattr(msg, 'source') and hasattr(msg, 'content'):
                        content_str = str(msg.content)
                        if (msg.source != self.config.agent_name and msg.source != 'user'):
                            intermediate_steps.append({
                                "source": msg.source,
                                "content": content_str,
                                "type": "intermediate"
                            })
                        if isinstance(msg, TextMessage) and msg.source == self.agent.name:
                            reply = str(msg.content)

                # Yield intermediate updates immediately
                if tool_calls or tool_results or intermediate_steps:
                    yield ChatResponse(
                        content="",
                        tool_calls=tool_calls if tool_calls else None,
                        tool_results=tool_results if tool_results else None,
                        intermediate_steps=intermediate_steps if intermediate_steps else None
                    )

                # Stream assistant text progressively when updated
                current_text = accumulated_text or reply
                if current_text and current_text != last_emitted_text:
                    last_emitted_text = current_text
                    yield ChatResponse(content=current_text)

            # After the stream ends, yield final content only if none was streamed
            if last_emitted_text == "":
                final_text = accumulated_text or reply or "I'm sorry, I couldn't process your request."
                yield ChatResponse(content=final_text)
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            yield ChatResponse(
                content="",
                error=error_msg,
                success=False
            )

    # Removed non-streaming chat method in favor of streaming-only flow
    
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
        """Get information about the agent configuration.
        
        Returns:
            Dict containing agent information.
        """
        return {
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
    
    # Removed non-streaming process_message in favor of streaming-only flow
    
    async def process_message_stream(self, message: str):
        """Process a user message through the agent with streaming.
        
        Args:
            message: User message to process.
            
        Yields:
            ChatResponse: Streaming responses including intermediate steps.
        """
        if not message or not message.strip():
            yield ChatResponse(
                content="",
                error="Please enter a message.",
                success=False
            )
            return
        
        async for response in self.agent.chat_stream(message.strip()):
            yield response
    
    async def update_model_and_prompt(self, model: Optional[str], prompt_name: Optional[str]) -> bool:
        """Update runtime model and system prompt, reinitializing the agent.
        
        Args:
            model: New model name (must be in available list) or None to keep current.
            prompt_name: New prompt base filename (without extension) or None to keep current.
        
        Returns:
            True if update succeeded and agent reinitialized, else False.
        """
        try:
            new_model = self.config.openai_model
            new_prompt_name = self.config.agent_system_prompt_name
            # Validate and apply model
            if model and model != new_model:
                if self.config.available_models and model not in self.config.available_models:
                    logger.warning(f"Requested model '{model}' is not in available_models")
                    return False
                new_model = model
            # Validate and apply prompt
            if prompt_name and prompt_name != new_prompt_name:
                if self.config.available_prompts and prompt_name not in self.config.available_prompts:
                    logger.warning(f"Requested prompt '{prompt_name}' is not in available_prompts")
                    return False
                new_prompt_name = prompt_name

            # If no effective change, nothing to do
            if new_model == self.config.openai_model and new_prompt_name == self.config.agent_system_prompt_name:
                return True

            # Mutate config
            self.config.openai_model = new_model
            self.config.agent_system_prompt_name = new_prompt_name
            # Always reload the system message from name to ensure freshness
            self.config.agent_system_message = load_prompt_by_name(new_prompt_name)

            # Recreate agent with updated config
            new_agent = AutoGenAgent(self.config)
            await new_agent.initialize()
            self.agent = new_agent
            return True
        except Exception as e:
            logger.error(f"Failed to update model/prompt: {str(e)}")
            return False
    
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
            "agent_info": self.agent.get_tools_info(),
            "config": {
                "model": self.config.openai_model,
                "agent_name": self.config.agent_name,
                "mcp_server": self.config.mcp_server_url,
                "prompt_name": getattr(self.config, "agent_system_prompt_name", "")
            }
        }
