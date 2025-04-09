# src/main.py
import os
import json
import logging
import sys
import traceback
from typing import Any
from dotenv import load_dotenv
from src.assistant.utils.menu_helpers import MenuSystem
from src.services.groq_api import GroqService
from src.config import load_config, Config
from src.tools.tools import Tools

# Configure logging to both file and console with DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def register_tools(groq_service: Any, tools: Any) -> None:
    logger.info("Registering tools...")
    try:
        groq_service.register_tool("search_history", tools.search_history)
        groq_service.register_tool("execute_command", tools.execute_command)
        groq_service.register_tool("provide_helpful_tips", tools.provide_helpful_tips)
        groq_service.register_tool("search_tavily", tools.search_tavily)
        logger.info("Tools registered successfully")
    except Exception as e:
        logger.error(f"Error registering tools: {e}")
        traceback.print_exc()
        raise

def main():
    try:
        logger.info("Starting application...")
        sys.stdout.write("Starting application...\n")
        sys.stdout.flush()

        logger.info("Loading environment variables...")
        sys.stdout.write("Loading environment variables...\n")
        sys.stdout.flush()
        
        load_dotenv()
        dotenv_path = os.path.abspath(".env")
        load_dotenv(dotenv_path=dotenv_path)
        
        logger.info("Environment variables loaded")
        sys.stdout.write("Environment variables loaded\n")
        sys.stdout.flush()

        logger.info("Loading configuration...")
        sys.stdout.write("Loading configuration...\n")
        sys.stdout.flush()
        
        config = load_config()
        config.load_system_prompts()
        
        logger.info("Configuration and system prompts loaded")
        sys.stdout.write("Configuration and system prompts loaded\n")
        sys.stdout.flush()

        logger.info("Initializing services...")
        sys.stdout.write("Initializing services...\n")
        sys.stdout.flush()
        
        groq_service = GroqService(config)
        tools = Tools(config, groq_service)
        register_tools(groq_service, tools)
        
        logger.info("Services initialized successfully")
        sys.stdout.write("Services initialized successfully\n")
        sys.stdout.flush()

        logger.info("Starting menu system...")
        sys.stdout.write("Starting menu system...\n")
        sys.stdout.flush()
        
        menu_system = MenuSystem(config, groq_service, tools)
        menu_system.run()
        
        logger.info("Menu system started")
        sys.stdout.write("Menu system started\n")
        sys.stdout.flush()

    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.stdout.write(f"Fatal error in main: {e}\n")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        return

if __name__ == "__main__":
    main()