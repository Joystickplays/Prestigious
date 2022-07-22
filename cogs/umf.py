import random
import traceback
from typing import Literal
import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio

class UserMadeForms(commands.Cog, app_commands.Group, name="umf"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
  
    # table forms
    # column - fname VARCHAR(100)
    # column - gid BIGINT
    # column - refid INT
    # column - ownid BIGINT
    # column - private BOOL
    # column - guildonly BOOL
    # column - maxtaken INT
    # CREATE TABLE forms (fname VARCHAR(100), gid BIGINT, refid INT, ownid BIGINT, private BOOL, guildonly BOOL, maxtaken INT);

    # table forminputs
    # column - refid INT
    # column - tlabel VARCHAR(128)
    # column - ttype SMALLINT
    # column - required BOOL
    # column - placeholder VARCHAR(128)
    # column - tdefault VARCHAR(128)
    # CREATE TABLE forminputs (refid INT, tlabel VARCHAR(128), ttype SMALLINT, required BOOL, placeholder VARCHAR(128), tdefault VARCHAR(128));
    
    # table bannedformers
    # column - uid BIGINT
    # column - reason VARCHAR(1000)
    # CREATE TABLE bannedformers (uid BIGINT, reason VARCHAR(1000));

    # table umfsettings
    # column - gid BIGINT
    # column - allowcreations BOOL
    # column - restrictguildonly BOOL
    # column - takingforms BOOL
    # CREATE TABLE umfsettings (gid BIGINT, allowcreations BOOL, restrictguildonly BOOL, takingforms BOOL);

    @app_commands.command(description="About UMF (or User-made forms).")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(title="User-made forms", description="User-made forms are forms that you can make yourself.\nThe forms are like Google forms. Anyone can take it if they have the referral and the results will get sent to you. Get started with /umf new", colour=interaction.client.accent)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(description="Create a new form.")
    async def new(self, interaction: discord.Interaction):
        banned = await interaction.client.db.fetchrow("SELECT * FROM bannedformers WHERE uid = $1", interaction.user.id)
        if banned:
            embed = discord.Embed(title="You are banned from making forms.", description=f"You're banned from creating or using forms by a Topstigious staff member.\nReason: `{banned['reason']}`\nAppeal the ban if this is a false ban.", colour=interaction.client.error)
            await interaction.response.send_message(embed=embed)
            return
        settings = await interaction.client.db.fetchrow("SELECT * FROM umfsettings WHERE gid = $1", interaction.guild.id)
        if settings:
            if not settings['allowcreations'] and not interaction.user.guild_permissions.manage_guild:
                embed = discord.Embed(title="Creations of forms is disabled", description="This server has disabled creation of new forms. You are still able to take existing forms if this server allows you to.", colour=interaction.client.error)
                await interaction.response.send_message(embed=embed)
                return

        class NewForm(ui.Modal, title="Name of the form"):
            formtitle = ui.TextInput(label="Name of the form", placeholder="Enter the name of the form", max_length=100)

            async def on_submit(self, interaction: discord.Interaction):
                formtitle = self.formtitle.value

                while True:
                    refid = random.randint(100000000, 999999999)
                    exists = await interaction.client.db.fetchrow("SELECT refid FROM forms WHERE refid = $1", refid)
                    if not exists:
                        break
                
                await interaction.client.db.execute("INSERT INTO forms (fname, refid, ownid) VALUES ($1, $2, $3)", formtitle, refid, interaction.user.id)
                await interaction.response.send_message(embed=discord.Embed(title="Form created", description=f"Form ({formtitle}) has been created with Referral ID of ({refid}).\nUse /umf newinput to add inputs to the form.", colour=interaction.client.accent))

        await interaction.response.send_modal(NewForm())

    @app_commands.command(description="Add an input to a form.")
    @app_commands.describe(
        refid = "The referral ID of the form.",
        label = "The label of the input.",
        inputtype = "The type of the input.",
        required = "Whether the input is required or not.",
        placeholder = "The placeholder of the input, if any.",
        default = "The default value of the input, if any."
    )
    async def newinput(self, interaction: discord.Interaction, refid: int, label: str, inputtype: Literal["Short", "Paragraph"], required: bool, placeholder: str = "", default: str = ""):
        await interaction.response.defer()
        form = await interaction.client.db.fetchrow("SELECT * FROM forms WHERE refid = $1", refid)
        if not form:
            embed = discord.Embed(title="Form not found.", description=f"Form with referral ID of ({refid}) was not found.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return
        
        if form['ownid'] != interaction.user.id:
            embed = discord.Embed(title="You don't own this.", description=f"Form with referral ID of ({refid}) does not belong to you.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
        
        inputs = await interaction.client.db.fetch("SELECT * FROM forminputs WHERE refid = $1", refid)
        if len(inputs) >= 5:
            embed = discord.Embed(title="Too many inputs.", description=f"Form with referral ID of ({refid}) already has 5 inputs.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return
        if len(label) >= 45 or len(placeholder) >= 45 or len(default) >= 45:
            embed = discord.Embed(title="Too long.", description=f"Label, placeholder, or default must be less than 45 characters.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return

        if inputtype == "Short":
            inputtype = 1
        elif inputtype == "Paragraph":
            inputtype = 2

        await interaction.client.db.execute("INSERT INTO forminputs (refid, ilabel, ttype, required, placeholder, tdefault) VALUES ($1, $2, $3, $4, $5, $6)", refid, label, inputtype, required, placeholder, default)
        await interaction.followup.send(embed=discord.Embed(title="Input added", description=f"Input ({label}) has been added to form ({form['fname']}).", colour=interaction.client.accent), ephemeral=True)
        
    @app_commands.command(description="Take a form.")
    @app_commands.describe(
        refid = "The referral ID of the form."
    )
    async def take(self, interaction: discord.Interaction, refid: int):
        await interaction.response.defer()
        form = await interaction.client.db.fetchrow("SELECT * FROM forms WHERE refid = $1", refid)

        banned = await interaction.client.db.fetchrow("SELECT uid FROM bannedformers WHERE uid = $1", interaction.user.id)
        if banned:
            embed = discord.Embed(title="You are banned from taking forms.", description=f"You're banned from taking forms by a Topstigious staff member.\nReason: `{banned['reason']}`\nAppeal the ban if this is a false ban.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return
        settings = await interaction.client.db.fetchrow("SELECT * FROM umfsettings WHERE gid = $1", interaction.guild.id)
        if settings:
            if not settings['takingforms'] and not interaction.user.guild_permissions.manage_guild:
                embed = discord.Embed(title="Takings of forms is disabled", description="This server has disabled taking of forms. Contact a server moderator to enable it back.", colour=interaction.client.error)
                await interaction.followup.send(embed=embed)
                return
            elif form["gid"] != interaction.guild.id and settings["restrictguildonly"] and not interaction.user.guild_permissions.manage_guild:
                embed = discord.Embed(title="Out of server.", description="This server has restricted taking of forms to forms from this server only.", colour=interaction.client.error)
                await interaction.followup.send(embed=embed)
                return

        form = await interaction.client.db.fetchrow("SELECT * FROM forms WHERE refid = $1", refid)
        if not form:
            embed = discord.Embed(title="Form not found.", description=f"Form with referral ID of ({refid}) was not found.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return
        
        inputs = await interaction.client.db.fetch("SELECT * FROM forminputs WHERE refid = $1", refid)
        if not inputs:
            embed = discord.Embed(title="No inputs.", description=f"Form with referral ID of ({refid}) has no inputs.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)

        class TakeForm(ui.Modal, title=f"{form['fname']}"):
            def __init__(self, inputs: list, form):
                self.form = form
                self.inputs = inputs
                super().__init__()

                for input in inputs:
                    self.add_item(ui.TextInput(label=input['ilabel'], placeholder=input['placeholder'], default=input['tdefault'], style=discord.TextStyle.short if input['ttype'] == 1 else discord.TextStyle.paragraph, required=input['required']))

            async def on_submit(self, interaction: discord.Interaction):
                inputs = self.inputs
                values = []
                for input in self.children:
                    values.append(input.value)

                ownid = form["ownid"]
                owneruser = await interaction.client.fetch_user(ownid)
                if not owneruser:
                    embed = discord.Embed(title="Owner not found.", description=f"The owner of form ({form['fname']}) could not be found.", colour=interaction.client.error)
                    await interaction.response.send_message(embed=embed)
                    return
                embed = discord.Embed(title=f"{interaction.user.name} taken your form {form['fname']}", description=f"{interaction.user.name}#{interaction.user.discriminator} has taken your form {form['fname']}.", colour=interaction.client.accent)
                i = 0
                for value in values:
                    embed.add_field(name=inputs[i]['ilabel'], value=value)
                    i += 1
                await owneruser.send(embed=embed)
                await interaction.response.send_message(embed=discord.Embed(title="Form taken", description=f"Form ({form['fname']}) has been taken and submitted. Thank you for filling the form!", colour=interaction.client.accent), ephemeral=True)

            async def on_error(self, interaction: discord.Interaction):
                embed = discord.Embed(title="Something went wrong.", description="Thank you for filling the form! Unfortunately, the form errored out and was not submitted.", colour=interaction.client.error)
                await interaction.response.send_message(embed=embed)

        class TakeFormView(ui.View):
            def __init__(self, form, member: discord.Member):
                self.form = form
                self.member = member

                super().__init__()

            @discord.ui.button(label="Take form", style=discord.ButtonStyle.primary)
            async def take(self, interaction: discord.Interaction, button: discord.Button):
                if interaction.user != self.member:
                    embed = discord.Embed(title="You can't take this form.", description=f"You can't take {self.member.mention}'s form.", colour=interaction.client.error)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                await interaction.response.send_modal(TakeForm(inputs, self.form))
        
        disabledview = TakeFormView(form, interaction.user)
        for button in disabledview.children:
            button.disabled = True
        owneruser = await interaction.client.fetch_user(form["ownid"])
        if not owneruser:
            embed = discord.Embed(title="Owner not found.", description=f"The owner of form ({form['fname']}) could not be found.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return
        msg = await interaction.followup.send(embed=discord.Embed(title=f"You are about to take the {form['fname']} form.", description=f"You're about to take a user-made form. This form is **made by {owneruser.name}#{owneruser.discriminator}** for others to take. Do not insert sensitive credentials to this form!\n\n**YOU HAVE BEEN WARNED.**\n**THIS FORM IS NOT AFFILIATED WITH DISCORD OR TOPSTIGIOUS.**", colour=interaction.client.accent), view=disabledview)
        await asyncio.sleep(3)
        await msg.edit(view=TakeFormView(form, interaction.user))

    @app_commands.command(description="Adjust UMF settings for your server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction):
        rawsettings = await interaction.client.db.fetchrow("SELECT * FROM umfsettings WHERE gid = $1", interaction.guild.id)
        if not rawsettings:
            settings = {
                "gid": interaction.guild.id,
                "allowcreations": True,
                "restrictguildonly": False,
                "takingforms": True
            }
            await interaction.client.db.execute("INSERT INTO umfsettings VALUES ($1, $2, $3, $4)", *settings.values())
        else:
            settings = {
                "gid": rawsettings["gid"],
                "allowcreations": rawsettings["allowcreations"],
                "restrictguildonly": rawsettings["restrictguildonly"],
                "takingforms": rawsettings["takingforms"]
            }

        class Settings(ui.View):
            def __init__(self, options):
                super().__init__()
                self.options = options
                self.allowcreations.style = discord.ButtonStyle.green if self.options["allowcreations"] else discord.ButtonStyle.secondary
                self.restrictguildonly.style = discord.ButtonStyle.green if self.options["restrictguildonly"] else discord.ButtonStyle.secondary
                self.takingforms.style = discord.ButtonStyle.green if self.options["takingforms"] else discord.ButtonStyle.secondary

            @discord.ui.button(label="Allow creations")
            async def allowcreations(self, interaction: discord.Interaction, button: discord.Button):
                self.options["allowcreations"] = not self.options["allowcreations"]
                button.style = discord.ButtonStyle.green if self.options["allowcreations"] else discord.ButtonStyle.gray
                await interaction.response.edit_message(view=self)

            @discord.ui.button(label="Restrict forms from guild only")
            async def restrictguildonly(self, interaction: discord.Interaction, button: discord.Button):
                self.options["restrictguildonly"] = not self.options["restrictguildonly"]
                button.style = discord.ButtonStyle.green if self.options["restrictguildonly"] else discord.ButtonStyle.gray
                await interaction.response.edit_message(view=self)

            @discord.ui.button(label="Allow taking forms")
            async def takingforms(self, interaction: discord.Interaction, button: discord.Button):
                self.options["takingforms"] = not self.options["takingforms"]
                button.style = discord.ButtonStyle.green if self.options["takingforms"] else discord.ButtonStyle.gray
                await interaction.response.edit_message(view=self)

            @discord.ui.button(label="Apply", style=discord.ButtonStyle.primary)
            async def apply(self, interaction: discord.Interaction, button: discord.Button):
                del self.options["gid"]
                await interaction.client.db.execute("UPDATE umfsettings SET allowcreations = $1, restrictguildonly = $2, takingforms = $3 WHERE gid = $4", *self.options.values(), interaction.guild.id)
                for button in self.children:
                    button.disabled = True
                await interaction.response.edit_message(embed=discord.Embed(title="Settings applied", description="Settings applied successfully.", colour=interaction.client.accent), view=self)

        await interaction.response.send_message(embed=discord.Embed(title="UMF Settings", description="These settings are only limited to your servers.\nTo enable/disable an option, click on their button.", colour=self.bot.accent), view=Settings(settings), ephemeral=True)

    @app_commands.command(description="Delete a form.")
    @app_commands.describe(refid="The referral ID of the form to delete.")
    async def delete(self, interaction: discord.Interaction, refid: int):
        form = await interaction.client.db.fetchrow("SELECT * FROM forms WHERE refid = $1", refid)
        if not form:
            embed = discord.Embed(title="Form not found.", description=f"Form with referral ID {refid} could not be found.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
        
        if form["gid"] == interaction.guild.id and interaction.user.guild_permissions.manage_guild:
            await interaction.client.db.execute("DELETE FROM forms WHERE refid = $1", refid)
            await interaction.client.db.execute("DELETE FROM forminputs WHERE refid = $1", refid)
            embed = discord.Embed(title="Form deleted.", description=f"Form with referral ID {refid} has been deleted.", colour=interaction.client.accent)
            await interaction.response.send_message(embed=embed)
            return
        elif form["ownid"] == interaction.user.id:
            await interaction.client.db.execute("DELETE FROM forms WHERE refid = $1", refid)
            await interaction.client.db.execute("DELETE FROM forminputs WHERE refid = $1", refid)
            embed = discord.Embed(title="Form deleted.", description=f"Form with referral ID {refid} has been deleted.", colour=interaction.client.accent)
            await interaction.response.send_message(embed=embed)
            return

        embed = discord.Embed(title="Permission denied.", description=f"You do not have permission to delete this form.", colour=interaction.client.error)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="View all your forms.")
    async def forms(self, interaction: discord.Interaction):
        forms = await interaction.client.db.fetch("SELECT * FROM forms WHERE ownid = $1", interaction.user.id)
        if not forms:
            embed = discord.Embed(title="No forms found.", description="You do not have any forms.", colour=interaction.client.warning)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="Your forms.", description="Here are your forms.", colour=interaction.client.accent)
        for ind, form in enumerate(forms):
            if ind < 23:
                embed.add_field(name=f"{form['fname']}", value=f"Referral ID: {form['refid']}")
            else:
                strbuild = ""
                for moreform in forms[ind:]:
                    strbuild += f"{moreform['fname']}: {moreform['refid']}\n"
                embed.add_field(name=f"And {len(forms) - ind} more forms...", value=strbuild, inline=False)
                break

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="Modify a form's settings.")
    @app_commands.describe(refid="The referral ID of the form to modify.")
    async def fsettings(self, interaction: discord.Interaction, refid: int):
        form = await interaction.client.db.fetchrow("SELECT * FROM forms WHERE refid = $1", refid)
        if not form:
            embed = discord.Embed(title="Form not found.", description=f"Form with referral ID {refid} could not be found.", colour=interaction.client.error)
            await interaction.followup.send(embed=embed)
            return
            
        if form["ownid"] != interaction.user.id:
            embed = discord.Embed(title="Permission denied.", description=f"You do not have permission to modify this form.", colour=interaction.client.error)
            await interaction.response.send_message(embed=embed)
            return

       # way too lazy

    @app_commands.command(description="View all the forms created in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def serverforms(self, interaction: discord.Interaction):
        forms = await interaction.client.db.fetch("SELECT * FROM forms WHERE gid = $1", interaction.guild.id)
        if not forms:
            embed = discord.Embed(title="No forms found.", description="There are no forms in this server.", colour=interaction.client.warning)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(title="Server forms.", description="Here are the forms created in this server.", colour=interaction.client.accent)
        for ind, form in enumerate(forms):
            if ind < 23:
                embed.add_field(name=f"{form['fname']}", value=f"Referral ID: {form['refid']}")
            else:
                strbuild = ""
                for moreform in forms[ind:]:
                    strbuild += f"{moreform['fname']}: {moreform['refid']}\n"
                embed.add_field(name=f"And {len(forms) - ind} more forms...", value=strbuild, inline=False)
                break


        await interaction.response.send_message(embed=embed, ephemeral=True)

    

async def setup(bot: commands.Bot):
    if bot.runmode == "p":
        await bot.add_cog(UserMadeForms(bot))
    else:
        await bot.add_cog(UserMadeForms(bot), guilds=[discord.Object(id=956522017983725588)])