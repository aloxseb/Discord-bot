import discord
import asyncio
import random
import datetime
import logging
import re
from discord.ext import commands, tasks

# Configure logging
logger = logging.getLogger('discord_bot.giveaway')

class Giveaway(commands.Cog):
    """A cog for creating and managing giveaways."""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}  # Dictionary to store active giveaways
        self.check_giveaways.start()
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.check_giveaways.cancel()
    
    # Error handler for the cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle permission errors for giveaway commands."""
        if isinstance(error, commands.MissingPermissions):
            if ctx.command and ctx.command.parent and ctx.command.parent.name == "giveaway":
                await ctx.send("❌ You need Administrator permission to manage giveaways.", delete_after=10)
                return
        
        # Let other errors propagate to the global error handler
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            ctx.command_failed = True
    
    @tasks.loop(seconds=10.0)
    async def check_giveaways(self):
        """Check active giveaways periodically to see if any have ended."""
        # Get the current time
        now = datetime.datetime.now()
        
        # Make a copy of the keys to avoid modifying the dictionary during iteration
        giveaway_ids = list(self.active_giveaways.keys())
        
        for giveaway_id in giveaway_ids:
            giveaway = self.active_giveaways[giveaway_id]
            
            # Check if the giveaway has ended
            if now >= giveaway['end_time']:
                try:
                    await self.end_giveaway(giveaway_id)
                except Exception as e:
                    logger.error(f"Error ending giveaway {giveaway_id}: {str(e)}")
    
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait until the bot is ready before starting the giveaway check loop."""
        await self.bot.wait_until_ready()
    
    @commands.group(name="giveaway", aliases=["g"], invoke_without_command=True)
    async def giveaway(self, ctx):
        """Command group for giveaways. Use subcommands to manage giveaways.
        
        Usage: !giveaway <subcommand>
        Subcommands: create, end, reroll, list, cancel
        Example: !giveaway create
        """
        await ctx.send(
            "🎉 **Giveaway Commands**\n"
            "`!giveaway create <time> <winners> <prize>` - Create a new giveaway\n"
            "`!giveaway list` - List all active giveaways\n"
            "`!giveaway end <message_id>` - End a giveaway early\n"
            "`!giveaway reroll <message_id> [winners]` - Reroll winners for a completed giveaway\n"
            "`!giveaway cancel <message_id>` - Cancel an active giveaway\n\n"
            "**Example:** `!giveaway create 24h 3 Discord Nitro`"
        )
    
    @giveaway.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create_giveaway(self, ctx, time_str: str, winners_str: str, *, prize: str):
        """Create a new giveaway.
        
        Time can be specified in seconds (s), minutes (m), hours (h), or days (d).
        Example times: 30s, 5m, 2h, 1d
        
        Usage: !giveaway create <time> <winners> <prize>
        Example: !giveaway create 24h 3 Discord Nitro
        Requires Administrator permission.
        """
        # Parse time
        try:
            seconds = self.parse_time(time_str)
            if seconds <= 0:
                await ctx.send("❌ Time must be a positive value!")
                return
        except ValueError:
            await ctx.send("❌ Invalid time format! Examples: 30s, 5m, 2h, 1d")
            return
        
        # Parse winners
        try:
            winners = int(winners_str)
            if winners <= 0:
                await ctx.send("❌ Winner count must be a positive number!")
                return
            if winners > 20:
                await ctx.send("❌ You can have at most 20 winners!")
                return
        except ValueError:
            await ctx.send("❌ Winner count must be a number!")
            return
        
        # Calculate end time
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        
        # Create the giveaway embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**{prize}**\n\n"
                      f"React with 🎉 to enter!\n\n"
                      f"Winner count: {winners}\n",
            color=discord.Color.gold()
        )
        
        # Add fields for hosted by and time remaining
        embed.add_field(name="Hosted by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Ends at", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        embed.set_footer(text=f"Giveaway ID: {ctx.message.id} | Ends at")
        embed.timestamp = end_time
        
        # Send the giveaway message and add the reaction
        giveaway_message = await ctx.send(embed=embed)
        await giveaway_message.add_reaction("🎉")
        
        # Store the giveaway information
        self.active_giveaways[giveaway_message.id] = {
            'channel_id': ctx.channel.id,
            'message_id': giveaway_message.id,
            'host_id': ctx.author.id,
            'prize': prize,
            'winner_count': winners,
            'end_time': end_time,
            'ended': False
        }
        
        await ctx.send(f"🎉 Giveaway created! ID: `{giveaway_message.id}`")
    
    @giveaway.command(name="end")
    @commands.has_permissions(administrator=True)
    async def end_giveaway_command(self, ctx, message_id: int):
        """End a giveaway early.
        
        Usage: !giveaway end <message_id>
        Example: !giveaway end 123456789012345678
        Requires Administrator permission.
        """
        if message_id not in self.active_giveaways:
            await ctx.send("❌ No active giveaway found with that ID!")
            return
        
        # End the giveaway
        await self.end_giveaway(message_id)
        await ctx.send("✅ Giveaway ended!")
    
    async def end_giveaway(self, giveaway_id):
        """End a giveaway and select winners."""
        if giveaway_id not in self.active_giveaways:
            return
        
        giveaway = self.active_giveaways[giveaway_id]
        
        # Mark the giveaway as ended
        giveaway['ended'] = True
        
        # Get the channel and message
        channel = self.bot.get_channel(giveaway['channel_id'])
        if not channel:
            logger.error(f"Channel {giveaway['channel_id']} not found for giveaway {giveaway_id}")
            # Can't end the giveaway if we can't find the channel
            return
        
        try:
            message = await channel.fetch_message(giveaway['message_id'])
        except discord.NotFound:
            logger.error(f"Message {giveaway['message_id']} not found for giveaway {giveaway_id}")
            # Can't end the giveaway if we can't find the message
            return
        
        # Get the reactions
        reaction = None
        for r in message.reactions:
            if str(r.emoji) == "🎉":
                reaction = r
                break
        
        if not reaction:
            # No reactions found, no winners
            winners = []
        else:
            # Get the list of users who reacted
            users = []
            async for user in reaction.users():
                if not user.bot:  # Exclude bots
                    users.append(user)
            
            # Select winners
            winner_count = min(giveaway['winner_count'], len(users))
            winners = random.sample(users, winner_count) if winner_count > 0 else []
        
        # Update the giveaway embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED 🎉",
            description=f"**{giveaway['prize']}**\n\n",
            color=discord.Color.gold()
        )
        
        # Add winner information
        if winners:
            winner_mentions = [winner.mention for winner in winners]
            embed.description += f"Winners: {', '.join(winner_mentions)}\n"
        else:
            embed.description += "No winners (no valid entries).\n"
        
        # Add fields
        host = await self.bot.fetch_user(giveaway['host_id'])
        host_mention = host.mention if host else "Unknown User"
        
        embed.add_field(name="Hosted by", value=host_mention, inline=True)
        embed.add_field(name="Ended at", value=f"<t:{int(datetime.datetime.now().timestamp())}:f>", inline=True)
        embed.set_footer(text=f"Giveaway ID: {giveaway_id} | Ended at")
        embed.timestamp = datetime.datetime.now()
        
        # Update the message
        await message.edit(embed=embed)
        
        # Send a message announcing the winners
        if winners:
            win_message = f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway['prize']}**!"
            await channel.send(win_message)
        else:
            await channel.send(f"❌ No winners for the **{giveaway['prize']}** giveaway (no valid entries).")
        
        # Remove from active giveaways but keep the info for rerolls
        # self.active_giveaways[giveaway_id] = giveaway
    
    @giveaway.command(name="reroll")
    @commands.has_permissions(administrator=True)
    async def reroll_giveaway(self, ctx, message_id: int, winners_str: str = None):
        """Reroll winners for a completed giveaway.
        
        Usage: !giveaway reroll <message_id> [winners]
        Example: !giveaway reroll 123456789012345678 2
        Requires Administrator permission.
        """
        if message_id not in self.active_giveaways:
            await ctx.send("❌ No giveaway found with that ID!")
            return
        
        giveaway = self.active_giveaways[message_id]
        
        if not giveaway['ended']:
            await ctx.send("❌ That giveaway has not ended yet!")
            return
        
        # Parse winners if provided
        if winners_str:
            try:
                winner_count = int(winners_str)
                if winner_count <= 0:
                    await ctx.send("❌ Winner count must be a positive number!")
                    return
                if winner_count > 20:
                    await ctx.send("❌ You can have at most 20 winners!")
                    return
            except ValueError:
                await ctx.send("❌ Winner count must be a number!")
                return
        else:
            winner_count = giveaway['winner_count']
        
        # Get the channel and message
        channel = self.bot.get_channel(giveaway['channel_id'])
        if not channel:
            await ctx.send("❌ Cannot find the giveaway channel!")
            return
        
        try:
            message = await channel.fetch_message(giveaway['message_id'])
        except discord.NotFound:
            await ctx.send("❌ Cannot find the giveaway message!")
            return
        
        # Get the reactions
        reaction = None
        for r in message.reactions:
            if str(r.emoji) == "🎉":
                reaction = r
                break
        
        if not reaction:
            await ctx.send("❌ No reactions found on the giveaway!")
            return
        
        # Get the list of users who reacted
        users = []
        async for user in reaction.users():
            if not user.bot:  # Exclude bots
                users.append(user)
        
        # Select winners
        winner_count = min(winner_count, len(users))
        winners = random.sample(users, winner_count) if winner_count > 0 else []
        
        # Send message with new winners
        if winners:
            winner_mentions = [winner.mention for winner in winners]
            await ctx.send(f"🎉 New winners for **{giveaway['prize']}**: {', '.join(winner_mentions)}!")
        else:
            await ctx.send(f"❌ Could not determine new winners for **{giveaway['prize']}** (no valid entries).")
    
    @giveaway.command(name="list")
    async def list_giveaways(self, ctx):
        """List all active giveaways.
        
        Usage: !giveaway list
        """
        # Filter to only active (not ended) giveaways
        active_giveaways = {gid: g for gid, g in self.active_giveaways.items() if not g['ended']}
        
        if not active_giveaways:
            await ctx.send("📋 There are no active giveaways.")
            return
        
        # Create an embed to list the giveaways
        embed = discord.Embed(
            title="🎉 Active Giveaways",
            color=discord.Color.blue()
        )
        
        for gid, giveaway in active_giveaways.items():
            # Calculate time left
            time_left = giveaway['end_time'] - datetime.datetime.now()
            if time_left.total_seconds() <= 0:
                time_str = "Ending soon..."
            else:
                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_parts = []
                if days > 0:
                    time_parts.append(f"{days}d")
                if hours > 0:
                    time_parts.append(f"{hours}h")
                if minutes > 0:
                    time_parts.append(f"{minutes}m")
                if seconds > 0 and not time_parts:  # Only show seconds if no other units
                    time_parts.append(f"{seconds}s")
                
                time_str = " ".join(time_parts) + " left"
            
            # Add a field for this giveaway
            embed.add_field(
                name=f"ID: {gid} - {giveaway['prize']}",
                value=f"Winners: {giveaway['winner_count']} | {time_str}\n"
                    f"[Jump to Giveaway](https://discord.com/channels/{ctx.guild.id}/{giveaway['channel_id']}/{giveaway['message_id']})",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @giveaway.command(name="cancel")
    @commands.has_permissions(administrator=True)
    async def cancel_giveaway(self, ctx, message_id: int):
        """Cancel an active giveaway.
        
        Usage: !giveaway cancel <message_id>
        Example: !giveaway cancel 123456789012345678
        Requires Administrator permission.
        """
        if message_id not in self.active_giveaways:
            await ctx.send("❌ No giveaway found with that ID!")
            return
        
        giveaway = self.active_giveaways[message_id]
        
        if giveaway['ended']:
            await ctx.send("❌ That giveaway has already ended!")
            return
        
        # Get the channel and message
        channel = self.bot.get_channel(giveaway['channel_id'])
        if not channel:
            await ctx.send("❌ Cannot find the giveaway channel!")
            return
        
        try:
            message = await channel.fetch_message(giveaway['message_id'])
            
            # Update the giveaway embed to show it was cancelled
            embed = discord.Embed(
                title="🚫 GIVEAWAY CANCELLED 🚫",
                description=f"**{giveaway['prize']}**\n\n"
                          f"This giveaway has been cancelled by a moderator.",
                color=discord.Color.red()
            )
            
            # Add fields
            host = await self.bot.fetch_user(giveaway['host_id'])
            host_mention = host.mention if host else "Unknown User"
            
            embed.add_field(name="Hosted by", value=host_mention, inline=True)
            embed.add_field(name="Cancelled at", value=f"<t:{int(datetime.datetime.now().timestamp())}:f>", inline=True)
            embed.set_footer(text=f"Giveaway ID: {message_id} | Cancelled at")
            embed.timestamp = datetime.datetime.now()
            
            # Update the message
            await message.edit(embed=embed)
            
            # Mark the giveaway as ended and cancelled
            giveaway['ended'] = True
            giveaway['cancelled'] = True
            
            await ctx.send("✅ Giveaway cancelled!")
            
        except discord.NotFound:
            await ctx.send("❌ Cannot find the giveaway message! It may have been deleted.")
            # Since the message is gone, just remove it from active giveaways
            del self.active_giveaways[message_id]
    
    def parse_time(self, time_str):
        """Parse a time string into seconds."""
        # Regular expression to match time format
        match = re.match(r'(\d+)([smhd])', time_str.lower())
        if not match:
            raise ValueError("Invalid time format")
        
        value, unit = match.groups()
        value = int(value)
        
        # Convert to seconds based on unit
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400

async def setup(bot):
    """Add the Giveaway cog to the bot."""
    await bot.add_cog(Giveaway(bot)) 