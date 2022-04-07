
import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import random

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(description="Ban a member.")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(member="The member to ban.", reason="The reason for the ban.", notifymember="Whether or not to notify the member.")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, notifymember: bool = True):
        if interaction.user.top_role.position < member.top_role.position:
            await interaction.message.channel.send(f"{interaction.user.mention}, You cannot ban a member that is higher than you.", ephemeral=True)
            return

        await member.ban(reason=reason)
        if notifymember:
            await member.send(f"You have been banned from {interaction.message.guild.name} for {reason}")
        
        await interaction.message.channel.send(f"{interaction.user.mention}, You have banned {member.mention}.", ephemeral=True)

    @app_commands.command(description="Kick a member.")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(member="The member to kick.", reason="The reason for the kick.", notifymember="Whether or not to notify the member.")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, notifymember: bool = True):
        if interaction.user.top_role.position < member.top_role.position:
            await interaction.message.channel.send(f"{interaction.user.mention}, You cannot kick a member that is higher than you.", ephemeral=True)
            return

        await member.kick(reason=reason)
        if notifymember:
            await member.send(f"You have been kicked from {interaction.message.guild.name} for {reason}")
        
        await interaction.message.channel.send(f"{interaction.user.mention}, You have kicked {member.mention}.", ephemeral=True)
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))