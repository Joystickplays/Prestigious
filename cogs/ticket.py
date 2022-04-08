import traceback
import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import random
import uuid
import sys

class CreateTicketModal(ui.Modal, title='Create ticket'):
    def __init__(self, category):
        self.category = category
        super().__init__()

    ticket = ui.TextInput(label="Reason for the ticket", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ticketchannel = await interaction.guild.create_text_channel(f"ticket-{random.randint(1, 100000)}", category=self.category, reason=self.ticket.value)
            await ticketchannel.set_permissions(interaction.user, read_messages=True)
            await interaction.response.send_message(f"Ticket has been created. Please visit {ticketchannel.mention}", ephemeral=True)
            class CloseTicket(discord.ui.View):
                def __init__(self):
                    super().__init__()
                    
                @discord.ui.button(label='Close ticket', style=discord.ButtonStyle.red)
                async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
                    try:
                        await ticketchannel.delete(reason="Ticket closed.")
                    except:
                        await interaction.response.send_message(f"Ticket could not be closed. Contact a server administrator.", ephemeral=True)
                        return
            await ticketchannel.send(embed=discord.Embed(title="Ticket", description=self.ticket.value, color=interaction.client.accent), view=CloseTicket())
        except Exception as e:
            await interaction.response.send_message(f"Ticket could not be created. Contact a server administrator.\n\n```{e}```", ephemeral=True)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            

class CreateTicketView(discord.ui.View):
    def __init__(self, category):
        super().__init__(timeout=None)
        self.category = category

    @discord.ui.button(label='Create ticket', style=discord.ButtonStyle.green, custom_id="createticket")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateTicketModal(self.category))

class Ticketing(commands.Cog, app_commands.Group, name="ticket"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
    
    # table ticketsettings
    # column gid bigint - guild id
    # column cid bigint - channel id
    # column caid bigint -  category id
    # CREATE TABLE ticketsettings (gid bigint, cid bigint, caid bigint);

    # table ticketpanels
    # column gid bigint - guild id
    # column mid bigint - message id
    # CREATE TABLE ticketpanels (gid bigint, mid bigint);

    @app_commands.command(description="Ticketing settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lookup = await self.bot.db.fetchrow("SELECT * FROM ticketsettings WHERE gid = $1", interaction.guild.id)
        if lookup is None:
            await interaction.followup.send(f"You have not set up ticketing settings yet. Please use `/ticket set` to set them up.", ephemeral=True)
            return
        
        embed = discord.Embed(title="Ticketing Settings", color=self.bot.accent)
        category = await interaction.guild.fetch_channel(lookup['caid'])
        channel = await interaction.guild.fetch_channel(lookup['cid'])
        embed.add_field(name="Channel", value=f"<#{lookup['cid']}>" if channel else "Not set.", inline=False)
        embed.add_field(name="Category", value=f"{category.name}" if category else "Not set.", inline=False)
        class SettingsModal(ui.Modal, title='Settings'):
            channel = ui.TextInput(label="Channel", max_length=100)
            category = ui.TextInput(label="Category", max_length=100)

            async def on_submit(self, interaction: discord.Interaction):
                getchannel = discord.utils.get(interaction.guild.channels, name=self.channel.value)
                getcategory = discord.utils.get(interaction.guild.categories, name=self.category.value)
                if getchannel is None or getcategory is None:
                    await interaction.response.send_message(f"One or more of the (category) channels you provided does not exist.", ephemeral=True)
                    return
                await interaction.client.db.execute("UPDATE ticketsettings SET cid = $1, caid = $2 WHERE gid = $3", getchannel.id, getcategory.id, interaction.guild.id)
                await interaction.response.send_message(f"Ticketing settings have been updated.", ephemeral=True)
                
        class ModSettings(discord.ui.View):
            def __init__(self, author: discord.Member):
                super().__init__()
                self.author = author
                
            @discord.ui.button(label='Modify settings', style=discord.ButtonStyle.green)
            async def modify(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.author.id:
                    await interaction.response.send_message(f"You cannot interact with this button.", ephemeral=True)
                    return
                await interaction.response.send_modal(SettingsModal())

        await interaction.followup.send(embed=embed, ephemeral=True, view=ModSettings(interaction.user))

    @app_commands.command(description="Set up ticketing settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to use for ticketing.", category="The category to use for ticketing.")
    async def set(self, interaction: discord.Interaction, channel: discord.TextChannel, category: discord.CategoryChannel):
        await self.bot.db.execute("INSERT INTO ticketsettings (gid, cid, caid) VALUES ($1, $2, $3)", interaction.guild.id, channel.id, category.id)
        await interaction.response.send_message(f"Ticketing settings have been set.", ephemeral=True)

    @app_commands.command(description="Open a ticket panel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lookup = await self.bot.db.fetchrow("SELECT * FROM ticketsettings WHERE gid = $1", interaction.guild.id)
        if lookup is None:
            await interaction.followup.send(f"You have not set up ticketing settings yet. Please use `/ticket set` to set them up.", ephemeral=True)
            return
        
        embed = discord.Embed(title="Get a ticket", description="Click on the button below to create a ticket.", color=self.bot.accent)
        category = await interaction.guild.fetch_channel(lookup["caid"])
        channel = await interaction.guild.fetch_channel(lookup["cid"])
        if category is None or channel is None:
            await interaction.followup.send(f"One or more of the (category) channels unexpectedly is inaccessible.", ephemeral=True)
            return
            
        msg = await channel.send(embed=embed, view=CreateTicketView(category))
        await self.bot.db.execute("INSERT INTO ticketpanels (gid, mid, cid) VALUES ($1, $2, $3)", interaction.guild.id, msg.id, category.id)
        await interaction.followup.send(f"Ticket panel has been created.")


async def setup(bot: commands.Bot):
    if bot.runmode == "p":
        await bot.add_cog(Ticketing(bot))
    else:
        await bot.add_cog(Ticketing(bot), guilds=[discord.Object(id=956522017983725588)])