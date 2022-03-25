import discord
from discord.ext import commands, tasks
import os

import asyncio
import aiohttp

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


activity = discord.Activity(name='the world burn :)', type=discord.ActivityType.watching)
intents = discord.Intents.all()
class PrestigiousBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

bot = PrestigiousBot(command_prefix=commands.when_mentioned_or("pr "), activity=activity, intents=intents)
bot.remove_command("help")
bot.starttime = datetime.datetime.utcnow()
bot.accent = 0xf7fa2f
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help", description="", color=bot.accent)
    embed.add_field(name="pr help", value="Shows this message", inline=False)
    await ctx.send(embed=embed)    

async def main():
    async with bot:
        await bot.start(os.getenv('TOKEN'))

asyncio.run(main())