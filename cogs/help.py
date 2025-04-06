import discord
from discord.ext import commands
from discord import ui
import logging

# Configure logging
logger = logging.getLogger('discord_bot.help')

class HelpView(ui.View):
    """Interactive view for the help command with category buttons."""
    
    def __init__(self, help_command, timeout=60):
        super().__init__(timeout=timeout)
        self.help_command = help_command
        self.ctx = help_command.context
        self.bot = help_command.context.bot
        self.current_page = "main"
    
    async def on_timeout(self):
        """Disable all buttons when the view times out."""
        for item in self.children:
            item.disabled = True
        
        try:
            await self.message.edit(view=self)
        except:
            pass
    
    @ui.button(label="Fun", style=discord.ButtonStyle.primary, emoji="🎮")
    async def fun_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show fun commands."""
        await interaction.response.defer()
        embed = await self.help_command.create_category_embed("Fun")
        self.current_page = "fun"
        await self.message.edit(embed=embed, view=self)
    
    @ui.button(label="Games", style=discord.ButtonStyle.primary, emoji="🎲")
    async def games_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show games commands."""
        await interaction.response.defer()
        embed = await self.help_command.create_category_embed("Games")
        self.current_page = "games"
        await self.message.edit(embed=embed, view=self)
    
    @ui.button(label="Music", style=discord.ButtonStyle.primary, emoji="🎵")
    async def music_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show music commands."""
        await interaction.response.defer()
        embed = await self.help_command.create_category_embed("Music")
        self.current_page = "music"
        await self.message.edit(embed=embed, view=self)
    
    @ui.button(label="Economy", style=discord.ButtonStyle.primary, emoji="💰")
    async def economy_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show economy commands."""
        await interaction.response.defer()
        embed = await self.help_command.create_category_embed("Economy")
        self.current_page = "economy"
        await self.message.edit(embed=embed, view=self)
    
    @ui.button(label="Moderation", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def moderation_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show moderation commands."""
        await interaction.response.defer()
        embed = await self.help_command.create_category_embed("Moderation")
        self.current_page = "moderation"
        await self.message.edit(embed=embed, view=self)
    
    @ui.button(label="Home", style=discord.ButtonStyle.success, emoji="🏠", row=1)
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        """Return to the main help page."""
        await interaction.response.defer()
        embed = await self.help_command.create_main_embed()
        self.current_page = "main"
        await self.message.edit(embed=embed, view=self)


class ModernHelpCommand(commands.HelpCommand):
    """A modern, interactive help command using embeds and buttons."""
    
    def __init__(self):
        super().__init__(
            command_attrs={
                "help": "Shows the interactive help menu",
                "brief": "Shows help"
            }
        )
    
    async def create_main_embed(self):
        """Create the main help embed with an overview of all categories."""
        embed = discord.Embed(
            title="📚 Bot Help",
            description="Welcome to the interactive help menu! Click the buttons below to navigate through command categories.",
            color=discord.Color.blurple()
        )
        
        # Add command count
        total_commands = 0
        for command in await self.filter_commands(self.context.bot.commands, sort=True):
            if command.hidden or command.name == "admin":
                continue
            total_commands += 1
        embed.add_field(name="Command Count", value=f"{total_commands} commands", inline=True)
        
        # Add bot info
        embed.add_field(name="Prefix", value=f"`{self.context.clean_prefix}`", inline=True)
        embed.add_field(name="Bot Version", value="1.0.0", inline=True)
        
        # Categories
        categories_text = (
            "🎮 **Fun** - Entertainment commands\n"
            "🎲 **Games** - Interactive games\n"
            "🔢 **Counting** - Number counting game\n"
            "🎁 **Giveaways** - Create and manage giveaways\n"
            "📢 **Announcements** - Server announcements\n"
            "🎵 **Music** - Music playback commands\n"
            "🛡️ **Moderation** - Server moderation\n"
            "💰 **Economy** - Server economy system\n"
            "✨ **Self-Roles** - Self-assignable roles"
        )
        
        # Add admin section for administrators only
        if self.context.author.guild_permissions.administrator:
            categories_text += "\n⚙️ **Admin** - Type `!admin` to see admin commands"
        
        embed.add_field(
            name="Categories",
            value=categories_text,
            inline=False
        )
        
        # Footer
        embed.set_footer(text=f"Type {self.context.clean_prefix}help <command> for more info on a command")
        
        return embed
    
    async def filter_commands(self, commands, *, sort=False):
        """Filter out commands based on checks and cooldowns."""
        # Get the original filtered commands
        filtered = await super().filter_commands(commands, sort=sort)
        
        # Hide admin-only commands from users without admin permissions
        if not self.context.author.guild_permissions.administrator:
            filtered = [
                cmd for cmd in filtered 
                if not (cmd.name in ["admin", "seteconomychannel", "removeeconomychannel", "addcoins", 
                                    "removecoins", "setcoins", "giveall", "setmusicchannel", 
                                    "removemusicchannel", "gstart", "gend", "greroll", "announce",
                                    "poll", "msg", "countsetup", "countreset", "countstrict", 
                                    "countfail", "selfroles"])
            ]
        
        return filtered
    
    async def create_category_embed(self, category_name):
        """Create an embed for a specific command category."""
        cog = self.context.bot.get_cog(category_name)
        if cog is None:
            return await self.create_main_embed()
        
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            description=cog.__doc__ or "No description provided",
            color=discord.Color.blurple()
        )
        
        # Add the commands from this cog
        filtered = await self.filter_commands(cog.get_commands())
        if filtered:
            for command in filtered:
                value = command.brief or command.help or "No description"
                if len(value) > 70:
                    value = value[:67] + "..."
                
                embed.add_field(
                    name=f"{self.context.clean_prefix}{command.name}",
                    value=value,
                    inline=False
                )
        else:
            embed.add_field(name="No Commands", value="This category has no commands available to you")
        
        # Footer
        embed.set_footer(text=f"Type {self.context.clean_prefix}help <command> for more info on a command")
        
        return embed
    
    async def create_command_embed(self, command):
        """Create an embed for a specific command."""
        embed = discord.Embed(
            title=f"Command: {command.qualified_name}",
            description=command.help or "No description provided",
            color=discord.Color.blurple()
        )
        
        # Add usage info
        embed.add_field(
            name="Usage",
            value=f"`{self.context.clean_prefix}{command.qualified_name} {command.signature}`",
            inline=False
        )
        
        # Add aliases if any
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join([f"`{alias}`" for alias in command.aliases]),
                inline=False
            )
        
        # Add subcommands if this is a group
        if isinstance(command, commands.Group):
            subcommands = await self.filter_commands(command.commands)
            if subcommands:
                value = "\n".join([f"`{self.context.clean_prefix}{c.qualified_name}` - {c.brief or 'No description'}" for c in subcommands])
                embed.add_field(name="Subcommands", value=value, inline=False)
        
        # Footer
        embed.set_footer(text=f"Category: {command.cog_name or 'No Category'}")
        
        return embed
    
    async def send_bot_help(self, mapping):
        """Send the main help page."""
        embed = await self.create_main_embed()
        view = HelpView(self)
        view.message = await self.context.send(embed=embed, view=view)
    
    async def send_command_help(self, command):
        """Send help for a specific command."""
        embed = await self.create_command_embed(command)
        await self.context.send(embed=embed)
    
    async def send_group_help(self, group):
        """Send help for a command group."""
        embed = await self.create_command_embed(group)
        await self.context.send(embed=embed)
    
    async def send_cog_help(self, cog):
        """Send help for a specific cog/category."""
        embed = await self.create_category_embed(cog.qualified_name)
        view = HelpView(self)
        view.message = await self.context.send(embed=embed, view=view)
    
    async def send_error_message(self, error):
        """Send an error message."""
        embed = discord.Embed(
            title="Error",
            description=error,
            color=discord.Color.red()
        )
        await self.context.send(embed=embed)


async def setup(bot):
    """Add the Help cog to the bot."""
    bot.help_command = ModernHelpCommand()
    await bot.add_cog(commands.Cog("Help")) 