import discord
from discord.ext import commands
import logging
from src.bot.utils import create_embed
from src.langchain_logic import keyword_extractor
from src.data import database
from src.langchain_logic.rag_system import add_feedback_to_rag
from src.data.database import get_request_by_channel_id

logger = logging.getLogger(__name__)

class RequestManagementCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="request")
    async def new_request(self, ctx: commands.Context, *, description: str):
        """
        Creates a new information request and a dedicated channel for it.
        Usage: !request <detailed description of the info you want>
        """
        if not description:
            await ctx.send("Please provide a description for your request. Usage: `!request <description>`")
            return

        try:
            # Acknowledge the request
            ack_embed = create_embed("Processing Your Request...",
                                     "I'm analyzing your request and setting up a dedicated channel.",
                                     color=discord.Color.orange())
            await ctx.send(embed=ack_embed)

            # 1. Get or create user in DB
            user = await database.get_or_create_user(ctx.author.id, str(ctx.author))

            # 2. Extract keywords using LangChain
            keywords = await keyword_extractor.extract_keywords(description)
            logger.info(f"Extracted keywords: '{keywords}' for request: '{description}'")

            # 3. Create a new Discord channel for the request
            category = discord.utils.get(ctx.guild.categories, name="Topics")
            if not category:
                category = await ctx.guild.create_category("Topics")
            
            # Sanitize channel name
            channel_name = f"topic-{keywords.split(',')[0].replace(' ', '-')[:50]}"
            
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            new_channel = await ctx.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Info request from {ctx.author.name}: {description}"
            )
            
            # 4. Store the request in the database
            await database.create_info_request(
                user_id=user.id,
                description=description,
                keywords=keywords,
                channel_id=new_channel.id
            )

            # 5. Notify the user
            success_embed = create_embed(
                "Channel Created!",
                f"I have created the channel {new_channel.mention} for your request about:\n> {description}",
                color=discord.Color.green()
            )
            await ctx.send(embed=success_embed)

            # Send a welcome message in the new channel
            initial_message_embed = create_embed(
                "Information Feed Started",
                f"**Request**: {description}\n**Keywords**: `{keywords}`\n\n"
                "I will now start searching for relevant information. "
                "Please use 👍 and 👎 reactions to give feedback on the results.",
            )
            await new_channel.send(embed=initial_message_embed)

        except Exception as e:
            logger.error(f"Failed to create new request: {e}", exc_info=True)
            await ctx.send(embed=create_embed("Error", f"An unexpected error occurred: {e}", color=discord.Color.red()))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Listens for reactions to process feedback for the RAG system.
        """
        # Ignore reactions from the bot itself
        if payload.user_id == self.bot.user.id:
            return

        # Check if the reaction is one we care about
        if str(payload.emoji) not in ["👍", "👎"]:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if not isinstance(channel, discord.TextChannel) or channel.category.name != "Topics":
                return # Not in a topic channel

            message = await channel.fetch_message(payload.message_id)
            # Ensure the message is from the bot and has an embed
            if message.author.id != self.bot.user.id or not message.embeds:
                return

            # Find the corresponding info request from the database
            request = await get_request_by_channel_id(channel.id)
            if not request:
                return
            
            is_relevant = True if str(payload.emoji) == "👍" else False
            content_snippet = message.embeds[0].description
            
            # Add this feedback to the RAG system for this request
            add_feedback_to_rag(
                request_id=request.id,
                content=content_snippet,
                is_relevant=is_relevant
            )

            user = self.bot.get_user(payload.user_id)
            logger.info(f"Feedback received from {user} in channel {channel.name}. Relevant: {is_relevant}")

            # Optional: Add a small confirmation message
            await channel.send(f"Thank you for your feedback, {user.mention}!", delete_after=5)

        except discord.NotFound:
            # Message or channel might have been deleted
            pass
        except Exception as e:
            logger.error(f"Error processing reaction feedback: {e}", exc_info=True)


async def setup(bot):
    await bot.add_cog(RequestManagementCog(bot))