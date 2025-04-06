import asyncio
import discord
import yt_dlp
import logging
import functools
import os
import sys
from async_timeout import timeout
from discord.ext import commands, tasks

# Configure logging
logger = logging.getLogger('discord_bot.music')

# YouTube DL options
YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # Bind to ipv4
}

# FFmpeg options - optimized for hosting platforms
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Detect if running on Replit
IS_REPLIT = 'REPL_ID' in os.environ

# Initialize ytdl with the specified options
ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    """A class that handles downloading and playing audio from YouTube."""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        
        # Store the song data and information
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = self._format_duration(int(data.get('duration', 0)))
        self.thumbnail = data.get('thumbnail')
        self.requester = None  # Will be set when requested
        
    def _format_duration(self, duration):
        """Format the duration into mm:ss or hh:mm:ss."""
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    @classmethod
    async def create_source(cls, search, *, loop=None, requester=None):
        """Create a source from a search query or URL."""
        loop = loop or asyncio.get_event_loop()
        
        # Run ytdl in a thread to avoid blocking
        partial = functools.partial(ytdl.extract_info, search, download=False)
        data = await loop.run_in_executor(None, partial)
        
        if data is None:
            raise Exception(f"Couldn't find anything that matches `{search}`")
        
        # Handle both direct videos and search results
        if 'entries' in data:
            # Take the first item from a playlist
            data = data['entries'][0]
        
        try:
            # Create the source and set the requester
            source = cls(
                discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS),
                data=data
            )
            source.requester = requester
            
            return source
        except discord.errors.ClientException as e:
            if "ffmpeg was not found" in str(e):
                # More detailed error for FFmpeg issues
                error_msg = "FFmpeg was not found. "
                if IS_REPLIT:
                    error_msg += "On Replit, run 'pip install python-ffmpeg' in the Shell tab and restart your repl."
                else:
                    error_msg += "Make sure FFmpeg is installed on your system or hosting platform."
                raise Exception(error_msg)
            else:
                raise e


class MusicPlayer:
    """A class to handle music playback for a specific guild."""
    
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog
        
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        
        self.current = None
        self.volume = 0.5
        self.np = None  # Now playing message
        self.last_activity = asyncio.get_event_loop().time()
        
        # Start the player task
        self.bot.loop.create_task(self.player_loop())
    
    async def player_loop(self):
        """Main player loop that handles playing songs from the queue."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            self.next.clear()
            
            # Check if there's been no activity for 5 minutes (300 seconds)
            if (asyncio.get_event_loop().time() - self.last_activity) > 300:
                # Auto-disconnect due to inactivity
                await self.guild.voice_client.disconnect()
                return
            
            # Wait for the next item in the queue with a 5-minute timeout
            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                # Auto-disconnect on timeout
                await self.guild.voice_client.disconnect()
                return
            
            # Check if anyone is still in the voice channel
            if self.guild.voice_client:
                if not [m for m in self.guild.voice_client.channel.members if not m.bot]:
                    # If no non-bot members remain, disconnect
                    await self.guild.voice_client.disconnect()
                    return
            
            # Update the last activity timestamp
            self.last_activity = asyncio.get_event_loop().time()
            
            # Set the current song and play it
            self.current = source
            self.guild.voice_client.play(
                source, 
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set)
            )
            
            # Send a now playing message
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"[{source.title}]({source.url})",
                color=discord.Color.blurple()
            )
            embed.add_field(name="Duration", value=source.duration)
            embed.add_field(name="Requested by", value=source.requester.display_name)
            
            if source.thumbnail:
                embed.set_thumbnail(url=source.thumbnail)
            
            self.np = await self.channel.send(embed=embed)
            
            # Wait for the song to finish
            await self.next.wait()
            
            # Clean up
            source.cleanup()
            self.current = None
            
            # Delete the now playing message if it exists
            try:
                await self.np.delete()
            except:
                pass


class Music(commands.Cog):
    """Music commands for Discord bot."""
    
    def __init__(self, bot):
        self.bot = bot
        self.players = {}  # Dictionary to store active players per guild
        self.check_voice_channels.start()
        self.music_channels = {}  # Store music channel IDs per guild
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.check_voice_channels.cancel()
    
    # Error handler for the cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle permission errors for music commands."""
        if isinstance(error, commands.MissingPermissions):
            if ctx.command.name in ['setmusicchannel', 'removemusicchannel']:
                await ctx.send("❌ You need Administrator permission to manage music channels.", delete_after=10)
                return
        
        # Let other errors propagate to the global error handler
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            ctx.command_failed = True
    
    # Custom check for music channel restrictions
    async def music_channel_check(self, ctx):
        """Check if the command is being used in an allowed music channel."""
        # If no music channels are set for this guild, allow it anywhere
        if not hasattr(self.bot, 'music_channels') or ctx.guild.id not in self.bot.music_channels:
            return True
        
        # If the command is used in the correct channel, allow it
        if ctx.channel.id == self.bot.music_channels[ctx.guild.id]:
            return True
        
        # If the user is an admin, inform them about the restriction
        if ctx.author.guild_permissions.administrator:
            channel_mention = f"<#{self.bot.music_channels[ctx.guild.id]}>"
            await ctx.send(
                f"❌ Music commands can only be used in {channel_mention}\n"
                f"As an administrator, you can use `!setmusicchannel` to change this.",
                delete_after=10
            )
        else:
            channel_mention = f"<#{self.bot.music_channels[ctx.guild.id]}>"
            await ctx.send(
                f"❌ Music commands can only be used in {channel_mention}",
                delete_after=10
            )
        
        return False
    
    @commands.command(name="setmusicchannel")
    @commands.has_permissions(administrator=True)
    async def set_music_channel(self, ctx, channel: discord.TextChannel = None):
        """Set a channel for music commands.
        
        Usage: !setmusicchannel [#channel]
        Example: !setmusicchannel #music
        If no channel is specified, the current channel will be used.
        Requires Administrator permission.
        """
        # Use the provided channel or the current one
        channel = channel or ctx.channel
        
        # Initialize music_channels dict if it doesn't exist
        if not hasattr(self.bot, 'music_channels'):
            self.bot.music_channels = {}
        
        # Set the music channel for this guild
        self.bot.music_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ {channel.mention} has been set as the music channel!")
    
    @commands.command(name="removemusicchannel")
    @commands.has_permissions(administrator=True)
    async def remove_music_channel(self, ctx):
        """Remove the music channel restriction.
        
        Usage: !removemusicchannel
        Requires Administrator permission.
        """
        # Check if music_channels exists and this guild has a restriction
        if hasattr(self.bot, 'music_channels') and ctx.guild.id in self.bot.music_channels:
            del self.bot.music_channels[ctx.guild.id]
            await ctx.send(f"✅ Music channel restriction has been removed!")
        else:
            await ctx.send(f"ℹ️ No music channel restriction was set.")
    
    @tasks.loop(minutes=5)
    async def check_voice_channels(self):
        """Periodically check voice channels for inactivity."""
        for guild_id, player in list(self.players.items()):
            # If the bot is in a voice channel but no one else is, disconnect
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                if not [m for m in guild.voice_client.channel.members if not m.bot]:
                    await guild.voice_client.disconnect()
                    self.players.pop(guild_id, None)
    
    @check_voice_channels.before_loop
    async def before_check_voice_channels(self):
        """Wait until the bot is ready before checking voice channels."""
        await self.bot.wait_until_ready()
    
    async def get_player(self, ctx):
        """Get or create a player for the guild."""
        player = self.players.get(ctx.guild.id)
        
        if player is None:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        
        return player
    
    async def ensure_voice(self, ctx):
        """Ensure the bot can join/use voice."""
        # Check if the user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ You are not connected to a voice channel.")
            return False
        
        # Check if the bot is already in a voice channel
        if ctx.voice_client:
            # If bot is in a different channel, move to the user's channel
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.voice_client.move_to(ctx.author.voice.channel)
            return True
        
        # Bot is not in a voice channel, join the user's channel
        await ctx.author.voice.channel.connect()
        return True
    
    @commands.command(name="play")
    async def play(self, ctx, *, query=None):
        """Play a song from YouTube.
        
        Usage: !play <song>
        Example: !play despacito
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if a query was provided
        if query is None:
            await ctx.send("❌ Please provide a song to play.\nUsage: `!play <YouTube URL or search query>`")
            return
        
        # Ensure the bot can join the voice channel
        if not await self.ensure_voice(ctx):
            return
        
        # Get the player for this guild
        player = await self.get_player(ctx)
        
        # Send a searching message
        searching_msg = await ctx.send(f"🔍 Searching for: `{query}`")
        
        try:
            # Create a source from the query
            source = await YTDLSource.create_source(query, loop=self.bot.loop, requester=ctx.author)
            
            # Add the source to the queue
            await player.queue.put(source)
            
            # Update the searching message
            await searching_msg.edit(content=f"✅ **{source.title}** has been added to the queue.")
            
            # Update the player's activity timestamp
            player.last_activity = asyncio.get_event_loop().time()
            
        except Exception as e:
            logger.error(f"Error processing play request: {str(e)}")
            await searching_msg.edit(content=f"❌ Error: {str(e)}")
    
    @commands.command(name="pause")
    async def pause(self, ctx):
        """Pause the currently playing song.
        
        Usage: !pause
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if the bot is in a voice channel
        if not ctx.voice_client:
            await ctx.send("❌ I am not currently playing anything.")
            return
        
        # Check if the bot is playing something
        if not ctx.voice_client.is_playing():
            await ctx.send("❌ I am not currently playing anything.")
            return
        
        # Pause the player
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused the player.")
    
    @commands.command(name="resume")
    async def resume(self, ctx):
        """Resume the currently paused song.
        
        Usage: !resume
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if the bot is in a voice channel
        if not ctx.voice_client:
            await ctx.send("❌ I am not currently connected to a voice channel.")
            return
        
        # Check if the bot is paused
        if not ctx.voice_client.is_paused():
            await ctx.send("❌ The player is not paused.")
            return
        
        # Resume the player
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed the player.")
    
    @commands.command(name="skip")
    async def skip(self, ctx):
        """Skip the current song.
        
        Usage: !skip
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if the bot is in a voice channel
        if not ctx.voice_client:
            await ctx.send("❌ I am not currently playing anything.")
            return
        
        # Check if the bot is playing something
        if not ctx.voice_client.is_playing():
            await ctx.send("❌ I am not currently playing anything to skip.")
            return
        
        # Stop the current player (this will trigger the next song)
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped the song.")
    
    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stop playing and clear the queue.
        
        Usage: !stop
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if the bot is in a voice channel
        if not ctx.voice_client:
            await ctx.send("❌ I am not currently playing anything.")
            return
        
        # Clear the queue (if the player exists)
        player = self.players.get(ctx.guild.id)
        if player:
            # Clear the queue
            while not player.queue.empty():
                await player.queue.get()
        
        # Stop the player and disconnect
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Stopped the player and cleared the queue.")
        
        # Remove the player
        self.players.pop(ctx.guild.id, None)
    
    @commands.command(name="queue")
    async def queue(self, ctx):
        """Show the current song queue.
        
        Usage: !queue
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if there's a player for this guild
        player = self.players.get(ctx.guild.id)
        if not player or player.queue.empty() and not player.current:
            await ctx.send("❌ There are no songs in the queue.")
            return
        
        # Create an embed for the queue
        embed = discord.Embed(
            title="🎵 Music Queue",
            color=discord.Color.blurple()
        )
        
        # Add the currently playing song
        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"[{player.current.title}]({player.current.url}) | `{player.current.duration}` | Requested by: {player.current.requester.display_name}",
                inline=False
            )
        
        # Add the queue
        if not player.queue.empty():
            # Convert the queue to a list to display it
            # Note: This is a bit of a hack since we can't enumerate an asyncio.Queue directly
            upcoming = list(player.queue._queue)
            
            # Limit to 10 songs to avoid huge embeds
            items_to_show = min(10, len(upcoming))
            
            # Generate the queue list
            queue_list = "\n".join(
                f"**{i+1}.** [{song.title}]({song.url}) | `{song.duration}` | Requested by: {song.requester.display_name}"
                for i, song in enumerate(upcoming[:items_to_show])
            )
            
            # Add queue field
            embed.add_field(
                name=f"Next Up ({len(upcoming)} songs)",
                value=queue_list if queue_list else "No songs in queue.",
                inline=False
            )
            
            # Add a note if there are more songs
            if len(upcoming) > 10:
                embed.set_footer(text=f"And {len(upcoming) - 10} more songs...")
        
        await ctx.send(embed=embed)

    @commands.command(name="volume")
    async def volume(self, ctx, volume: int = None):
        """Change the player volume.
        
        Usage: !volume <level>
        Example: !volume 50
        The volume level should be between 0 and 100.
        """
        # Check if the command is being used in a designated music channel
        if not await self.music_channel_check(ctx):
            return
        
        # Check if a volume level was provided
        if volume is None:
            await ctx.send("❌ Please provide a volume level between 0 and 100.")
            return
        
        # Check if the provided volume level is valid
        if not (0 <= volume <= 100):
            await ctx.send("❌ The volume level should be between 0 and 100.")
            return
        
        # Get the player for this guild
        player = await self.get_player(ctx)
        
        # Set the new volume
        player.volume = volume / 100
        await ctx.send(f"✅ Volume set to {volume}%")

    @commands.command(name="music")
    async def music_list(self, ctx):
        """Display a list of all available music commands.
        
        Usage: !music
        """
        embed = discord.Embed(
            title="🎵 Music Commands",
            description="Here are all the music commands you can use:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="▶️ Play (`!play`)",
            value="Play a song from YouTube. Usage: `!play <song name or URL>`",
            inline=False
        )
        
        embed.add_field(
            name="⏸️ Pause (`!pause`)",
            value="Pause the currently playing song.",
            inline=False
        )
        
        embed.add_field(
            name="▶️ Resume (`!resume`)",
            value="Resume playback of a paused song.",
            inline=False
        )
        
        embed.add_field(
            name="⏭️ Skip (`!skip`)",
            value="Skip the currently playing song.",
            inline=False
        )
        
        embed.add_field(
            name="⏹️ Stop (`!stop`)",
            value="Stop playback and clear the queue.",
            inline=False
        )
        
        embed.add_field(
            name="📋 Queue (`!queue`)",
            value="Show the current music queue.",
            inline=False
        )
        
        embed.add_field(
            name="🔊 Volume (`!volume`)",
            value="Set the volume of the music player. Usage: `!volume <0-100>`",
            inline=False
        )
        
        embed.add_field(
            name="❓ Now Playing (`!np`)",
            value="Show information about the currently playing song.",
            inline=False
        )
        
        # Only show admin reference if user is an administrator
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Commands",
                value="Type `!admin` to see all administrative commands, including music channel management.",
                inline=False
            )
        
        embed.set_footer(text="Some music commands may be restricted to specific channels")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the Music cog to the bot."""
    await bot.add_cog(Music(bot)) 