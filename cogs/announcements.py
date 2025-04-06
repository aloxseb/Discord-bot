import discord
import asyncio
import logging
from discord.ext import commands
from discord import app_commands
from typing import Optional

# Configure logging
logger = logging.getLogger('discord_bot.announcements')

class Announcements(commands.Cog):
    """A cog for server announcements and notifications."""
    
    def __init__(self, bot):
        self.bot = bot
        self.announcement_channels = {}  # Store announcement channel IDs per guild
    
    # Error handler for the cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle permission errors for announcement commands."""
        if isinstance(error, commands.MissingPermissions):
            if ctx.command and ctx.command.parent and ctx.command.parent.name == "announce":
                await ctx.send("❌ You need Administrator permission to manage announcements.", delete_after=10)
                return
        
        # Let other errors propagate to the global error handler
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            ctx.command_failed = True
    
    @commands.command(name="msg")
    @commands.has_permissions(administrator=True)
    async def send_message(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send a message to a specific channel as the bot.
        
        Usage: !msg [#channel] {message}
        Example: !msg #general Hello everyone!
        
        Requires Administrator permission.
        """
        try:
            # Send the message to the specified channel
            sent_message = await channel.send(message)
            
            # Send confirmation to the command user
            confirm_embed = discord.Embed(
                title="✅ Message Sent",
                description=f"**Message:**\n{message}",
                color=discord.Color.green()
            )
            confirm_embed.add_field(name="Channel", value=channel.mention, inline=True)
            confirm_embed.add_field(name="Jump to Message", 
                                   value=f"[Click Here](https://discord.com/channels/{ctx.guild.id}/{channel.id}/{sent_message.id})", 
                                   inline=True)
            
            await ctx.send(embed=confirm_embed, delete_after=30)
            
            # If command was used in a different channel, delete the command message
            if ctx.channel.id != channel.id:
                try:
                    await ctx.message.delete()
                except:
                    pass
                
            logger.info(f"Admin {ctx.author.name} sent a message to {channel.name} using the bot")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to send messages in that channel.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}", delete_after=10)
            logger.error(f"Error in msg command: {e}")
    
    @commands.group(name="announce", aliases=["announcement"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx):
        """Command group for announcements. Use subcommands to manage announcements.
        
        Usage: !announce <subcommand>
        Subcommands: send, setup, clear
        Example: !announce send Important announcement!
        Requires Administrator permission.
        """
        await ctx.send(
            "📢 **Announcement Commands**\n"
            "`!announce send <message>` - Send an announcement\n"
            "`!announce setup [channel]` - Set up the announcement channel\n"
            "`!announce embed <title> | <description> | [color] | [image_url]` - Send an embed announcement\n"
            "`!announce clear` - Clear the announcement channel setting\n"
            "`!announce poll <question> | <option1> | <option2> | [option3] ...` - Create a poll\n\n"
            "**Example:** `!announce send Hello @everyone, this is an important announcement!`"
        )
    
    @announce.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_announcement_channel(self, ctx, channel: discord.TextChannel = None):
        """Set up the announcement channel for this server.
        
        Usage: !announce setup [channel]
        Example: !announce setup #announcements
        Requires Administrator permission.
        """
        # If no channel is specified, use the current channel
        if channel is None:
            channel = ctx.channel
        
        # Store the channel ID for this guild
        self.announcement_channels[ctx.guild.id] = channel.id
        
        await ctx.send(f"✅ Announcement channel set to {channel.mention}.")
    
    @announce.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear_announcement_channel(self, ctx):
        """Clear the announcement channel setting for this server.
        
        Usage: !announce clear
        Requires Administrator permission.
        """
        if ctx.guild.id in self.announcement_channels:
            del self.announcement_channels[ctx.guild.id]
            await ctx.send("✅ Announcement channel setting cleared.")
        else:
            await ctx.send("❌ No announcement channel is set for this server.")
    
    @announce.command(name="send")
    @commands.has_permissions(administrator=True)
    async def send_announcement(self, ctx, *, message: str):
        """Send an announcement to the designated channel.
        
        Usage: !announce send <message>
        Example: !announce send Hello everyone, this is an important announcement!
        Requires Administrator permission.
        """
        # Check if an announcement channel is set
        if ctx.guild.id not in self.announcement_channels:
            await ctx.send("❌ No announcement channel is set. Use `!announce setup` first.")
            return
        
        # Get the announcement channel
        channel_id = self.announcement_channels[ctx.guild.id]
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            await ctx.send("❌ Announcement channel not found. It may have been deleted.")
            del self.announcement_channels[ctx.guild.id]
            return
        
        # Preview the announcement
        preview = discord.Embed(
            title="📢 Announcement Preview",
            description=message,
            color=discord.Color.blue()
        )
        preview.add_field(name="Destination", value=channel.mention, inline=False)
        preview.set_footer(text="React with ✅ to send or ❌ to cancel")
        
        # Send preview and add reactions
        preview_msg = await ctx.send(embed=preview)
        await preview_msg.add_reaction("✅")
        await preview_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == preview_msg.id
        
        try:
            # Wait for reaction
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            # If confirmed, send the announcement
            if str(reaction.emoji) == "✅":
                await channel.send(message)
                
                # Add confirmation to preview message
                conf_embed = discord.Embed(
                    title="✅ Announcement Sent",
                    description=message,
                    color=discord.Color.green()
                )
                conf_embed.add_field(name="Sent to", value=channel.mention, inline=False)
                await preview_msg.edit(embed=conf_embed)
                
                # Remove reactions
                await preview_msg.clear_reactions()
            else:
                # If cancelled, update preview message
                cancel_embed = discord.Embed(
                    title="❌ Announcement Cancelled",
                    description=message,
                    color=discord.Color.red()
                )
                await preview_msg.edit(embed=cancel_embed)
                
                # Remove reactions
                await preview_msg.clear_reactions()
        
        except asyncio.TimeoutError:
            # If timed out, update preview message
            timeout_embed = discord.Embed(
                title="⏱️ Announcement Timed Out",
                description=message,
                color=discord.Color.orange()
            )
            await preview_msg.edit(embed=timeout_embed)
            
            # Remove reactions
            await preview_msg.clear_reactions()
    
    @announce.command(name="embed")
    @commands.has_permissions(administrator=True)
    async def embed_announcement(self, ctx, *, content: str):
        """Send an embed announcement to the designated channel.
        
        Format: !announce embed <title> | <description> | [color] | [image_url]
        Example: !announce embed Server Update | We've added new features! | blue | https://example.com/image.png
        
        Available colors: red, green, blue, gold, orange, purple, teal
        Requires Administrator permission.
        """
        # Check if an announcement channel is set
        if ctx.guild.id not in self.announcement_channels:
            await ctx.send("❌ No announcement channel is set. Use `!announce setup` first.")
            return
        
        # Get the announcement channel
        channel_id = self.announcement_channels[ctx.guild.id]
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            await ctx.send("❌ Announcement channel not found. It may have been deleted.")
            del self.announcement_channels[ctx.guild.id]
            return
        
        # Parse the content
        parts = [part.strip() for part in content.split('|', 3)]
        
        if len(parts) < 2:
            await ctx.send("❌ Not enough parameters. Format: `!announce embed <title> | <description> | [color] | [image_url]`")
            return
        
        title = parts[0]
        description = parts[1]
        
        # Parse color if provided
        color = discord.Color.blue()  # Default color
        if len(parts) >= 3 and parts[2]:
            color_name = parts[2].lower()
            if color_name == "red":
                color = discord.Color.red()
            elif color_name == "green":
                color = discord.Color.green()
            elif color_name == "blue":
                color = discord.Color.blue()
            elif color_name == "gold":
                color = discord.Color.gold()
            elif color_name == "orange":
                color = discord.Color.orange()
            elif color_name == "purple":
                color = discord.Color.purple()
            elif color_name == "teal":
                color = discord.Color.teal()
        
        # Create the embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        # Add image if provided
        if len(parts) >= 4 and parts[3]:
            image_url = parts[3]
            embed.set_image(url=image_url)
        
        # Add footer with author info
        embed.set_footer(text=f"Posted by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # Preview the announcement
        preview_embed = discord.Embed(
            title="📢 Embed Announcement Preview",
            description="Here's a preview of your announcement:",
            color=discord.Color.blue()
        )
        preview_embed.add_field(name="Destination", value=channel.mention, inline=False)
        preview_embed.set_footer(text="React with ✅ to send or ❌ to cancel")
        
        # Send preview and add reactions
        preview_msg = await ctx.send(embeds=[preview_embed, embed])
        await preview_msg.add_reaction("✅")
        await preview_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == preview_msg.id
        
        try:
            # Wait for reaction
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            # If confirmed, send the announcement
            if str(reaction.emoji) == "✅":
                await channel.send(embed=embed)
                
                # Add confirmation to preview message
                conf_embed = discord.Embed(
                    title="✅ Embed Announcement Sent",
                    description="Your announcement has been sent.",
                    color=discord.Color.green()
                )
                conf_embed.add_field(name="Sent to", value=channel.mention, inline=False)
                await preview_msg.edit(embeds=[conf_embed])
                
                # Remove reactions
                await preview_msg.clear_reactions()
            else:
                # If cancelled, update preview message
                cancel_embed = discord.Embed(
                    title="❌ Embed Announcement Cancelled",
                    description="Your announcement has been cancelled.",
                    color=discord.Color.red()
                )
                await preview_msg.edit(embeds=[cancel_embed])
                
                # Remove reactions
                await preview_msg.clear_reactions()
        
        except asyncio.TimeoutError:
            # If timed out, update preview message
            timeout_embed = discord.Embed(
                title="⏱️ Embed Announcement Timed Out",
                description="You did not respond in time.",
                color=discord.Color.orange()
            )
            await preview_msg.edit(embeds=[timeout_embed])
            
            # Remove reactions
            await preview_msg.clear_reactions()
    
    @announce.command(name="poll")
    @commands.has_permissions(administrator=True)
    async def create_poll(self, ctx, *, content: str):
        """Create a poll with reactions.
        
        Format: !announce poll <question> | <option1> | <option2> | [option3] ...
        Example: !announce poll What's your favorite color? | Red | Blue | Green | Yellow
        
        You can add up to 10 options.
        Requires Administrator permission.
        """
        # Check if an announcement channel is set
        if ctx.guild.id not in self.announcement_channels:
            await ctx.send("❌ No announcement channel is set. Use `!announce setup` first.")
            return
        
        # Get the announcement channel
        channel_id = self.announcement_channels[ctx.guild.id]
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            await ctx.send("❌ Announcement channel not found. It may have been deleted.")
            del self.announcement_channels[ctx.guild.id]
            return
        
        # Parse the content
        parts = [part.strip() for part in content.split('|')]
        
        if len(parts) < 3:
            await ctx.send("❌ Not enough options. Format: `!announce poll <question> | <option1> | <option2> | [option3] ...`")
            return
        
        if len(parts) > 11:
            await ctx.send("❌ Too many options. Maximum is 10 options.")
            return
        
        question = parts[0]
        options = parts[1:]
        
        # Emoji numbers for options (1-10)
        emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        # Create the poll embed
        embed = discord.Embed(
            title="📊 " + question,
            description="React with the corresponding emoji to vote!",
            color=discord.Color.blue()
        )
        
        # Add options to the embed
        for i, option in enumerate(options):
            embed.add_field(name=f"{emoji_numbers[i]} {option}", value="", inline=False)
        
        # Add footer with author info
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # Preview the poll
        preview_embed = discord.Embed(
            title="📊 Poll Preview",
            description="Here's a preview of your poll:",
            color=discord.Color.blue()
        )
        preview_embed.add_field(name="Destination", value=channel.mention, inline=False)
        preview_embed.set_footer(text="React with ✅ to send or ❌ to cancel")
        
        # Send preview and add reactions
        preview_msg = await ctx.send(embeds=[preview_embed, embed])
        await preview_msg.add_reaction("✅")
        await preview_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == preview_msg.id
        
        try:
            # Wait for reaction
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            # If confirmed, send the poll
            if str(reaction.emoji) == "✅":
                poll_msg = await channel.send(embed=embed)
                
                # Add option reactions
                for i in range(len(options)):
                    await poll_msg.add_reaction(emoji_numbers[i])
                
                # Add confirmation to preview message
                conf_embed = discord.Embed(
                    title="✅ Poll Sent",
                    description="Your poll has been sent.",
                    color=discord.Color.green()
                )
                conf_embed.add_field(name="Sent to", value=channel.mention, inline=False)
                await preview_msg.edit(embeds=[conf_embed])
                
                # Remove reactions
                await preview_msg.clear_reactions()
            else:
                # If cancelled, update preview message
                cancel_embed = discord.Embed(
                    title="❌ Poll Cancelled",
                    description="Your poll has been cancelled.",
                    color=discord.Color.red()
                )
                await preview_msg.edit(embeds=[cancel_embed])
                
                # Remove reactions
                await preview_msg.clear_reactions()
        
        except asyncio.TimeoutError:
            # If timed out, update preview message
            timeout_embed = discord.Embed(
                title="⏱️ Poll Timed Out",
                description="You did not respond in time.",
                color=discord.Color.orange()
            )
            await preview_msg.edit(embeds=[timeout_embed])
            
            # Remove reactions
            await preview_msg.clear_reactions()

async def setup(bot):
    """Add the Announcements cog to the bot."""
    await bot.add_cog(Announcements(bot)) 