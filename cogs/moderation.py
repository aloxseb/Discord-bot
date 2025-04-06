import logging
import discord
from discord.ext import commands
import asyncio
import datetime
from typing import Optional, Union

# Configure logging
logger = logging.getLogger('discord_bot.moderation')

class Moderation(commands.Cog):
    """Commands for server moderation."""
    
    def __init__(self, bot):
        self.bot = bot
        self.muted_users = {}  # Dictionary to store muted users and their timers
    
    async def cog_check(self, ctx):
        """Check if the user has the appropriate permissions for any command in this cog."""
        # Skip the check if in DMs
        if not ctx.guild:
            await ctx.send("Moderation commands can only be used in servers.")
            return False
        
        # Check if the user has the appropriate permissions
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("You don't have the required permissions to use moderation commands.")
            return False
        
        return True
    
    @commands.command(name="mod")
    async def mod_list(self, ctx):
        """Display a list of all available moderation commands.
        
        Usage: !mod
        """
        embed = discord.Embed(
            title="🛡️ Moderation Commands",
            description="Here are all the moderation commands you can use:",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="🧹 Clear Messages (`!clear`)",
            value="Delete a specified number of messages from a channel. Usage: `!clear <amount> [user]`",
            inline=False
        )
        
        embed.add_field(
            name="👢 Kick (`!kick`)",
            value="Kick a member from the server. Usage: `!kick <user> [reason]`",
            inline=False
        )
        
        embed.add_field(
            name="🔨 Ban (`!ban`)",
            value="Ban a member from the server. Usage: `!ban <user> [reason]`",
            inline=False
        )
        
        embed.add_field(
            name="🔓 Unban (`!unban`)",
            value="Unban a user from the server. Usage: `!unban <user_id> [reason]`",
            inline=False
        )
        
        embed.add_field(
            name="🔇 Mute (`!mute`)",
            value="Temporarily mute a member. Usage: `!mute <user> [duration] [reason]`\nDuration format: 1d12h30m (1 day, 12 hours, 30 minutes)",
            inline=False
        )
        
        embed.add_field(
            name="🔊 Unmute (`!unmute`)",
            value="Unmute a previously muted member. Usage: `!unmute <user> [reason]`",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Warn (`!warn`)",
            value="Warn a member for rule violations. Usage: `!warn <user> [reason]`",
            inline=False
        )
        
        # Show admin reference for admins
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Commands",
                value="Type `!admin` to see all administrative commands.",
                inline=False
            )
        
        embed.set_footer(text="Moderation commands require appropriate permissions")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="clear", aliases=["purge", "clean"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear_messages(self, ctx, amount: int, user: Optional[discord.Member] = None):
        """Delete a specified number of messages from a channel.
        
        Usage: !clear <amount> [user]
        Example: !clear 10
        Example: !clear 20 @User
        """
        if amount <= 0:
            await ctx.send("❌ Please specify a positive number of messages to delete.")
            return
        
        if amount > 100:
            await ctx.send("❌ You can delete at most 100 messages at once.")
            return
        
        # Delete the command message
        await ctx.message.delete()
        
        # If a user is specified, delete only their messages
        if user:
            def check(message):
                return message.author == user
            
            deleted = await ctx.channel.purge(limit=amount, check=check)
            message = f"🧹 Deleted {len(deleted)} messages from {user.display_name}."
        else:
            deleted = await ctx.channel.purge(limit=amount)
            message = f"🧹 Deleted {len(deleted)} messages."
        
        # Send confirmation message that will self-delete after 5 seconds
        confirm_msg = await ctx.send(message)
        await asyncio.sleep(5)
        try:
            await confirm_msg.delete()
        except discord.NotFound:
            pass  # Message was already deleted
    
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server.
        
        Usage: !kick <user> [reason]
        Example: !kick @User Breaking rules
        """
        # Check if the bot can kick the member
        if not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send("❌ I don't have permission to kick members!")
            return
        
        # Check if the user is trying to kick themselves
        if member == ctx.author:
            await ctx.send("❌ You cannot kick yourself!")
            return
        
        # Check if the user is trying to kick someone with a higher role
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot kick someone with a higher or equal role!")
            return
        
        # Check if the bot can kick the member (role hierarchy)
        if ctx.guild.me.top_role <= member.top_role:
            await ctx.send("❌ I cannot kick someone with a higher or equal role to me!")
            return
        
        # Create an embed for the kick
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked from the server.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Try to send a DM to the member before kicking
        try:
            dm_embed = discord.Embed(
                title="You have been kicked",
                description=f"You have been kicked from **{ctx.guild.name}**.",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            dm_embed.timestamp = datetime.datetime.utcnow()
            
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            # Can't send DM to the user
            pass
        
        # Kick the member
        try:
            await member.kick(reason=f"{ctx.author} - {reason}")
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick that member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban_member(self, ctx, member: Union[discord.Member, discord.User], *, reason: str = "No reason provided"):
        """Ban a member from the server.
        
        Usage: !ban <user> [reason]
        Example: !ban @User Breaking rules
        """
        # Check if the bot can ban the member
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send("❌ I don't have permission to ban members!")
            return
        
        # Check if the user is trying to ban themselves
        if isinstance(member, discord.Member) and member == ctx.author:
            await ctx.send("❌ You cannot ban yourself!")
            return
        
        # Check if the user is trying to ban someone with a higher role (if it's a member)
        if isinstance(member, discord.Member):
            if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("❌ You cannot ban someone with a higher or equal role!")
                return
            
            # Check if the bot can ban the member (role hierarchy)
            if ctx.guild.me.top_role <= member.top_role:
                await ctx.send("❌ I cannot ban someone with a higher or equal role to me!")
                return
        
        # Create an embed for the ban
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned from the server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Try to send a DM to the member before banning
        if isinstance(member, discord.Member):
            try:
                dm_embed = discord.Embed(
                    title="You have been banned",
                    description=f"You have been banned from **{ctx.guild.name}**.",
                    color=discord.Color.dark_red()
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
                dm_embed.timestamp = datetime.datetime.utcnow()
                
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                # Can't send DM to the user
                pass
        
        # Ban the member
        try:
            await ctx.guild.ban(member, reason=f"{ctx.author} - {reason}", delete_message_days=1)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban_member(self, ctx, user_id: int, *, reason: str = "No reason provided"):
        """Unban a user from the server using their ID.
        
        Usage: !unban <user_id> [reason]
        Example: !unban 123456789012345678 Good behavior
        """
        # Check if the bot can unban the user
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send("❌ I don't have permission to unban members!")
            return
        
        # Try to find the banned user
        try:
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            user = ban_entry.user
        except discord.NotFound:
            await ctx.send("❌ This user is not banned!")
            return
        
        # Create an embed for the unban
        embed = discord.Embed(
            title="🔓 User Unbanned",
            description=f"{user.mention} has been unbanned from the server.",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Unban the user
        try:
            await ctx.guild.unban(user, reason=f"{ctx.author} - {reason}")
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unban that user!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def mute_member(self, ctx, member: discord.Member, duration: Optional[str] = None, *, reason: str = "No reason provided"):
        """Mute a member in the server.
        
        Duration can be specified in seconds (s), minutes (m), hours (h), or days (d).
        If no duration is specified, the mute is indefinite.
        
        Usage: !mute <user> [duration] [reason]
        Example: !mute @User 10m Spamming
        """
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("❌ I don't have permission to manage roles!")
            return
        
        # Check if the user is trying to mute themselves
        if member == ctx.author:
            await ctx.send("❌ You cannot mute yourself!")
            return
        
        # Check if the user is trying to mute someone with a higher role
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot mute someone with a higher or equal role!")
            return
        
        # Check if the bot can mute the member (role hierarchy)
        if ctx.guild.me.top_role <= member.top_role:
            await ctx.send("❌ I cannot mute someone with a higher or equal role to me!")
            return
        
        # Find or create a "Muted" role
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role is None:
            # Create the Muted role
            try:
                muted_role = await ctx.guild.create_role(
                    name="Muted",
                    reason="Mute command auto-created role"
                )
                
                # Set permissions for the role
                for channel in ctx.guild.channels:
                    try:
                        await channel.set_permissions(muted_role, send_messages=False, add_reactions=False, speak=False)
                    except discord.Forbidden:
                        continue
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to create roles!")
                return
            except discord.HTTPException as e:
                await ctx.send(f"❌ An error occurred: {e}")
                return
        
        # Check if the member is already muted
        if muted_role in member.roles:
            await ctx.send(f"❌ {member.mention} is already muted!")
            return
        
        # Parse duration if provided
        seconds = 0
        if duration:
            try:
                unit = duration[-1].lower()
                value = int(duration[:-1])
                
                if unit == 's':
                    seconds = value
                elif unit == 'm':
                    seconds = value * 60
                elif unit == 'h':
                    seconds = value * 3600
                elif unit == 'd':
                    seconds = value * 86400
                else:
                    await ctx.send("❌ Invalid duration format! Examples: 10s, 5m, 2h, 1d")
                    return
            except (ValueError, IndexError):
                await ctx.send("❌ Invalid duration format! Examples: 10s, 5m, 2h, 1d")
                return
        
        # Create an embed for the mute
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted in the server.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=False)
            embed.add_field(name="Expires", value=f"<t:{int((datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)).timestamp())}:R>", inline=False)
        else:
            embed.add_field(name="Duration", value="Indefinite", inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Try to send a DM to the member before muting
        try:
            dm_embed = discord.Embed(
                title="You have been muted",
                description=f"You have been muted in **{ctx.guild.name}**.",
                color=discord.Color.orange()
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            if duration:
                dm_embed.add_field(name="Duration", value=duration, inline=False)
                dm_embed.add_field(name="Expires", value=f"<t:{int((datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)).timestamp())}:R>", inline=False)
            else:
                dm_embed.add_field(name="Duration", value="Indefinite", inline=False)
            dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            dm_embed.timestamp = datetime.datetime.utcnow()
            
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            # Can't send DM to the user
            pass
        
        # Mute the member
        try:
            await member.add_roles(muted_role, reason=f"{ctx.author} - {reason}")
            await ctx.send(embed=embed)
            
            # Set up temporary mute if duration is provided
            if seconds > 0:
                # Store the timer and member info for unmuting later
                self.muted_users[member.id] = {
                    'guild_id': ctx.guild.id,
                    'expiration': datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds),
                    'muted_role_id': muted_role.id,
                    'moderator_id': ctx.author.id,
                    'reason': reason
                }
                
                # Schedule the unmute
                self.bot.loop.create_task(self.unmute_task(member.id, seconds))
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to mute that member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    async def unmute_task(self, member_id, seconds):
        """Task to automatically unmute a member after a given time."""
        await asyncio.sleep(seconds)
        
        # Check if the member is still in the muted list
        if member_id not in self.muted_users:
            return
        
        mute_info = self.muted_users.pop(member_id)
        guild = self.bot.get_guild(mute_info['guild_id'])
        
        if not guild:
            return
        
        member = guild.get_member(member_id)
        muted_role = guild.get_role(mute_info['muted_role_id'])
        
        if not member or not muted_role or muted_role not in member.roles:
            return
        
        # Unmute the member
        try:
            await member.remove_roles(muted_role, reason="Temporary mute expired")
            
            # Try to DM the member
            try:
                embed = discord.Embed(
                    title="You have been unmuted",
                    description=f"You have been automatically unmuted in **{guild.name}**.",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                embed.timestamp = datetime.datetime.utcnow()
                
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
            
            # Log the unmute in the server logs if possible
            log_channel = discord.utils.get(guild.text_channels, name="mod-logs")
            if log_channel and log_channel.permissions_for(guild.me).send_messages:
                moderator = guild.get_member(mute_info['moderator_id']) or f"User ID: {mute_info['moderator_id']}"
                moderator_mention = moderator.mention if isinstance(moderator, discord.Member) else moderator
                
                embed = discord.Embed(
                    title="🔊 Member Unmuted",
                    description=f"{member.mention} has been automatically unmuted.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Original Reason", value=mute_info['reason'], inline=False)
                embed.add_field(name="Original Moderator", value=moderator_mention, inline=False)
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.timestamp = datetime.datetime.utcnow()
                
                await log_channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass
    
    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Unmute a member in the server.
        
        Usage: !unmute <user> [reason]
        Example: !unmute @User Good behavior
        """
        # Find the "Muted" role
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role is None:
            await ctx.send("❌ There is no 'Muted' role in this server!")
            return
        
        # Check if the member is muted
        if muted_role not in member.roles:
            await ctx.send(f"❌ {member.mention} is not muted!")
            return
        
        # Create an embed for the unmute
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted in the server.",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Try to send a DM to the member
        try:
            dm_embed = discord.Embed(
                title="You have been unmuted",
                description=f"You have been unmuted in **{ctx.guild.name}**.",
                color=discord.Color.green()
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            dm_embed.timestamp = datetime.datetime.utcnow()
            
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            # Can't send DM to the user
            pass
        
        # Unmute the member
        try:
            await member.remove_roles(muted_role, reason=f"{ctx.author} - {reason}")
            await ctx.send(embed=embed)
            
            # Remove from muted users if present
            if member.id in self.muted_users:
                del self.muted_users[member.id]
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to unmute that member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {e}")
    
    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def warn_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member in the server.
        
        Usage: !warn <user> [reason]
        Example: !warn @User Breaking rules
        """
        # Check if the user is trying to warn themselves
        if member == ctx.author:
            await ctx.send("❌ You cannot warn yourself!")
            return
        
        # Check if the user is trying to warn someone with a higher role
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot warn someone with a higher or equal role!")
            return
        
        # Create an embed for the warning
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"{member.mention} has been warned.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Try to send a DM to the member
        try:
            dm_embed = discord.Embed(
                title="You have been warned",
                description=f"You have received a warning in **{ctx.guild.name}**.",
                color=discord.Color.gold()
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            dm_embed.timestamp = datetime.datetime.utcnow()
            
            await member.send(embed=dm_embed)
            dm_sent = True
        except discord.Forbidden:
            # Can't send DM to the user
            dm_sent = False
        
        # Send the warning embed
        await ctx.send(embed=embed)
        
        # Inform if DM couldn't be sent
        if not dm_sent:
            await ctx.send(f"⚠️ I couldn't DM {member.mention} about this warning.")

async def setup(bot):
    """Add the Moderation cog to the bot."""
    await bot.add_cog(Moderation(bot)) 