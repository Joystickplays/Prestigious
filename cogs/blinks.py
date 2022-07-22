import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import random

class ButtonLinks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(description="Create a message")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(member="The member to ban.", reason="The reason for the ban.", notifymember="Whether or not to notify the member.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, notifymember: bool = True):
        if interaction.user.top_role.position < member.top_role.position:
            await interaction.response.send_message(f"You cannot ban a member that is higher than you.", ephemeral=True)
            return

        await member.ban(reason=reason)
        if notifymember:
            await member.send(f"You have been banned from {interaction.guild.name} for {reason}")
        
        await interaction.response.send_message(f"You have banned {member.mention}.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ButtonLinks(bot))