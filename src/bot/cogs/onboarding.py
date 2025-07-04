"""
Handles secure user registration and credential management via direct messages.
"""

import discord
from discord.ext import commands
from src.bot.utils import create_embed

class OnboardingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup")
    async def setup(self, ctx: commands.Context):
        """
        Starts the secure onboarding process via Direct Messages.
        """
        try:
            # Create an embed to send in the public channel
            public_embed = create_embed(
                "Onboarding Started!",
                f"{ctx.author.mention}, I've sent you a Direct Message to securely set up your profile.",
                color=discord.Color.purple()
            )
            await ctx.send(embed=public_embed)

            # Create the initial DM embed
            dm_embed = create_embed(
                "Welcome to Veritas Setup!",
                "This is a secure channel to configure your settings.\n\n"
                "**Note:** This template uses global API keys from the bot's configuration. "
                "In a multi-user environment where users provide their own keys, "
                "the logic to collect, encrypt, and store them would go here."
            )
            
            await ctx.author.send(embed=dm_embed)
            
        except discord.errors.Forbidden:
            # This happens if the user has DMs disabled
            error_embed = create_embed(
                "Onboarding Failed",
                f"{ctx.author.mention}, I couldn't send you a Direct Message. "
                "Please enable DMs from server members in your Privacy & Safety settings.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")

async def setup(bot):
    await bot.add_cog(OnboardingCog(bot))