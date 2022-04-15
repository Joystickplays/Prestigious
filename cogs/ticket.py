import traceback
import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import random
import uuid
import sys
from io import BytesIO

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

class ClosedTicketPanel(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel

    @discord.ui.button(label="Delete ticket", style=discord.ButtonStyle.grey)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.client.db.execute("DELETE FROM tickets WHERE cid = $1", self.channel.id)
        await self.channel.delete(reason="Ticket deleted.")

    # @discord.ui.button(label="Open ticket", style=discord.ButtonStyle.green)
    # async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     lookup = await interaction.client.db.fetchrow("SELECT * FROM tickets WHERE cid = $1", self.channel.id)
    #     member = discord.utils.get(interaction.guild.members, id=lookup["uid"])
    #     if not member:
    #         await interaction.response.send_message(f"The member is no longer accessible or left the server.", ephemeral=True)
    #         return
    #     await self.channel.edit(name=f"ticket-{self.channel.name.split('-')[1]}") 
    #     await interaction.client.db.execute("UPDATE tickets SET isopen = true WHERE cid = $1", self.channel.id)
    #     await interaction.response.send_message("The ticket has been re-opened.")
    #     await self.channel.set_permissions(member, read_messages=True)

class CloseTicket(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel

        
    @discord.ui.button(label='Close ticket', style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        lookup = await interaction.client.db.fetchrow("SELECT * FROM tickets WHERE cid = $1", self.channel.id)
        if lookup["isopen"] == False:
            await interaction.response.send_message(f"This ticket is already closed.", ephemeral=True)
            return
        try:
            overwrites = {}

            for key, overwrite in self.channel.overwrites.items():
                if not isinstance(key, discord.Member):
                    overwrites[key] = overwrite

            await self.channel.edit(name=f"closed-{self.channel.name.split('-')[1]}", overwrites=overwrites) 
            await interaction.client.db.execute("UPDATE tickets SET isopen = false WHERE cid = $1", self.channel.id)
            await interaction.response.send_message(embed=discord.Embed(title="Ticket closed.", description=f"The ticket has been closed.", colour=interaction.client.accent), view=ClosedTicketPanel(self.channel))
        except Exception as e:
            filler = None
            if str(e).endswith("Missing Permissions"):
                filler = "This may be caused by the bot not having the correct permissions to edit the channel. It will need Manage Channels."
            elif str(e).endswith("Missing Access"):
                filler = "This may be caused by the bot not being able to access the category where the tickets is supposed to be. Overwrite permissions for the bot."
            await interaction.response.send_message(f"Ticket could not be closed. Contact a server administrator.\n\n```{e}```\n{filler}", ephemeral=True)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            return

class CreateTicketModal(ui.Modal, title='Create ticket'):
    def __init__(self, category):
        self.category = category
        super().__init__()

    ticket = ui.TextInput(label="Reason for the ticket", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ticketchannel = await interaction.guild.create_text_channel(f"ticket-{random.randint(1, 100000)}", category=self.category, reason=self.ticket.value)
            await ticketchannel.set_permissions(interaction.user, read_messages=True)
            await interaction.client.db.execute("INSERT INTO tickets (gid, uid, cid, isopen) VALUES ($1, $2, $3, $4)", interaction.guild.id, interaction.user.id, ticketchannel.id, True)
            await interaction.response.send_message(f"Ticket has been created. Please visit {ticketchannel.mention}", ephemeral=True)
            
            await ticketchannel.send(embed=discord.Embed(title="Welcome to your ticket.", description=f"Welcome to your ticket, {interaction.user.mention}, support will be with you soon.\nTo close the ticket, click the button below.\n\n{self.ticket.value}", color=interaction.client.accent), view=CloseTicket(ticketchannel))
        except Exception as e:
            filler = None
            if str(e).endswith("Missing Permissions"):
                filler = "This may be caused by the bot not having the correct permissions to create a channel. It will need Manage Channels."
            elif str(e).endswith("Missing Access"):
                filler = "This may be caused by the bot not being able to access the category where the tickets is supposed to be. Overwrite permissions for the bot."
            await interaction.response.send_message(f"Ticket could not be created. Contact a server administrator.\n\n```{e}```\n{filler}", ephemeral=True)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            return
            

class CreateTicketView(discord.ui.View):
    def __init__(self, category):
        super().__init__(timeout=None)
        self.category = category

    @discord.ui.button(label='Create ticket', style=discord.ButtonStyle.green, custom_id="createticket")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        lookup = await interaction.client.db.fetchrow("SELECT * FROM tickets WHERE uid = $1 AND gid = $2 AND isopen = true", interaction.user.id, interaction.guild.id)
        if lookup:
            embed = discord.Embed(title="A ticket open", description=f"You already have a ticket open. Close the previous one first.", colour=interaction.client.error)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
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
            
        try:
            msg = await channel.send(embed=embed, view=CreateTicketView(category))
            await self.bot.db.execute("INSERT INTO ticketpanels (gid, mid, cid) VALUES ($1, $2, $3)", interaction.guild.id, msg.id, category.id)
            await interaction.followup.send(f"Ticket panel has been created.")
        except Exception as e:
            filler = None
            if str(e).endswith("Missing Permissions"):
                filler = "This may be caused by the bot not having the correct permissions to send messages to the channel. It will need Manage Channels."
            elif str(e).endswith("Missing Access"):
                filler = "This may be caused by the bot not being able to access the channels where the message is supposed to be. Overwrite permissions for the bot."
            await interaction.response.send_message(f"Message cannot be sent. Contact a server administrator.\n\n```{e}```\n{filler}", ephemeral=True)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


async def setup(bot: commands.Bot):
    if bot.runmode == "p":
        await bot.add_cog(Ticketing(bot))
    else:
        await bot.add_cog(Ticketing(bot), guilds=[discord.Object(id=956522017983725588)])