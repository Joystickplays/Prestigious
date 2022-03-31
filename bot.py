import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord import ui
import os

import asyncio
import aiohttp
import asyncpg

# from io import StringIO
import time
import random
import traceback
import sys
# import json
import warnings
import datetime
# from PIL import Image, ImageDraw, ImageFont, ImageOps

from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore", category=DeprecationWarning) 

class IRRoleButton(discord.ui.Button["InteractionRoles"]):
        def __init__(self, role: discord.Role):
            super().__init__(style=discord.ButtonStyle.primary, label=role.name, custom_id=str(role.id))
            # role = discord.utils.get(interaction.guild.roles, id=id)
            self.role = role
        
        async def callback(self, interaction: discord.Interaction):
            try:
                if not self.role in interaction.user.roles:
                    await interaction.user.add_roles(self.role)
                    embed = discord.Embed(title="Role added", description=f"You have been given the role {self.role.name}.", color=bot.success)
                else:
                    await interaction.user.remove_roles(self.role)
                    embed = discord.Embed(title="Role removed", description=f"You have been removed from the role {self.role.name}.", color=bot.success)
            except Exception as e:
                embed = discord.Embed(title="Something went wrong", description=f"Contact the server administrator.", color=bot.error)
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
class InteractionRoles(discord.ui.View):
    def __init__(self, guild: discord.Guild, irroles: list):
        super().__init__(timeout=None)

        for button in irroles:
            role = discord.utils.get(guild.roles, id=button["rid"])
            if role:
                self.add_item(IRRoleButton(role)) 

activity = discord.Activity(name='the world burn :)', type=discord.ActivityType.watching)
intents = discord.Intents.all()
class PersistentView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label='Green', style=discord.ButtonStyle.green, custom_id='persistent_view:green')
        async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message('This is green.', ephemeral=True)

class PrestigiousBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        pass

bot = PrestigiousBot(command_prefix=commands.when_mentioned_or("pr "), activity=activity, intents=intents)
apptree = bot.tree
bot.remove_command("help")
bot.starttime = datetime.datetime.utcnow()
bot.accent = 0x007bff # blue
bot.success = 0x28a745 # green
bot.error = 0xdc3545 # red
bot.warning = 0xffc107 # yellow
db_credentials = {
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'host': os.environ.get('DB_HOST'),
}
bot.db = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(**db_credentials))

async def addviews():
    await bot.wait_until_ready()
    lookup = await bot.db.fetch("SELECT * FROM irpanels")

    for panel in lookup:
        async with bot.db.acquire() as conn:
            rolelookup = await conn.fetch("SELECT * FROM irroles WHERE grid = $1", panel["grid"])
            guild = bot.get_guild(panel["gid"])
            bot.add_view(InteractionRoles(guild, rolelookup), message_id=panel['msgid'])



@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    # lookup = await bot.db.fetch("SELECT * FROM irpanels")

    # for panel in lookup:
    #     async with bot.db.acquire() as conn:
    #         rolelookup = await conn.fetch("SELECT * FROM irroles WHERE grid = $1", panel["grid"])
    #         print(panel["gid"])
    #         guild = bot.get_guild(panel["gid"])
    #         bot.add_view(InteractionRoles(guild, rolelookup), message_id=panel['msgid'])


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help", description="", color=bot.accent)
    embed.add_field(name="pr help", value="Shows this message", inline=False)
    await ctx.send(embed=embed)    

@bot.command()
async def sync(ctx):
    msg = await ctx.send("Syncing...")
    await apptree.sync(guild=discord.Object(id=ctx.guild.id))
    await msg.edit(content="Synced!", delete_after=5)

@bot.command()
async def addviewss(ctx):
    msg = await ctx.send("Adding...")
    conn = await bot.db.acquire()
    lookup = await conn.fetch("SELECT * FROM irpanels")

    for panel in lookup:
        conn2 = await bot.db.acquire()
        rolelookup = await conn2.fetch("SELECT * FROM irroles WHERE grid = $1", panel["grid"])
        print(panel["gid"])
        guild = bot.get_guild(panel["gid"])
        bot.add_view(InteractionRoles(guild, rolelookup), message_id=panel['msgid'])
    await msg.edit(content="Added!", delete_after=5)

@apptree.command(description="Determine a text's sentiment.", guild=discord.Object(id=956522017983725588))
@app_commands.describe(text="The text to analyze.")
async def sentiment(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    if len(text) > 255:
        await interaction.response.send_message(f"Text too long (Max 255 characters).")
        return
    async with aiohttp.ClientSession() as session:
        async with session.post("http://text-processing.com/api/sentiment/", data={"text": text}) as resp:
            data = await resp.json()

    def convert(label):
        if label == "pos":
            return "positive"
        elif label == "neg":
            return "negative"
        elif label == "neutral":
            return "neutral"
    
    embed = discord.Embed(title="Sentiment Analysis", description=f"The text `{text}` has been determined as: `{convert(data['label'])}`.", color=bot.accent)
    await interaction.followup.send(embed=embed)

@apptree.command(description="Views all IR groups for this server.", guild=discord.Object(id=956522017983725588))
async def irgroups(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(title="Missing permissions", description="You need the Manage Server permission to use this command.", color=bot.error)
        return await interaction.response.send_message(embed=embed)

    lookup = await bot.db.fetch("SELECT * FROM irgroups")
    if not lookup:
        embed = discord.Embed(title="No IR groups", description="There are no IR groups in this server.", color=bot.warning)
        return await interaction.response.send_message(embed=embed)

    embed = discord.Embed(title="IR groups", description="This shows the list of IR groups in your server. If none, create one using /newirgroup.", color=bot.accent)
    for row in lookup:
        irroles = await bot.db.fetch("SELECT * FROM irroles WHERE grid = $1", row['grid'])
        desc = "There is no IR roles for this group."
        if irroles:
            desc = f"There is {len(irroles)} IR roles for this group."

        embed.add_field(name=f"Group {row['gname']} ({row['grid']})", value=desc, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
@apptree.command(description="Creates a new IR group.", guild=discord.Object(id=956522017983725588))
@app_commands.describe(name="The name of the group.")
async def irnewgroup(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(title="Missing permissions", description="You need the Manage Server permission to use this command.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    while True:
        randomid = random.randint(111111, 999999)
        lookup = await bot.db.fetchrow("SELECT * FROM irgroups WHERE grid = $1", randomid)
        if not lookup:
            break

    lookup = await bot.db.fetchrow("SELECT * FROM irgroups WHERE gid = $1 AND gname = $2", interaction.guild.id, name)
    if lookup:
        embed = discord.Embed(title="IR group already exists", description="There is already an IR group with that name.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    await bot.db.execute("INSERT INTO irgroups (gid, gname, grid) VALUES ($1, $2, $3)", interaction.guild.id, name, randomid)
    embed = discord.Embed(title="IR group created", description=f"The IR group {name} has been created. Start adding roles by using /newir", color=bot.success)

    await interaction.followup.send(embed=embed, ephemeral=True)

@apptree.command(description="Deletes an IR group.", guild=discord.Object(id=956522017983725588))
@app_commands.describe(group="The ID of the group.")
async def irdelgroup(interaction: discord.Interaction, group: int):
    await interaction.response.defer
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(title="Missing permissions", description="You need the Manage Server permission to use this command.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    lookup = await bot.db.fetchrow("SELECT * FROM irgroups WHERE id = $1", group)
    if not lookup:
        embed = discord.Embed(title="IR group not found", description="There is no IR group with that ID.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    await bot.db.execute("DELETE FROM irgroups WHERE grid = $1", group)
    embed = discord.Embed(title="IR group deleted", description="The IR group has been deleted.", color=bot.success)

    await interaction.followup.send(embed=embed, ephemeral=True)

@apptree.command(description="Creates a new IR (Interaction role).", guild=discord.Object(id=956522017983725588))
@app_commands.describe(group="The ID of the group.", role="The role to be given.")
async def irnew(interaction: discord.Interaction, group: int, role: discord.Role):
    await interaction.response.defer()
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(title="Missing permissions", description="You need the Manage Server permission to use this command.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    lookup = await bot.db.fetch("SELECT * FROM irgroups WHERE grid = $1", group)
    if not lookup:
        embed = discord.Embed(title="IR group not found", description=f"An IR group with the ID `{group}` does not exist.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    lookup = await bot.db.fetch("SELECT * FROM irroles WHERE grid = $1 AND rid = $2", group, role.id)
    if lookup:
        embed = discord.Embed(title="IR role already exists", description=f"An IR role with the ID `{role.id}` already exists.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    await bot.db.execute("INSERT INTO irroles (grid, rid, gid) VALUES ($1, $2, $3)", group, role.id, interaction.guild.id)
    embed = discord.Embed(title="IR role created", description=f"The IR role {role.name} has been created.", color=bot.success)

    await interaction.followup.send(embed=embed, ephemeral=True)

@apptree.command(description="Deletes an IR.", guild=discord.Object(id=956522017983725588))
@app_commands.describe(group="The ID of the group.", role="The role to be removed.")
async def irdel(interaction: discord.Interaction, group: int, role: discord.Role):
    await interaction.response.defer()
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(title="Missing permissions", description="You need the Manage Server permission to use this command.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    lookup = await bot.db.fetch("SELECT * FROM irgroups WHERE grid = $1", group)
    if not lookup:
        embed = discord.Embed(title="IR group not found", description=f"An IR group with the ID `{group}` does not exist.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    lookup = await bot.db.fetch("SELECT * FROM irroles WHERE grid = $1 AND rid = $2", group, role.id)
    if not lookup:
        embed = discord.Embed(title="IR role not found", description=f"An IR role with the ID `{role.id}` does not exist.", color=bot.error)
        return await interaction.followup.send(embed=embed)

    await bot.db.execute("DELETE FROM irroles WHERE grid = $1 AND rid = $2", group, role.id)
    embed = discord.Embed(title="IR role deleted", description=f"The IR role {role.name} has been deleted.", color=bot.success)

    await interaction.followup.send(embed=embed, ephemeral=True)

@apptree.command(description="Lists all Interaction roles.", guild=discord.Object(id=956522017983725588))
async def irlist(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        embed = discord.Embed(title="Missing permissions", description="You need the Manage Server permission to use this command.", color=bot.error)
        return await interaction.response.send_message(embed=embed)

    lookup = await bot.db.fetch("SELECT * FROM irroles")
    if not lookup:
        embed = discord.Embed(title="No IR roles found", description="There are no IR roles in this server.", color=bot.warning)
        return await interaction.response.send_message(embed=embed)
    
    embed = discord.Embed(title="IR roles", description="", color=bot.success)
    for row in lookup:
        group = await bot.db.fetchrow("SELECT * FROM irgroups WHERE grid = $1", row["grid"])
        role = discord.utils.get(interaction.guild.roles, id=row["rid"])
        embed.add_field(name=f"{role.name} - {group['gname']}", value=f"This interaction role belongs to `{group['gname']}`.", inline=False)
    
@apptree.command(description="Opens a public IR panel.", guild=discord.Object(id=956522017983725588))
@app_commands.describe(group="The ID of the group to open.")
async def iropen(interaction: discord.Interaction, group: int):
    await interaction.response.defer()
    group = await bot.db.fetchrow("SELECT * FROM irgroups WHERE grid = $1", group)
    if not group:
        embed = discord.Embed(title="IR group not found", description=f"An IR group with the ID `{group}` does not exist.", color=bot.error)
        return await interaction.followup.send(embed=embed) 
    
    irroles = await bot.db.fetch("SELECT * FROM irroles WHERE grid = $1", group["grid"])
    msg = await interaction.channel.send(embed=discord.Embed(title=str(group['gname']), description="Press a button to get the corresponding role.", color=bot.accent), view=InteractionRoles(interaction.guild, irroles))
    await bot.db.execute("INSERT INTO irpanels (msgid, grid, gid) VALUES ($1, $2, $3)", msg.id, group["grid"], interaction.guild.id)
    await interaction.followup.send(embed=discord.Embed(title="IR panel opened", description=f"The IR panel for {group['gname']} has been opened. Feel free to delete this message.", color=bot.success))

# @apptree.command(description="Fills this server's form, if any.", guild=discord.Object(id=956522017983725588))
# async def serverform(interaction: discord.Interaction):
#     class Form(ui.Modal, title='If you are a nobody fill this!'):
#         name = ui.TextInput(label='Name')
#         answer = ui.TextInput(label='Answer', style=discord.TextStyle.paragraph)

#         async def on_submit(self, interaction: discord.Interaction):
#             await interaction.followup.edit_message(f'Thanks for your response, {self.name}!', ephemeral=True)

#     await interaction.response.send_modal(Form())
#     await interaction.response.send_message("The form is sent to you. If not, please contact the server owner.")

async def main():
    async with bot:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')

        bot.loop.create_task(addviews())        
        await bot.start(os.getenv('TOKEN'))
        
        
        

asyncio.get_event_loop().run_until_complete(main())