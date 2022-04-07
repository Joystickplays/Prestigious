
import discord
from discord import app_commands, ui
from discord.ext import commands
import os
import random

class Fun(commands.Cog, app_commands.Group, name="fun"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.benanswers = ["Yes?", "No.", "Hohoho!", "Eugh.", "*declines*"]
        super().__init__()

    # unoriginal idea.
    @app_commands.command(description="Ask Ben a question.")
    @app_commands.describe(question="The question to ask.")
    async def askben(self, interaction: discord.Interaction, question: str):
        embed = discord.Embed(description=random.choice(self.benanswers), color=self.bot.accent)
        embed.set_author(name="Ben", icon_url="https://static.wikia.nocookie.net/logopedia/images/c/ce/TalkingBenAppIcon%282011-2017%29.png/revision/latest/scale-to-width-down/512?cb=20170414163600")
        await interaction.response.send_message(embed=embed)

        

async def setup(bot: commands.Bot):
    if bot.runmode == "p":
        await bot.add_cog(Fun(bot))
    else:
        await bot.add_cog(Fun(bot), guilds=[discord.Object(id=956522017983725588)])