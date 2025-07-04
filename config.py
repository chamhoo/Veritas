"""
Loads configurations from the .env file and makes them available to the application.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Configuration class to hold all application settings from environment variables.
    """
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    RETRIEVAL_FREQUENCY = int(os.getenv("RETRIEVAL_FREQUENCY_SECONDS", 900))

    # Basic validation
    if not all([DISCORD_BOT_TOKEN, OPENAI_API_KEY, ENCRYPTION_KEY]):
        raise ValueError("One or more required environment variables are missing.")

# Instantiate the config
config = Config()