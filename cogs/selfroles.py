import discord
import asyncio
import logging
import json
import os
import re
import traceback
from discord.ext import commands

# Configure logging
logger = logging.getLogger('discord_bot.selfroles')

class SelfRoles(commands.Cog):
    """A cog for self-assignable roles via reactions."""
    
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles = {}  # Format: {message_id: {emoji: role_id}}
        self.load_reaction_roles()
    
    def load_reaction_roles(self):
        """Load reaction roles from a JSON file."""
        try:
            if os.path.exists('reaction_roles.json'):
                with open('reaction_roles.json', 'r') as f:
                    self.reaction_roles = json.load(f)
                logger.info(f"Loaded {len(self.reaction_roles)} reaction role messages")
        except Exception as e:
            logger.error(f"Error loading reaction roles: {e}")
            self.reaction_roles = {}
    
    def save_reaction_roles(self):
        """Save reaction roles to a JSON file."""
        try:
            with open('reaction_roles.json', 'w') as f:
                json.dump(self.reaction_roles, f, indent=4)
            logger.info(f"Saved {len(self.reaction_roles)} reaction role messages")
        except Exception as e:
            logger.error(f"Error saving reaction roles: {e}")
    
    def parse_emoji(self, emoji_str):
        """Parse a string into a standard or custom emoji format.
        
        Returns:
            str: The formatted emoji string that can be used for comparisons.
        """
        # Check if it's a custom emoji
        custom_emoji_pattern = re.compile(r'<(a?):([a-zA-Z0-9_]+):(\d+)>')
        match = custom_emoji_pattern.match(emoji_str)
        
        if match:
            animated = match.group(1) == 'a'
            emoji_name = match.group(2)
            emoji_id = match.group(3)
            
            # Get the actual emoji object for adding reaction
            if emoji_id:
                # Try to find the emoji in the server
                for guild in self.bot.guilds:
                    found_emoji = discord.utils.get(guild.emojis, id=int(emoji_id))
                    if found_emoji:
                        custom_emoji = found_emoji
                        break
            
            if not custom_emoji:
                # If we couldn't find the emoji, we try to use the string format
                custom_emoji = emoji
        else:
            # It's a standard Unicode emoji
            custom_emoji = emoji
        
        return custom_emoji
    
    # Error handler for the cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle permission errors for selfroles commands."""
        if isinstance(error, commands.MissingPermissions):
            if ctx.command and ctx.command.parent and ctx.command.parent.name == "selfroles":
                await ctx.send("❌ You need Administrator permission to manage self-roles.", delete_after=10)
                return
        
        # Let other errors propagate to the global error handler
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            ctx.command_failed = True
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction adds for role assignment."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if this is a reaction role message
        if str(payload.message_id) in self.reaction_roles:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                logger.error(f"Guild {payload.guild_id} not found for reaction role")
                return
            
            # Get the emoji string representation
            emoji = str(payload.emoji)
            message_id = str(payload.message_id)
            role_mappings = self.reaction_roles[message_id]
            
            logger.info(f"Reaction added: message={message_id}, emoji={emoji}")
            logger.info(f"Available mappings: {list(role_mappings.keys())}")
            
            # Try direct match first
            role_id = None
            if emoji in role_mappings:
                role_id = role_mappings[emoji]
            else:
                # For custom emojis, try matching by ID
                if hasattr(payload.emoji, 'id') and payload.emoji.id:
                    emoji_id = str(payload.emoji.id)
                    # Look for matching emoji by ID
                    for key, value in role_mappings.items():
                        if f":{emoji_id}>" in key or f":{emoji_id}" == key:
                            role_id = value
                            logger.info(f"Found matching emoji by ID: {key} -> {value}")
                            break
            
            if role_id:
                try:
                    role_id = int(role_id)
                    role = guild.get_role(role_id)
                    
                    if not role:
                        logger.warning(f"Role {role_id} not found in guild {guild.id}")
                        return
                    
                    member = guild.get_member(payload.user_id)
                    if not member:
                        logger.warning(f"Member {payload.user_id} not found in guild {guild.id}")
                        return
                    
                    await member.add_roles(role)
                    logger.info(f"Added role {role.name} to {member.display_name}")
                except ValueError:
                    logger.error(f"Invalid role ID format: {role_id}")
                except discord.Forbidden:
                    logger.error(f"No permission to add role {role_id} to user {payload.user_id}")
                except Exception as e:
                    logger.error(f"Error adding role: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.info(f"No role mapping found for emoji {emoji} in message {message_id}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removes for role removal."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if this is a reaction role message
        if str(payload.message_id) in self.reaction_roles:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                logger.error(f"Guild {payload.guild_id} not found for reaction role")
                return
            
            # Get the emoji string representation
            emoji = str(payload.emoji)
            message_id = str(payload.message_id)
            role_mappings = self.reaction_roles[message_id]
            
            logger.info(f"Reaction removed: message={message_id}, emoji={emoji}")
            logger.info(f"Available mappings: {list(role_mappings.keys())}")
            
            # Try direct match first
            role_id = None
            if emoji in role_mappings:
                role_id = role_mappings[emoji]
            else:
                # For custom emojis, try matching by ID
                if hasattr(payload.emoji, 'id') and payload.emoji.id:
                    emoji_id = str(payload.emoji.id)
                    # Look for matching emoji by ID
                    for key, value in role_mappings.items():
                        if f":{emoji_id}>" in key or f":{emoji_id}" == key:
                            role_id = value
                            logger.info(f"Found matching emoji by ID: {key} -> {value}")
                            break
            
            if role_id:
                try:
                    role_id = int(role_id)
                    role = guild.get_role(role_id)
                    
                    if not role:
                        logger.warning(f"Role {role_id} not found in guild {guild.id}")
                        return
                    
                    member = guild.get_member(payload.user_id)
                    if not member:
                        logger.warning(f"Member {payload.user_id} not found in guild {guild.id}")
                        return
                    
                    await member.remove_roles(role)
                    logger.info(f"Removed role {role.name} from {member.display_name}")
                except ValueError:
                    logger.error(f"Invalid role ID format: {role_id}")
                except discord.Forbidden:
                    logger.error(f"No permission to remove role {role_id} from user {payload.user_id}")
                except Exception as e:
                    logger.error(f"Error removing role: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.info(f"No role mapping found for emoji {emoji} in message {message_id}")
    
    @commands.group(name="selfroles", aliases=["sr"], invoke_without_command=True)
    async def selfroles(self, ctx):
        """Command group for self-assignable roles. Use subcommands to manage roles.
        
        Usage: !selfroles <subcommand>
        Subcommands: create, add, remove, list, clear
        Example: !selfroles create
        """
        await ctx.send(
            "🎭 **Self-Roles Commands**\n"
            "`!selfroles create <title> | <description>` - Create a new self-role message\n"
            "`!selfroles add <message_id> <emoji> <role>` - Add a role to a self-role message\n"
            "`!selfroles remove <message_id> <emoji>` - Remove a role from a self-role message\n"
            "`!selfroles list` - List all self-role messages\n"
            "`!selfroles clear <message_id>` - Remove all roles from a message\n"
            "`!selfroles delete <message_id>` - Delete a self-role message completely\n"
            "`!selfroles debug <message_id>` - Debug a self-role message to see stored emoji and role mappings\n"
            "`!selfroles fix <message_id> <emoji> <role>` - Fix a role mapping for cases where emoji format is causing issues\n\n"
            "**Example:** `!selfroles create Server Roles | React to get roles!`"
        )
    
    @selfroles.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create_selfroles(self, ctx, *, content: str):
        """Create a new self-role message.
        
        Usage: !selfroles create <title> | <description>
        Example: !selfroles create Server Roles | React to get roles!
        
        Requires Administrator permission.
        """
        # Parse the content
        parts = [part.strip() for part in content.split('|', 1)]
        
        if len(parts) != 2:
            await ctx.send("❌ Invalid format. Usage: `!selfroles create <title> | <description>`")
            return
        
        title, description = parts
        
        # Create the embed for the self-role message
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text="React to get roles!")
        
        # Send the message
        message = await ctx.send(embed=embed)
        
        # Store the message ID for reaction roles
        self.reaction_roles[str(message.id)] = {}
        self.save_reaction_roles()
        
        await ctx.send(f"✅ Self-role message created! ID: `{message.id}`\nUse `!selfroles add {message.id} <emoji> <role>` to add roles.")
    
    @selfroles.command(name="add")
    @commands.has_permissions(administrator=True)
    async def add_selfrole(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """Add a role to a self-role message.
        
        Usage: !selfroles add <message_id> <emoji> <role>
        Example: !selfroles add 123456789012345678 🔴 @Red
        
        You can use both standard emojis (e.g., 🔴) or custom server emojis.
        For custom emojis, use their exact format (e.g., <:name:id> or <a:name:id>).
        
        Requires Administrator permission.
        """
        try:
            # Check if the message exists in our tracking
            if str(message_id) not in self.reaction_roles:
                await ctx.send("❌ No self-role message found with that ID!")
                return
            
            # Try to get the message
            try:
                channel = ctx.channel
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found in this channel!")
                return
            except discord.HTTPException as e:
                await ctx.send(f"❌ Error retrieving message: {str(e)}")
                return
            
            # Parse custom emoji if needed
            custom_emoji = emoji
            custom_emoji_pattern = re.compile(r'<(a?):([a-zA-Z0-9_]+):(\d+)>')
            match = custom_emoji_pattern.match(emoji)
            
            if match:
                # It's a custom emoji
                animated = match.group(1) == 'a'
                emoji_name = match.group(2)
                emoji_id = match.group(3)
                
                # Check if the bot has access to this emoji
                found_emoji = None
                for guild in self.bot.guilds:
                    found_emoji = discord.utils.get(guild.emojis, id=int(emoji_id))
                    if found_emoji:
                        custom_emoji = found_emoji
                        break
                
                if not found_emoji:
                    await ctx.send(f"❌ Custom emoji with ID {emoji_id} not found or the bot doesn't have access to it. Make sure the emoji is from a server the bot is in.")
                    return
            
            # Add the emoji to the message
            try:
                await message.add_reaction(custom_emoji)
            except discord.HTTPException as e:
                await ctx.send(f"❌ Error adding reaction: {str(e)}\nMake sure the emoji is valid and the bot has the 'Add Reactions' permission.")
                return
            except discord.InvalidArgument:
                await ctx.send("❌ Invalid emoji format. For custom emojis, use the format `<:name:id>` or `<a:name:id>`.")
                return
            
            # Store the role mapping using the string representation
            emoji_key = str(custom_emoji)
            self.reaction_roles[str(message_id)][emoji_key] = str(role.id)
            self.save_reaction_roles()
            
            # Get current embed and update it
            embed = message.embeds[0] if message.embeds else discord.Embed(title="Self Roles", color=discord.Color.blue())
            
            # Display emoji for the embed
            display_emoji = emoji
            
            # Add or update the field for this role
            existing_fields = len(embed.fields)
            found = False
            
            for i, field in enumerate(embed.fields):
                if field.name.endswith(role.name) and (display_emoji in field.name or emoji_key in field.name):
                    embed.set_field_at(i, name=f"{display_emoji} {role.name}", value=f"React with {display_emoji} to get the {role.mention} role", inline=False)
                    found = True
                    break
            
            if not found:
                embed.add_field(name=f"{display_emoji} {role.name}", value=f"React with {display_emoji} to get the {role.mention} role", inline=False)
            
            # Update the message
            try:
                await message.edit(embed=embed)
            except discord.HTTPException as e:
                await ctx.send(f"⚠️ Warning: Could not update the embed: {str(e)}. The role assignment will still work.")
            
            await ctx.send(f"✅ Added {display_emoji} for role {role.name} to the self-role message!")
            
        except Exception as e:
            logger.error(f"Error in add_selfrole command: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ An unexpected error occurred: {str(e)}")
    
    @selfroles.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def remove_selfrole(self, ctx, message_id: int, emoji: str):
        """Remove a role from a self-role message.
        
        Usage: !selfroles remove <message_id> <emoji>
        Example: !selfroles remove 123456789012345678 🔴
        
        Requires Administrator permission.
        """
        try:
            # Check if the message exists in our tracking
            if str(message_id) not in self.reaction_roles:
                await ctx.send("❌ No self-role message found with that ID!")
                return
            
            # Check if the emoji exists in the mapping
            message_roles = self.reaction_roles[str(message_id)]
            
            # For custom emojis, try to normalize the format
            emoji_key = str(emoji)
            found_key = None
            
            for key in message_roles.keys():
                if key == emoji_key or key.endswith(emoji_key.split(":")[-1]) if ":" in emoji_key else False:
                    found_key = key
                    break
                    
            if not found_key:
                await ctx.send("❌ That emoji is not used in this self-role message!")
                return
            
            emoji_key = found_key
            
            # Try to get the message
            try:
                channel = ctx.channel
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found in this channel!")
                return
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")
                return
            
            # Remove the emoji from the message
            for reaction in message.reactions:
                if str(reaction.emoji) == emoji_key:
                    await reaction.clear()
                    break
            
            # Remove the role mapping
            role_id = message_roles.pop(emoji_key)
            self.save_reaction_roles()
            
            # Get current embed and update it
            embed = message.embeds[0] if message.embeds else discord.Embed(title="Self Roles", color=discord.Color.blue())
            
            # Remove the field for this role
            new_fields = []
            for field in embed.fields:
                # Check if the field contains this emoji
                if not (emoji in field.name or emoji_key in field.name):
                    new_fields.append(field)
            
            # Create a new embed with the updated fields
            new_embed = discord.Embed(
                title=embed.title,
                description=embed.description,
                color=embed.color
            )
            
            for field in new_fields:
                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            # Update the message
            try:
                await message.edit(embed=new_embed)
            except discord.HTTPException as e:
                await ctx.send(f"⚠️ Warning: Could not update the embed: {str(e)}. The role was still removed.")
            
            role = ctx.guild.get_role(int(role_id))
            role_name = role.name if role else "Unknown Role"
            await ctx.send(f"✅ Removed {emoji} for role {role_name} from the self-role message!")
            
        except Exception as e:
            logger.error(f"Error in remove_selfrole command: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await ctx.send(f"❌ An unexpected error occurred: {str(e)}")
    
    @selfroles.command(name="list")
    @commands.has_permissions(administrator=True)
    async def list_selfroles(self, ctx):
        """List all self-role messages.
        
        Usage: !selfroles list
        
        Requires Administrator permission.
        """
        if not self.reaction_roles:
            await ctx.send("❌ No self-role messages have been set up!")
            return
        
        embed = discord.Embed(
            title="🎭 Self-Role Messages",
            description=f"Found {len(self.reaction_roles)} self-role messages:",
            color=discord.Color.blue()
        )
        
        for message_id, roles in self.reaction_roles.items():
            role_count = len(roles)
            
            # Try to get the message
            try:
                channel = ctx.channel
                message = await channel.fetch_message(int(message_id))
                location = f"In {channel.mention}"
                
                # Get the message title
                if message.embeds:
                    title = message.embeds[0].title or "No Title"
                else:
                    title = "No Embed"
            except:
                message = None
                location = "Unknown location"
                title = "Unknown"
            
            # Create a field for this message
            roles_text = "\n".join([f"{emoji} → <@&{role_id}>" for emoji, role_id in roles.items()])
            if not roles_text:
                roles_text = "No roles assigned yet"
            
            embed.add_field(
                name=f"ID: {message_id} - {title}",
                value=f"{location}\n{role_count} roles\n{roles_text}\n[Jump to Message](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{message_id})",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @selfroles.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear_selfroles(self, ctx, message_id: int):
        """Remove all roles from a self-role message.
        
        Usage: !selfroles clear <message_id>
        Example: !selfroles clear 123456789012345678
        
        Requires Administrator permission.
        """
        # Check if the message exists in our tracking
        if str(message_id) not in self.reaction_roles:
            await ctx.send("❌ No self-role message found with that ID!")
            return
        
        # Try to get the message
        try:
            channel = ctx.channel
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Message not found in this channel!")
            return
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
            return
        
        # Clear all reactions
        await message.clear_reactions()
        
        # Save an empty dictionary for this message
        self.reaction_roles[str(message_id)] = {}
        self.save_reaction_roles()
        
        # Update the embed
        if message.embeds:
            embed = message.embeds[0]
            
            # Create a new embed with just the title and description
            new_embed = discord.Embed(
                title=embed.title,
                description=embed.description,
                color=embed.color
            )
            new_embed.set_footer(text="React to get roles!")
            
            # Update the message
            await message.edit(embed=new_embed)
        
        await ctx.send(f"✅ Cleared all roles from the self-role message!")
    
    @selfroles.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def delete_selfroles(self, ctx, message_id: int):
        """Delete a self-role message completely.
        
        Usage: !selfroles delete <message_id>
        Example: !selfroles delete 123456789012345678
        
        Requires Administrator permission.
        """
        # Check if the message exists in our tracking
        if str(message_id) not in self.reaction_roles:
            await ctx.send("❌ No self-role message found with that ID!")
            return
        
        # Try to delete the message
        try:
            channel = ctx.channel
            message = await channel.fetch_message(message_id)
            await message.delete()
        except discord.NotFound:
            # Message already deleted or not found
            pass
        except Exception as e:
            await ctx.send(f"❌ Error deleting message: {str(e)}")
        
        # Remove from tracking regardless of whether the message was found
        del self.reaction_roles[str(message_id)]
        self.save_reaction_roles()
        
        await ctx.send(f"✅ Self-role message deleted and removed from tracking!")

    @selfroles.command(name="debug")
    @commands.has_permissions(administrator=True)
    async def debug_selfroles(self, ctx, message_id: int):
        """Debug a self-role message to see stored emoji and role mappings.
        
        Usage: !selfroles debug <message_id>
        Example: !selfroles debug 123456789012345678
        
        Requires Administrator permission.
        """
        if str(message_id) not in self.reaction_roles:
            await ctx.send("❌ No self-role message found with that ID!")
            return
        
        role_mappings = self.reaction_roles[str(message_id)]
        
        if not role_mappings:
            await ctx.send("ℹ️ This message has no role mappings configured yet.")
            return
        
        # Try to get the message to check actual reactions
        message = None
        try:
            message = await ctx.channel.fetch_message(message_id)
            message_exists = True
            actual_reactions = [str(reaction.emoji) for reaction in message.reactions]
        except:
            message_exists = False
            actual_reactions = []
        
        # Create debug embed
        embed = discord.Embed(
            title=f"🔍 Debug: Self-Roles Message {message_id}",
            description=f"**Message exists:** {message_exists}\n**Role mappings:** {len(role_mappings)}",
            color=discord.Color.gold()
        )
        
        # Add field for each role mapping
        for emoji_key, role_id in role_mappings.items():
            try:
                role = ctx.guild.get_role(int(role_id))
                role_name = role.name if role else "Unknown Role"
                role_status = "✅ Found" if role else "❌ Not Found"
                emoji_in_msg = "✅ Reaction exists" if emoji_key in actual_reactions else "❌ No reaction"
                
                embed.add_field(
                    name=f"Emoji: {emoji_key}",
                    value=f"**Role:** {role_name} ({role_id})\n**Role Status:** {role_status}\n**Reaction Status:** {emoji_in_msg}\n**Stored Key Format:** `{emoji_key}`",
                    inline=False
                )
            except:
                embed.add_field(
                    name=f"Emoji: {emoji_key}",
                    value=f"**Role ID:** {role_id}\n**Status:** ❌ Error processing",
                    inline=False
                )
        
        # Add field with raw data for advanced debugging
        embed.add_field(
            name="Raw Data",
            value=f"```json\n{json.dumps({str(message_id): role_mappings}, indent=2)}\n```",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @selfroles.command(name="fix")
    @commands.has_permissions(administrator=True)
    async def fix_selfroles(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """Fix a role mapping for cases where emoji format is causing issues.
        
        Usage: !selfroles fix <message_id> <emoji> <role>
        Example: !selfroles fix 123456789012345678 🔴 @Red
        
        This removes any existing mapping for the role and creates a new one.
        Requires Administrator permission.
        """
        if str(message_id) not in self.reaction_roles:
            await ctx.send("❌ No self-role message found with that ID!")
            return
        
        role_mappings = self.reaction_roles[str(message_id)]
        
        # Find and remove any mappings for this role
        role_id_str = str(role.id)
        to_remove = []
        for emoji_key, stored_role_id in role_mappings.items():
            if stored_role_id == role_id_str:
                to_remove.append(emoji_key)
        
        for key in to_remove:
            del role_mappings[key]
            
        # Add the new mapping
        role_mappings[str(emoji)] = role_id_str
        self.save_reaction_roles()
        
        # Try to update the reaction on the message
        try:
            message = await ctx.channel.fetch_message(message_id)
            
            # Clear existing reactions for this role
            for reaction in message.reactions:
                if str(reaction.emoji) in to_remove:
                    await reaction.clear()
            
            # Add the new reaction
            await message.add_reaction(emoji)
            
            # Update the embed
            if message.embeds:
                embed = message.embeds[0]
                
                # Remove fields for this role
                new_fields = []
                for field in embed.fields:
                    if role.name not in field.name:
                        new_fields.append(field)
                
                # Create new embed with remaining fields
                new_embed = discord.Embed(
                    title=embed.title,
                    description=embed.description,
                    color=embed.color
                )
                
                # Add all fields except the role we're fixing
                for field in new_fields:
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                
                # Add the fixed role field
                new_embed.add_field(
                    name=f"{emoji} {role.name}",
                    value=f"React with {emoji} to get the {role.mention} role",
                    inline=False
                )
                
                # Update the message
                await message.edit(embed=new_embed)
        except Exception as e:
            await ctx.send(f"⚠️ Warning: Could not update the message: {str(e)}. The role mapping was still updated.")
        
        removed_msg = f"Removed {len(to_remove)} previous mappings" if to_remove else "No previous mappings removed"
        await ctx.send(f"✅ Fixed role mapping for {role.name}! {removed_msg}.")

async def setup(bot):
    """Add the SelfRoles cog to the bot."""
    await bot.add_cog(SelfRoles(bot)) 