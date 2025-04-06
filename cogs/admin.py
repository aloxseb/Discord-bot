import discord
import logging
from discord.ext import commands

# Configure logging
logger = logging.getLogger('discord_bot.admin')

class Admin(commands.Cog):
    """Administrative commands for server management."""
    
    def __init__(self, bot):
        self.bot = bot

    # Command check to ensure only administrators can use these commands
    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator
    
    @commands.command(name="admin")
    async def admin_help(self, ctx):
        """Display all administrative commands.
        
        Usage: !admin
        Requires Administrator permission.
        """
        embed = discord.Embed(
            title="⚙️ Admin Commands",
            description="Here are all the administrative commands available:",
            color=discord.Color.dark_red()
        )
        
        # Economy admin commands
        embed.add_field(
            name="💰 Economy Admin",
            value=(
                "`!seteconomychannel [#channel]` - Set economy channel\n"
                "`!removeeconomychannel` - Remove economy channel restriction\n"
                "`!addcoins <user> <amount>` - Add coins to a user\n"
                "`!removecoins <user> <amount>` - Remove coins from a user\n"
                "`!setcoins <user> <amount>` - Set a user's coin balance\n"
                "`!giveall <amount>` - Give coins to all members"
            ),
            inline=False
        )
        
        # Music admin commands
        embed.add_field(
            name="🎵 Music Admin",
            value=(
                "`!setmusicchannel [#channel]` - Set music channel\n"
                "`!removemusicchannel` - Remove music channel restriction"
            ),
            inline=False
        )
        
        # Giveaway admin commands
        embed.add_field(
            name="🎁 Giveaway Admin",
            value=(
                "`!gstart <time> <winners> <prize>` - Start a giveaway\n"
                "`!gend <message_id>` - End a giveaway early\n"
                "`!greroll <message_id>` - Reroll winners"
            ),
            inline=False
        )
        
        # Announcements admin commands
        embed.add_field(
            name="📢 Announcements Admin",
            value=(
                "`!announce #channel <message>` - Send announcement\n"
                "`!poll #channel <question> | <options>` - Create a poll\n"
                "`!msg #channel <message>` - Send a regular message"
            ),
            inline=False
        )
        
        # Counting game admin commands
        embed.add_field(
            name="🔢 Counting Admin",
            value=(
                "`!countsetup #channel` - Set up counting channel\n"
                "`!countreset` - Reset the count\n"
                "`!countstrict [on/off]` - Toggle strict mode\n"
                "`!countfail [message/restart/continue]` - Set fail behavior"
            ),
            inline=False
        )
        
        # Self-roles admin commands
        embed.add_field(
            name="✨ Self-Roles Admin",
            value=(
                "`!selfroles create <title> | <description>` - Create self-role message\n"
                "`!selfroles add <message_id> <emoji> <role>` - Add role\n"
                "`!selfroles remove <message_id> <emoji>` - Remove role\n"
                "`!selfroles list` - List messages\n"
                "`!selfroles clear <message_id>` - Clear roles\n"
                "`!selfroles delete <message_id>` - Delete message"
            ),
            inline=False
        )
        
        # Game channels admin commands
        embed.add_field(
            name="🎮 Game Channels Admin",
            value=(
                "`!setgamechannel [#channel]` - Set game channel\n"
                "`!removegamechannel [#channel]` - Remove game channel"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the Admin cog to the bot."""
    await bot.add_cog(Admin(bot)) 