"""Main application file for the AutoGen Chat Application.

This module contains the Gradio web interface and main application logic.
"""

import asyncio
import logging
import sys
from typing import List, Tuple, Optional, Dict

import gradio as gr
from dotenv import load_dotenv

from config import load_config, AppConfig
from agent import AgentManager, ChatResponse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('chat_app.log')
    ]
)
logger = logging.getLogger(__name__)


class AutoGenChatApp:
    """Main chat application using Gradio interface."""
    
    def __init__(self, config: AppConfig):
        """Initialize the chat application.
        
        Args:
            config: Application configuration.
        """
        self.config = config
        self.agent_manager = AgentManager(config)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the application and agent.
        
        Raises:
            Exception: If initialization fails.
        """
        if self._initialized:
            return
            
        try:
            logger.info("Initializing AutoGen Chat Application...")
            await self.agent_manager.start()
            self._initialized = True
            logger.info("Application initialized successfully")
        except Exception as e:
            logger.error(f"Application initialization failed: {str(e)}")
            raise
    
    async def chat_handler(self, message: str, history: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
        """Handle chat messages from the Gradio interface.
        
        Args:
            message: User message.
            history: Chat history (list of message dictionaries with 'role' and 'content' keys).
            
        Returns:
            Tuple of (empty_string, updated_history) - empty string clears input, updated history for chat display.
        """
        if not self._initialized:
            error_response = "❌ Application not initialized. Please restart the application."
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": error_response})
            return "", history
        
        try:
            # Process the message through the agent
            response = await self.agent_manager.process_message(message)
            
            if response.success:
                reply = response.content
            else:
                reply = f"❌ Error: {response.error or 'Unknown error occurred'}"
            
            # Add to chat history using the new message format
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": reply})
            logger.info(f"Chat exchange completed - User: {message[:50]}... | Agent: {reply[:50]}...")
            
        except Exception as e:
            error_reply = f"❌ Unexpected error: {str(e)}"
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": error_reply})
            logger.error(f"Unexpected error in chat handler: {str(e)}")
        
        return "", history
    
    async def reset_handler(self) -> gr.update:
        """Handle conversation reset requests.
        
        Returns:
            Gradio update to clear the chat history.
        """
        if not self._initialized:
            logger.warning("Cannot reset: Application not initialized")
            return gr.update(value=[])
        
        try:
            success = await self.agent_manager.reset_conversation()
            if success:
                logger.info("Conversation reset successfully")
            else:
                logger.warning("Conversation reset failed")
            return gr.update(value=[])
        except Exception as e:
            logger.error(f"Error during reset: {str(e)}")
            return gr.update(value=[])
    
    def get_status_info(self) -> str:
        """Get current application status information.
        
        Returns:
            String containing status information.
        """
        if not self._initialized:
            return "❌ Application not initialized"
        
        try:
            status = self.agent_manager.get_status()
            if status["ready"]:
                model = status["config"]["model"]
                agent_name = status["config"]["agent_name"]
                return f"✅ Ready | Agent: {agent_name} | Model: {model} | MCP: Connected"
            else:
                return "⚠️ Agent not ready"
        except Exception as e:
            return f"❌ Status error: {str(e)}"
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface.
        
        Returns:
            Gradio Blocks interface.
        """
        # Define custom CSS for better styling
        css = """
        .gradio-container {
            max-width: 1000px !important;
            margin: auto !important;
        }
        .chat-container {
            height: 600px !important;
        }
        .status-text {
            font-family: monospace;
            font-size: 0.9em;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        """
        
        with gr.Blocks(
            title=self.config.app_title,
            theme=gr.themes.Soft(),
            css=css
        ) as interface:
            # Header
            gr.Markdown(
                f"# {self.config.app_title}\n"
                f"Powered by AutoGen agents with MCP tools integration"
            )
            
            # Status display
            status_display = gr.Textbox(
                value=self.get_status_info(),
                label="Status",
                interactive=False,
                elem_classes=["status-text"]
            )
            
            # Main chat interface
            with gr.Row():
                with gr.Column(scale=1):
                    chatbot = gr.Chatbot(
                        value=[],
                        label="Chat History",
                        height=self.config.chat_height,
                        show_label=True,
                        elem_classes=["chat-container"],
                        type="messages"
                    )
                    
                    with gr.Row():
                        message_input = gr.Textbox(
                            placeholder="Type your message and press Enter...",
                            label="Message",
                            scale=4,
                            lines=1,
                            max_lines=5
                        )
                        
                    with gr.Row():
                        reset_btn = gr.Button(
                            "🔄 Reset Conversation",
                            variant="secondary",
                            scale=1
                        )
                        refresh_status_btn = gr.Button(
                            "🔄 Refresh Status",
                            variant="secondary",
                            scale=1
                        )
            
            # Information section
            with gr.Accordion("ℹ️ Information", open=False):
                gr.Markdown(f"""
                ### Configuration
                - **Model**: {self.config.openai_model}
                - **Agent**: {self.config.agent_name}
                - **MCP Server**: {self.config.mcp_server_url}
                
                ### Features
                - 🤖 AI-powered responses using AutoGen agents
                - 🔧 Extended functionality through MCP tools
                - 🔄 Conversation reset capability
                - 💬 Real-time chat interface
                
                ### Usage Tips
                - Use natural language to interact with the AI
                - The agent has access to various tools for enhanced functionality
                - Reset the conversation to start fresh at any time
                - Check the status indicator for system health
                """)
            
            # Event handlers
            message_input.submit(
                fn=self.chat_handler,
                inputs=[message_input, chatbot],
                outputs=[message_input, chatbot],
                queue=True
            )
            
            reset_btn.click(
                fn=self.reset_handler,
                outputs=chatbot,
                queue=True
            )
            
            refresh_status_btn.click(
                fn=lambda: self.get_status_info(),
                outputs=status_display,
                queue=False
            )
            
            # Initialize status on load
            interface.load(
                fn=lambda: self.get_status_info(),
                outputs=status_display
            )
        
        return interface
    
    def launch(self) -> None:
        """Launch the Gradio interface.
        
        This method creates and launches the web interface after ensuring
        the application is properly initialized.
        """
        try:
            # Create the interface
            interface = self.create_interface()
            
            # Configure launch parameters
            launch_kwargs = {
                "server_name": self.config.gradio_host,
                "server_port": self.config.gradio_port,
                "share": self.config.gradio_share,
                "inbrowser": True,
                "quiet": False
            }
            
            logger.info(f"Launching interface at http://{self.config.gradio_host}:{self.config.gradio_port}")
            
            # Launch the interface
            interface.queue().launch(**launch_kwargs)
            
        except Exception as e:
            logger.error(f"Failed to launch interface: {str(e)}")
            raise


async def main():
    """Main application entry point."""
    try:
        # Load and validate configuration (environment variables are loaded in config.py)
        logger.info("Loading configuration...")
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Create and initialize the application
        app = AutoGenChatApp(config)
        await app.initialize()
        
        # Launch the interface
        app.launch()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        print("\nPlease check:")
        print("1. Your .env file contains OPENAI_API_KEY")
        print("2. The MCP server is running")
        print("3. All dependencies are installed")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
