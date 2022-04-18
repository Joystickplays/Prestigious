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
    # column - name VARCHAR(100)
    # column - refid INT
    # column - ownid BIGINT
    # CREATE TABLE forms (fname VARCHAR(100), refid INT, ownid BIGINT);

    # table forminputs
    # column - refid INT
    # column - label VARCHAR(128)
    # column - type SMALLINT
    # column - required BOOL
    # column - placeholder VARCHAR(128)
    # column - default VARCHAR(128)
    # CREATE TABLE forminputs (refid INT, label VARCHAR(128), type SMALLINT, required BOOL, placeholder VARCHAR(128), default VARCHAR(128));
    
    # table bannedformers
    # column - uid BIGINT
    # column - reason VARCHAR(1000)
    # CREATE TABLE bannedformers (uid BIGINT, reason VARCHAR(1000));

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
                await interaction.response.send_message(embed=discord.Embed(title="Form created", description=f"Form ({formtitle}) has been created with Referral ID of ({refid}).\nUse /umf newinput to add inputs to the form.", colour=interaction.client.accent), ephemeral=True)

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
        banned = await interaction.client.db.fetchrow("SELECT uid FROM bannedformers WHERE uid = $1", interaction.user.id)
        if banned:
            embed = discord.Embed(title="You are banned from taking forms.", description=f"You're banned from taking forms by a Topstigious staff member.\nReason: `{banned['reason']}`\nAppeal the ban if this is a false ban.", colour=interaction.client.error)
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
                strbuild = ""
                i = 0
                for value in values:
                    strbuild += f"{inputs[i]['ilabel']}: {value}\n"
                    i += 1
                await owneruser.send(embed=discord.Embed(title=f"{interaction.user.name} taken your form {form['fname']}", description=f"{interaction.user.mention} has taken your form {form['fname']}.\n\n{strbuild}", colour=interaction.client.accent))
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
        

async def setup(bot: commands.Bot):
    if bot.runmode == "p":
        await bot.add_cog(UserMadeForms(bot))
    else:
        await bot.add_cog(UserMadeForms(bot), guilds=[discord.Object(id=956522017983725588)])