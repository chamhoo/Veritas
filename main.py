"""
Main entry point to start the entire application, initializing and running the Discord bot.
"""


import asyncio
import discord
from src.bot.bot import VeritasBot
from src.data.database import init_db
from config import config

async def main():
    """
    Main entry point for the application.
    Initializes the database and runs the Discord bot.
    """
    # 1. Initialize the database
    print("Initializing the database...")
    init_db()
    print("Database initialized successfully.")

    # 2. Set up bot intents
    intents = discord.Intents.default()
    intents.message_content = True  # Required for reading message content
    intents.members = True          # Required for tracking members (e.g., for DMs)
    intents.reactions = True        # Required for feedback

    # 3. Create and run the bot instance
    bot = VeritasBot(command_prefix='!', intents=intents)
    
    print("Starting Veritas Bot...")
    await bot.start(config.DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutting down.")
    except Exception as e:
        print(f"An error occurred: {e}")