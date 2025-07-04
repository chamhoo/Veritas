"""
Utility functions for the bot, such as embed creation and error handling.
"""

import discord

def create_embed(title: str, description: str, color=discord.Color.blue()) -> discord.Embed:
    """Helper function to create a styled Discord embed."""
    return discord.Embed(title=title, description=description, color=color)

def create_item_embed(item: dict) -> discord.Embed:
    """Creates a styled embed for a retrieved information item."""
    title = f"[{item['source']}] {item['title']}"
    # Truncate title if it's too long for Discord's embed limits
    if len(title) > 256:
        title = title[:253] + "..."

    embed = discord.Embed(
        title=title,
        url=item['link'],
        description=item['snippet'],
        color=discord.Color.green()
    )
    embed.set_footer(text="React with 👍 or 👎 to provide feedback.")
    return embed