import traceback
import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import hashlib


class InputPasswordV(ui.View):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter password", style=discord.ButtonStyle.primary, custom_id="enterpass")
    async def enterpass(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.send_modal(InputPasswordM(self.guild, interaction.channel))

class InputPasswordM(ui.Modal, title="Enter password"):
    def __init__(self, guild: discord.Guild, channel: discord.TextChannel):
        self.guild = guild
        self.channel = channel
        super().__init__()

    passw = ui.TextInput(label="Enter the password to gain access.")

    async def on_submit(self, interaction: discord.Interaction):
        def __init__(self, channel: discord.TextChannel):
            self.channel = channel
            super().__init__()

        getpass = await interaction.client.db.fetchrow("SELECT * FROM ppcs WHERE cid = $1", self.channel.category.id)
        try:
            if getpass["hashedpass"] == hashlib.sha256(self.passw.value.encode()).hexdigest():
                category = interaction.client.get_channel(getpass["cid"])
                if not category:
                    try:
                        category = await interaction.client.fetch_channel(getpass["cid"])
                    except:
                        await interaction.response.send_message(embed=discord.Embed(title="Not found", description="The category was not found. Please contact the server owner.", color=interaction.client.error), ephemeral=True)
                        return

                await interaction.response.defer()
                await category.set_permissions(interaction.user, read_messages=True)
                for channel in category.channels:
                    await channel.set_permissions(interaction.user, read_messages=True)
                await self.channel.set_permissions(interaction.user, read_messages=False)
            else:
                await interaction.response.send_message(embed=discord.Embed(title="Incorrect password", description="The password you entered was incorrect.", color=interaction.client.error), ephemeral=True)
                return
        except Exception as e:
            await interaction.response.send_message(embed=discord.Embed(title="Something went wrong", description="Sorry, something went wrong while processing your request!", color=interaction.client.error), ephemeral=True)
            traceback.print_exception(type(e), e, e.__traceback__)

class PasswordPC(commands.Cog, app_commands.Group, name="ppc"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    # table ppcs
    # column gid BIGINT
    # column cid BIGINT
    # column hashedpass TEXT
    # column messageid BIGINT
    # CREATE TABLE ppcs (gid BIGINT, cid BIGINT, hashedpass TEXT, messageid BIGINT);

    @commands.Cog.listener('on_raw_message_delete')
    async def ormd(self, payload: discord.RawMessageDeleteEvent):
        for entry in self.bot.ppcs:
            if entry["messageid"] == payload.message_id:
                category = self.bot.get_channel(entry["cid"])
                if not category:
                    try:
                        category = await self.bot.fetch_channel(entry["cid"])
                    except:
                        return

                await category.edit(overwrites={})
                for channel in category.channels:
                    await channel.edit(overwrites={})
                channel = discord.utils.get(category.text_channels, name="get-access")
                if channel:
                    await channel.delete()
                await self.bot.db.execute("DELETE FROM ppcs WHERE cid = $1", category.id)
                self.bot.ppcs.remove(entry)
                return
        
        self.bot.ppcs = await self.bot.db.fetch("SELECT * FROM ppcs")
        for entry in self.bot.ppcs:
            if entry["messageid"] == payload.message_id:
                category = self.bot.get_channel(entry["cid"])
                if not category:
                    try:
                        category = await self.bot.fetch_channel(entry["cid"])
                    except:
                        return

                await category.edit(overwrites={})
                for channel in category.channels:
                    await channel.edit(overwrites={})
                channel = discord.utils.get(category.text_channels, name="get-access")
                if channel:
                    await channel.delete()
                await self.bot.db.execute("DELETE FROM ppcs WHERE cid = $1", category.id)
                self.bot.ppcs.remove(entry)
                return


    @app_commands.command(description="About PPC (or Password-protected categories.).")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Password-protected categories", description="Password-protected categories are self-explanatory. They protect categories using passwords, and the passwords are guranteed to be very secure. To get started, run /ppc new", colour=interaction.client.accent)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="Create a new password-protected category.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def new(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        lookup = await interaction.client.db.fetchrow("SELECT * FROM ppcs WHERE cid = $1", category.id)
        if lookup:
            await interaction.response.send_message(embed=discord.Embed(title="Already protected", description="This category is already protected with a password, delete the protection first by /ppc delete", color=interaction.client.error), ephemeral=True)
            return

        class PassModal(ui.Modal, title="Set a password"):
            def __init__(self, category: discord.CategoryChannel):
                self.category = category
                super().__init__()

            passinput = ui.TextInput(label="Password to use for the category", placeholder="We recommend using 6-15 char passwords.")

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer(thinking=True, ephemeral=True)
                hashed = hashlib.sha256(self.passinput.value.encode()).hexdigest()
                getacc = await self.category.create_text_channel("get-access")
                
                await self.category.set_permissions(interaction.guild.default_role, read_messages=False)
                await getacc.set_permissions(interaction.guild.default_role, read_messages=True)
                await getacc.edit(topic=f"Enter the password to gain access to this category.\n\nAutomatically created and powered by Topstigious")
                
                msg = await getacc.send(embed=discord.Embed(title="Password-protected category", description="This category has been password-protected, and you will need to input the correct password to gain access. Click the button below to input the password.", color=interaction.client.warning), view=InputPasswordV(interaction.guild))
                
                await interaction.client.db.execute("INSERT INTO ppcs (gid, cid, hashedpass, messageid) VALUES ($1, $2, $3, $4)", interaction.guild.id, self.category.id, hashed, msg.id)
                await interaction.followup.send(embed=discord.Embed(title="Category protected", description="The category has been protected with a password.", color=interaction.client.success))
                
        await interaction.response.send_modal(PassModal(category))
    
    @app_commands.command(description="Delete a password-protected category.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        await interaction.response.defer()
        lookup = await interaction.client.db.fetchrow("SELECT * FROM ppcs WHERE cid = $1", category.id)
        if not lookup:
            await interaction.followup.send(embed=discord.Embed(title="Not protected", description="This category is not password-protected.", color=interaction.client.error), ephemeral=True)
            return

        category = interaction.client.get_channel(lookup["cid"])
        if not category:
            try:
                category = await interaction.client.fetch_channel(lookup["cid"])
            except:
                await interaction.followup.send(embed=discord.Embed(title="Not found", description="The category was not found. Please contact the server owner.", color=interaction.client.error), ephemeral=True)
                return

        await category.edit(overwrites={})
        for channel in category.channels:
            await channel.edit(overwrites={})
        channel = discord.utils.get(category.text_channels, name="get-access")
        if channel:
            await channel.delete()
        await interaction.client.db.execute("DELETE FROM ppcs WHERE cid = $1", category.id)
        
        await interaction.followup.send(embed=discord.Embed(title="Category unprotected", description="The category has been unprotected. You may safely remove the entry channel, if any.", color=interaction.client.success), ephemeral=True)


async def setup(bot: commands.Bot):
    if bot.runmode == "p":
        await bot.add_cog(PasswordPC(bot))
    else:
        await bot.add_cog(PasswordPC(bot), guilds=[discord.Object(id=956522017983725588)])