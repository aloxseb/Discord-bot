import discord
import asyncio
import logging
from discord.ext import commands
from discord import app_commands

# Configure logging
logger = logging.getLogger('discord_bot.counting')

class Counting(commands.Cog):
    """A cog for the counting game."""
    
    def __init__(self, bot):
        self.bot = bot
        self.counting_channels = {}  # Dictionary to store counting game info for each channel
        
        # Sample counting game structure:
        # self.counting_channels[channel_id] = {
        #    'next_number': 1,
        #    'last_user': None,
        #    'highest_count': 0,
        #    'strict_mode': True,
        #    'error_on_fail': True,
        #    'active': True
        # }
    
    # Error handler for the cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle permission errors for counting commands."""
        if isinstance(error, commands.MissingPermissions):
            if ctx.command and ctx.command.parent and ctx.command.parent.name == "counting":
                await ctx.send("❌ You need Administrator permission to manage counting channels.", delete_after=10)
                return
        
        # Let other errors propagate to the global error handler
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            ctx.command_failed = True
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages in counting channels."""
        # Ignore if message is from a bot or not in a counting channel
        if message.author.bot or message.channel.id not in self.counting_channels:
            return
        
        # Get the counting game for this channel
        game = self.counting_channels[message.channel.id]
        
        # Check if the game is active
        if not game['active']:
            return
        
        # Try to convert the message to a number
        try:
            number = int(message.content.strip())
        except ValueError:
            # Not a valid number, ignore
            return
        
        # In strict mode, check if the number is exactly the next number
        if game['strict_mode'] and number != game['next_number']:
            if game['error_on_fail']:
                await self.handle_counting_error(message.channel, message.author, game, number)
            return
        
        # In non-strict mode, check if the number is at least greater than the last
        if not game['strict_mode'] and number <= game['next_number'] - 1:
            if game['error_on_fail']:
                await self.handle_counting_error(message.channel, message.author, game, number)
            return
        
        # Check if the same user is counting twice in a row
        if game['last_user'] == message.author.id:
            if game['error_on_fail']:
                await self.handle_consecutive_error(message.channel, message.author, game)
            return
        
        # If we got here, the count is valid
        game['next_number'] = number + 1
        game['last_user'] = message.author.id
        
        # Update highest count if applicable
        if number > game['highest_count']:
            game['highest_count'] = number
        
        # Add a reaction to indicate success
        await message.add_reaction('✅')
        
        # Special milestones
        if number in [10, 25, 50, 69, 100, 250, 500, 1000]:
            await message.add_reaction('🎉')
            if number >= 100:
                await message.channel.send(f"Congratulations on reaching **{number}**! 🎊")
    
    async def handle_counting_error(self, channel, user, game, number):
        """Handle a counting error (wrong number)."""
        # Add error reaction
        await channel.send(
            f"❌ {user.mention} broke the count at **{game['next_number'] - 1}**! "
            f"The next number was **{game['next_number']}**, but you said **{number}**.\n"
            f"Counting restarts from **1**."
        )
        
        # Reset the game
        game['next_number'] = 1
        game['last_user'] = None
    
    async def handle_consecutive_error(self, channel, user, game):
        """Handle a user counting twice in a row."""
        # Add error reaction
        await channel.send(
            f"❌ {user.mention} broke the count at **{game['next_number'] - 1}**! "
            f"You can't count twice in a row.\n"
            f"Counting restarts from **1**."
        )
        
        # Reset the game
        game['next_number'] = 1
        game['last_user'] = None
    
    @commands.group(name="counting", aliases=["count"], invoke_without_command=True)
    async def counting(self, ctx):
        """Command group for the counting game. Use subcommands to manage the game.
        
        Usage: !counting <subcommand>
        Subcommands: setup, info, reset, strict, mode
        Example: !counting setup
        """
        await ctx.send(
            "📊 **Counting Game Commands**\n"
            "`!counting setup` - Set up a counting channel\n"
            "`!counting info` - Show information about the current counting game\n"
            "`!counting reset` - Reset the counting game\n"
            "`!counting strict <on/off>` - Toggle strict mode\n"
            "`!counting mode <silent/error>` - Set error mode\n"
            "`!counting stop` - Stop the counting game\n"
            "`!counting start` - Start the counting game"
        )
    
    @counting.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_counting(self, ctx):
        """Set up the current channel as a counting channel.
        
        Usage: !counting setup
        Requires Administrator permission.
        """
        channel_id = ctx.channel.id
        
        # Check if already set up
        if channel_id in self.counting_channels:
            await ctx.send("❌ This channel is already set up for counting!")
            return
        
        # Create a new counting game
        self.counting_channels[channel_id] = {
            'next_number': 1,
            'last_user': None,
            'highest_count': 0,
            'strict_mode': True,
            'error_on_fail': True,
            'active': True
        }
        
        # Send confirmation message
        embed = discord.Embed(
            title="🔢 Counting Game Setup",
            description=(
                "This channel is now set up for counting!\n\n"
                "**Rules:**\n"
                "1. Count one number at a time, starting from 1\n"
                "2. Each person can only count once in a row\n"
                "3. If you make a mistake, the count restarts\n\n"
                "**Type '1' to start counting!**"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @counting.command(name="info")
    async def counting_info(self, ctx):
        """Show information about the current counting game.
        
        Usage: !counting info
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting!")
            return
        
        # Get the game info
        game = self.counting_channels[channel_id]
        
        # Create the info embed
        embed = discord.Embed(
            title="🔢 Counting Game Info",
            color=discord.Color.blue()
        )
        
        # Add fields with game info
        embed.add_field(name="Next Number", value=game['next_number'], inline=True)
        embed.add_field(name="Highest Count", value=game['highest_count'], inline=True)
        embed.add_field(name="Strict Mode", value="On" if game['strict_mode'] else "Off", inline=True)
        embed.add_field(name="Error Mode", value="Show Errors" if game['error_on_fail'] else "Silent", inline=True)
        embed.add_field(name="Status", value="Active" if game['active'] else "Paused", inline=True)
        
        # If there's a last user, get their mention
        if game['last_user']:
            last_user = await self.bot.fetch_user(game['last_user'])
            last_user_mention = last_user.mention if last_user else "Unknown User"
        else:
            last_user_mention = "None"
        
        embed.add_field(name="Last Counter", value=last_user_mention, inline=True)
        
        await ctx.send(embed=embed)
    
    @counting.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_counting(self, ctx):
        """Reset the counting game back to 1.
        
        Usage: !counting reset
        Requires Administrator permission.
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting!")
            return
        
        # Reset game but keep settings
        game = self.counting_channels[channel_id]
        highest_count = game['highest_count']  # Keep track of highest count
        game['next_number'] = 1
        game['last_user'] = None
        
        await ctx.send(f"🔄 The counting game has been reset. Next number: **1**\n"
                     f"The highest count was: **{highest_count}**")
    
    @counting.command(name="strict")
    @commands.has_permissions(administrator=True)
    async def set_strict_mode(self, ctx, mode: str = None):
        """Set the strict mode for the counting game.
        
        In strict mode, users must enter the exact next number.
        In non-strict mode, users can skip numbers but must still count up.
        
        Usage: !counting strict <on/off>
        Example: !counting strict off
        Requires Administrator permission.
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting!")
            return
        
        if mode is None:
            await ctx.send("❌ Please specify `on` or `off` for strict mode!")
            return
        
        # Parse the mode
        mode = mode.lower()
        if mode in ('on', 'true', 'yes', 'enable', 'enabled'):
            strict_mode = True
            mode_str = "on"
        elif mode in ('off', 'false', 'no', 'disable', 'disabled'):
            strict_mode = False
            mode_str = "off"
        else:
            await ctx.send("❌ Invalid mode! Please use `on` or `off`.")
            return
        
        # Update the game
        self.counting_channels[channel_id]['strict_mode'] = strict_mode
        
        await ctx.send(f"✅ Strict mode has been turned **{mode_str}**.\n"
                     f"{'Users must enter the exact next number.' if strict_mode else 'Users can skip numbers but must still count up.'}")
    
    @counting.command(name="mode")
    @commands.has_permissions(manage_channels=True)
    async def set_error_mode(self, ctx, mode: str = None):
        """Set the error handling mode for the counting game.
        
        In error mode, the bot sends a message when someone breaks the count.
        In silent mode, the bot doesn't send error messages.
        
        Usage: !counting mode <error/silent>
        Example: !counting mode silent
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting!")
            return
        
        if mode is None:
            await ctx.send("❌ Please specify `error` or `silent` for the error mode!")
            return
        
        # Parse the mode
        mode = mode.lower()
        if mode in ('error', 'errors', 'show', 'alert', 'alerts'):
            error_on_fail = True
            mode_str = "show errors"
        elif mode in ('silent', 'quiet', 'hide', 'nothing'):
            error_on_fail = False
            mode_str = "silent"
        else:
            await ctx.send("❌ Invalid mode! Please use `error` or `silent`.")
            return
        
        # Update the game
        self.counting_channels[channel_id]['error_on_fail'] = error_on_fail
        
        await ctx.send(f"✅ Error mode has been set to **{mode_str}**.\n"
                     f"{'The bot will send messages when someone breaks the count.' if error_on_fail else 'The bot will not send error messages.'}")
    
    @counting.command(name="stop", aliases=["pause"])
    @commands.has_permissions(manage_channels=True)
    async def stop_counting(self, ctx):
        """Stop the counting game.
        
        Usage: !counting stop
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting!")
            return
        
        # Check if already stopped
        if not self.counting_channels[channel_id]['active']:
            await ctx.send("❌ The counting game is already stopped!")
            return
        
        # Stop the game
        self.counting_channels[channel_id]['active'] = False
        
        await ctx.send("⏸️ The counting game has been stopped. Use `!counting start` to resume.")
    
    @counting.command(name="start", aliases=["resume"])
    @commands.has_permissions(manage_channels=True)
    async def start_counting(self, ctx):
        """Start the counting game.
        
        Usage: !counting start
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting! Use `!counting setup` first.")
            return
        
        # Check if already active
        if self.counting_channels[channel_id]['active']:
            await ctx.send("❌ The counting game is already active!")
            return
        
        # Start the game
        self.counting_channels[channel_id]['active'] = True
        
        await ctx.send(f"▶️ The counting game has been started. Next number: **{self.counting_channels[channel_id]['next_number']}**")
    
    @counting.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def remove_counting(self, ctx):
        """Remove the counting game from this channel.
        
        Usage: !counting remove
        """
        channel_id = ctx.channel.id
        
        # Check if channel is set up for counting
        if channel_id not in self.counting_channels:
            await ctx.send("❌ This channel is not set up for counting!")
            return
        
        # Remove the game
        del self.counting_channels[channel_id]
        
        await ctx.send("🗑️ The counting game has been removed from this channel.")

async def setup(bot):
    """Add the Counting cog to the bot."""
    await bot.add_cog(Counting(bot)) 