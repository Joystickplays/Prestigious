
from code import interact
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
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, notifymember: bool = True):
        if interaction.user.top_role.position < member.top_role.position:
            await interaction.response.send_message(f"You cannot ban a member that is higher than you.", ephemeral=True)
            return

        await member.ban(reason=reason)
        if notifymember:
            await member.send(f"You have been banned from {interaction.guild.name} for {reason}")
        
        await interaction.response.send_message(f"You have banned {member.mention}.", ephemeral=True)

    @app_commands.command(description="Kick a member.")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(member="The member to kick.", reason="The reason for the kick.", notifymember="Whether or not to notify the member.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, notifymember: bool = True):
        if interaction.user.top_role.position < member.top_role.position:
            await interaction.response.send_message(f"You cannot kick a member that is higher than you.", ephemeral=True)
            return

        await member.kick(reason=reason)
        if notifymember:
            await member.send(f"You have been kicked from {interaction.guild.name} for {reason}")
        
        await interaction.response.send_message(f"You have kicked {member.mention}.", ephemeral=True)

    @app_commands.command(description="Lists all warns (of a member, if specificed.).")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(member="The member to list warns for.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warns(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()
        if member is None:
            lookup = await self.bot.db.fetch("SELECT * FROM warns WHERE gid = $1", interaction.guild.id)
        else:
            lookup = await self.bot.db.fetch("SELECT * FROM warns WHERE gid = $1 AND uid = $2", interaction.guild.id, member.id)

        if len(lookup) == 0:
            if member:
                embed = discord.Embed(title=f"No warns", description=f"{member.name} has no warnings in this server.", color=self.bot.warning)
                await interaction.followup.send(embed=embed)
                return
            else:
                embed = discord.Embed(title="No warns", description="No members in this server has a warning.", color=self.bot.warning)
                await interaction.followup.send(embed=embed)
                return

        desc = ""
        for warn in lookup:
            warnedmember = await interaction.guild.fetch_member(warn["uid"])
            warner = await interaction.guild.fetch_member(warn["warnerid"])
            desc += f"**{warn['wid']}**: \nWarned member: {warnedmember.name if warnedmember else 'Unknown'}\nWarned by: {warner.name if warner else 'Unknown'}\nReason: {warn['reason']}\n\n"
        embed = discord.Embed(title=f"Warns for {member.name if member is not None else 'this server'}", description=desc, color=self.bot.accent)
        await interaction.followup.send(embed=embed)

    @app_commands.command(description="Warn a member.")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(member="The member to warn.", reason="The reason for the warn.", notifymember="Whether or not to notify the member.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Not specificed", notifymember: bool = True):
        await interaction.response.defer()
        if interaction.user.top_role.position < member.top_role.position:
            embed = discord.Embed(title="Low hierachy", description=f"You cannot warn a member that is higher than you.", color=self.bot.error)
            await interaction.followup.send(embed=embed)
            return

        while True:
            wid = random.randint(111111, 999999)
            temp = await self.bot.db.fetch("SELECT * FROM warns WHERE wid = $1", wid)
            if not temp:
                break

        await self.bot.db.execute("INSERT INTO warns (wid, uid, gid, warnerid, reason) VALUES ($1, $2, $3, $4, $5)", wid, member.id, interaction.guild.id, interaction.user.id, reason)
        if notifymember:
            embed = discord.Embed(title=f"You have been warned in {interaction.guild.name}", description=f"You have been warned in {interaction.guild.name} for {reason}", color=self.bot.accent)
            await member.send(embed=embed)
        
        embed = discord.Embed(title=f"You have warned {member.name}", description=f"You have warned {member.mention if notifymember else member.name} for {reason}", color=self.bot.success)
        await interaction.followup.send(embed=embed)

    @app_commands.command(description="Inspect a warn entry.")
    # @app_commands.guilds(discord.Object(id=956522017983725588))
    @app_commands.describe(wid="The warn entry to inspect.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warninspect(self, interaction: discord.Interaction, wid: int):
        await interaction.response.defer()
        warn = await self.bot.db.fetch("SELECT * FROM warns WHERE gid = $1 AND wid = $2", interaction.guild.id, wid)
        if not warn:
            embed = discord.Embed(title="No warn", description=f"No warn with id {wid} found.", color=self.bot.error)
            await interaction.followup.send(embed=embed)
            return

        warnedmember = await interaction.guild.fetch_member(warn[0]["uid"])
        warner = await interaction.guild.fetch_member(warn[0]["warnerid"])
        embed = discord.Embed(title=f"Warn {wid}", description=f"Warned member: {warnedmember.name if warnedmember else 'Unknown'}\nWarned by: {warner.name if warner else 'Unknown'}\nReason: {warn[0]['reason']}", color=self.bot.accent)
        class WarnActions(discord.ui.View):
            def __init__(self, wid: int, author: discord.Member):
                super().__init__()
                self.wid = wid
                self.author = author
                self.deleted = False

            @discord.ui.button(label='Delete warn', style=discord.ButtonStyle.grey)
            async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not interaction.user == self.author:
                    embed = discord.Embed(title="No access", description="You cannot interact with this button.", color=interaction.client.error)
                    await interaction.response.send_message(embed = embed)

                if not self.deleted:
                    await interaction.client.db.execute("DELETE FROM warns WHERE wid = $1 AND gid = $2", self.wid, interaction.guild.id)
                    embed = discord.Embed(title=f"Warn {self.wid} deleted", description=f"This warn entry has been deleted.", color=interaction.client.success)
                    await interaction.response.send_message(embed = embed)
                    self.deleted = True
                else:
                    embed = discord.Embed(title="Already deleted", description="This warn entry has already been deleted.", color=interaction.client.error)
                    await interaction.response.send_message(embed=embed)

        await interaction.followup.send(embed=embed, view=WarnActions(wid, interaction.user))

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))