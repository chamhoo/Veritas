"""
Main entry point for the Discord bot instance.
Loads and initializes all bot extensions (cogs).
"""
import discord
from discord.ext import commands, tasks
import logging
from config import config
from src.data.database import get_all_active_requests
from src.langchain_logic.relevance_filter import is_content_relevant
from src.retrievers import rss_retriever, twitter_retriever
from src.bot.utils import create_item_embed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class VeritasBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent_item_links = set() # Simple in-memory cache to avoid sending duplicate links

    async def setup_hook(self):
        """A special method that is called when the bot logs in."""
        logger.info("Running setup hook...")
        # Load extensions (cogs)
        await self.load_extension("src.bot.cogs.onboarding")
        await self.load_extension("src.bot.cogs.request_management")
        logger.info("Cogs loaded successfully.")
        
        # Start background tasks
        self.information_retrieval_loop.start()
        logger.info("Background retrieval loop started.")

    async def on_ready(self):
        """Event triggered when the bot is ready and connected to Discord."""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info('------')
        
    @tasks.loop(seconds=config.RETRIEVAL_FREQUENCY)
    async def information_retrieval_loop(self):
        """The main background task that continuously fetches and filters information."""
        logger.info("Starting information retrieval cycle...")
        active_requests = await get_all_active_requests()
        
        if not active_requests:
            logger.info("No active requests found. Skipping cycle.")
            return

        for request in active_requests:
            logger.info(f"Processing request ID {request.id} for channel {request.discord_channel_id}")
            channel = self.get_channel(request.discord_channel_id)
            if not channel:
                logger.warning(f"Channel {request.discord_channel_id} not found for request ID {request.id}. Skipping.")
                continue

            # 1. Gather content from all retrievers
            all_content = []
            rss_items = await rss_retriever.fetch_rss_feeds(request.keywords)
            tweet_items = await twitter_retriever.search_tweets(request.keywords)
            all_content.extend(rss_items)
            all_content.extend(tweet_items)
            # Add other retrievers (e.g., web) here

            # 2. Filter and post relevant content
            for item in all_content:
                # Avoid sending the same link multiple times in a session
                if item['link'] in self.sent_item_links:
                    continue

                # Use LLM to check for relevance
                is_relevant = await is_content_relevant(
                    original_request=request.description,
                    content_title=item['title'],
                    content_snippet=item['snippet']
                )

                if is_relevant:
                    try:
                        embed = create_item_embed(item)
                        await channel.send(embed=embed)
                        self.sent_item_links.add(item['link'])
                        logger.info(f"Posted relevant item to channel {channel.id}: {item['title']}")
                    except discord.errors.Forbidden:
                        logger.error(f"Missing permissions to send message in channel {channel.id}")
                    except Exception as e:
                        logger.error(f"Failed to send message to channel {channel.id}: {e}")

    @information_retrieval_loop.before_loop
    async def before_retrieval_loop(self):
        """Ensures the bot is ready before the loop starts."""
        await self.wait_until_ready()