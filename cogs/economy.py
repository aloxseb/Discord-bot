import discord
import random
import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from discord.ext import commands

# Configure logging
logger = logging.getLogger('discord_bot.economy')

class Economy(commands.Cog):
    """Economy commands for earning and spending coins."""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "economy_data.json"
        self.economy_data = {}
        self.load_data()
        self.economy_channels = {}  # Store economy channel IDs per guild
    
    def load_data(self):
        """Load economy data from JSON file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.economy_data = json.load(f)
                logger.info(f"Loaded economy data for {len(self.economy_data)} users")
            else:
                self.economy_data = {}
                self.save_data()
        except Exception as e:
            logger.error(f"Error loading economy data: {e}")
            self.economy_data = {}
    
    def save_data(self):
        """Save economy data to JSON file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.economy_data, f, indent=4)
            logger.info(f"Saved economy data for {len(self.economy_data)} users")
        except Exception as e:
            logger.error(f"Error saving economy data: {e}")
    
    def get_user_data(self, user_id):
        """Get or create user data."""
        user_id = str(user_id)
        if user_id not in self.economy_data:
            self.economy_data[user_id] = {
                "coins": 100,  # Starting amount
                "last_daily": None,
                "last_work": None,
                "inventory": []
            }
            self.save_data()
        return self.economy_data[user_id]
    
    # Custom check for economy channel restrictions
    async def economy_channel_check(self, ctx):
        """Check if the command is being used in an allowed economy channel."""
        # If no economy channels are set for this guild, allow it anywhere
        if ctx.guild.id not in self.economy_channels:
            return True
        
        # If the command is used in the correct channel, allow it
        if ctx.channel.id == self.economy_channels[ctx.guild.id]:
            return True
        
        # If the user is an admin, inform them about the restriction
        if ctx.author.guild_permissions.administrator:
            channel_mention = f"<#{self.economy_channels[ctx.guild.id]}>"
            await ctx.send(
                f"❌ Economy commands can only be used in {channel_mention}\n"
                f"As an administrator, you can use `!seteconomychannel` to change this.",
                delete_after=10
            )
        else:
            channel_mention = f"<#{self.economy_channels[ctx.guild.id]}>"
            await ctx.send(
                f"❌ Economy commands can only be used in {channel_mention}",
                delete_after=10
            )
        
        return False
    
    @commands.command(name="seteconomychannel")
    @commands.has_permissions(administrator=True)
    async def set_economy_channel(self, ctx, channel: discord.TextChannel = None):
        """Set a channel for economy commands.
        
        Usage: !seteconomychannel [#channel]
        Example: !seteconomychannel #economy
        If no channel is specified, the current channel will be used.
        Requires Administrator permission.
        """
        # Use the provided channel or the current one
        channel = channel or ctx.channel
        
        # Set the economy channel for this guild
        self.economy_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ {channel.mention} has been set as the economy channel!")
    
    @commands.command(name="removeeconomychannel")
    @commands.has_permissions(administrator=True)
    async def remove_economy_channel(self, ctx):
        """Remove the economy channel restriction.
        
        Usage: !removeeconomychannel
        Requires Administrator permission.
        """
        # Check if this guild has a restriction
        if ctx.guild.id in self.economy_channels:
            del self.economy_channels[ctx.guild.id]
            await ctx.send(f"✅ Economy channel restriction has been removed!")
        else:
            await ctx.send(f"ℹ️ No economy channel restriction was set.")
    
    @commands.command(name="balance", aliases=["bal", "coins", "money"])
    async def balance(self, ctx, member: discord.Member = None):
        """Check your coin balance or someone else's.
        
        Usage: !balance [member]
        Example: !balance @User
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Use the mentioned user or the command author
        target = member or ctx.author
        user_data = self.get_user_data(target.id)
        
        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Balance",
            color=discord.Color.gold()
        )
        embed.add_field(name="Coins", value=f"**{user_data['coins']}** 🪙", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily reward of coins.
        
        Usage: !daily
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        # Check if user has already claimed their daily reward
        if user_data["last_daily"]:
            last_claim = datetime.fromisoformat(user_data["last_daily"])
            now = datetime.now()
            
            # Check if 24 hours have passed since last claim
            if now < last_claim + timedelta(days=1):
                # Calculate time until next claim
                next_claim = last_claim + timedelta(days=1)
                time_left = next_claim - now
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                await ctx.send(f"❌ You have already claimed your daily reward. Try again in {hours}h {minutes}m.")
                return
        
        # Random amount between 100 and 200 coins
        amount = random.randint(100, 200)
        user_data["coins"] += amount
        user_data["last_daily"] = datetime.now().isoformat()
        self.save_data()
        
        embed = discord.Embed(
            title="💰 Daily Reward Claimed!",
            description=f"You received **{amount}** coins! 🪙",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"**{user_data['coins']}** 🪙", inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="work")
    async def work(self, ctx):
        """Work to earn some coins.
        
        Usage: !work
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        # Check if user has already worked recently
        if user_data["last_work"]:
            last_work = datetime.fromisoformat(user_data["last_work"])
            now = datetime.now()
            
            # Check if 1 hour has passed since last work
            if now < last_work + timedelta(hours=1):
                # Calculate time until next work
                next_work = last_work + timedelta(hours=1)
                time_left = next_work - now
                minutes, seconds = divmod(time_left.seconds, 60)
                
                await ctx.send(f"❌ You are too tired to work. Try again in {minutes}m {seconds}s.")
                return
        
        # List of jobs and earnings
        jobs = [
            {"name": "Programmer", "pay": random.randint(25, 50), "message": "You fixed a critical bug in the code."},
            {"name": "Pizza Delivery", "pay": random.randint(20, 40), "message": "You delivered pizzas around town."},
            {"name": "Gardener", "pay": random.randint(15, 35), "message": "You tended to a beautiful garden."},
            {"name": "Teacher", "pay": random.randint(30, 45), "message": "You taught a class of eager students."},
            {"name": "Mechanic", "pay": random.randint(35, 55), "message": "You repaired a broken engine."},
            {"name": "Artist", "pay": random.randint(20, 60), "message": "You sold one of your paintings."},
            {"name": "Chef", "pay": random.randint(25, 45), "message": "You prepared a delicious meal for customers."},
            {"name": "Streamer", "pay": random.randint(10, 70), "message": "You had a successful streaming session."}
        ]
        
        job = random.choice(jobs)
        amount = job["pay"]
        
        user_data["coins"] += amount
        user_data["last_work"] = datetime.now().isoformat()
        self.save_data()
        
        embed = discord.Embed(
            title=f"💼 Worked as a {job['name']}",
            description=job["message"],
            color=discord.Color.blue()
        )
        embed.add_field(name="Earned", value=f"**{amount}** coins 🪙", inline=False)
        embed.add_field(name="New Balance", value=f"**{user_data['coins']}** 🪙", inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="give", aliases=["pay", "send"])
    async def give(self, ctx, member: discord.Member, amount: int):
        """Give coins to another user.
        
        Usage: !give <user> <amount>
        Example: !give @User 100
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Validate the amount
        if amount <= 0:
            await ctx.send("❌ You must give a positive amount of coins.")
            return
        
        # Check if the target is the command author
        if member.id == ctx.author.id:
            await ctx.send("❌ You cannot give coins to yourself.")
            return
        
        # Check if the target is a bot
        if member.bot:
            await ctx.send("❌ You cannot give coins to a bot.")
            return
        
        # Get user data
        sender_data = self.get_user_data(ctx.author.id)
        
        # Check if the sender has enough coins
        if sender_data["coins"] < amount:
            await ctx.send(f"❌ You don't have enough coins! You have **{sender_data['coins']}** 🪙.")
            return
        
        # Get receiver data and transfer the coins
        receiver_data = self.get_user_data(member.id)
        sender_data["coins"] -= amount
        receiver_data["coins"] += amount
        self.save_data()
        
        embed = discord.Embed(
            title="💸 Coins Transferred",
            description=f"{ctx.author.mention} gave **{amount}** coins to {member.mention} 🪙",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{ctx.author.display_name}'s Balance", value=f"**{sender_data['coins']}** 🪙", inline=True)
        embed.add_field(name=f"{member.display_name}'s Balance", value=f"**{receiver_data['coins']}** 🪙", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="gamble", aliases=["bet"])
    async def gamble(self, ctx, amount: int):
        """Gamble your coins for a chance to win more.
        
        Usage: !gamble <amount>
        Example: !gamble 50
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Validate the amount
        if amount <= 0:
            await ctx.send("❌ You must gamble a positive amount of coins.")
            return
        
        # Get user data
        user_data = self.get_user_data(ctx.author.id)
        
        # Check if the user has enough coins
        if user_data["coins"] < amount:
            await ctx.send(f"❌ You don't have enough coins! You have **{user_data['coins']}** 🪙.")
            return
        
        # Roll the dice (1-100)
        roll = random.randint(1, 100)
        
        embed = discord.Embed(
            title="🎲 Gambling Results",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        # Calculate the result
        if roll < 40:  # 40% chance to lose everything
            user_data["coins"] -= amount
            embed.description = f"You rolled a **{roll}** and lost **{amount}** coins. 😢"
            embed.color = discord.Color.red()
        elif roll < 60:  # 20% chance to win nothing (keep your bet)
            embed.description = f"You rolled a **{roll}** and broke even. Your bet has been returned."
            embed.color = discord.Color.gold()
        elif roll < 90:  # 30% chance to win 1.5x
            winnings = int(amount * 1.5)
            user_data["coins"] += (winnings - amount)
            embed.description = f"You rolled a **{roll}** and won **{winnings - amount}** coins! 🎉"
            embed.color = discord.Color.green()
        else:  # 10% chance to win 2x
            winnings = amount * 2
            user_data["coins"] += (winnings - amount)
            embed.description = f"You rolled a **{roll}** and won **{winnings - amount}** coins! 🎊"
            embed.color = discord.Color.green()
        
        self.save_data()
        embed.add_field(name="New Balance", value=f"**{user_data['coins']}** 🪙", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard", aliases=["lb", "rich"])
    async def leaderboard(self, ctx):
        """Display the richest users in the server.
        
        Usage: !leaderboard
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Get all users in the server
        server_members = {member.id: member for member in ctx.guild.members}
        
        # Filter economy data to only include server members and sort by coins
        server_data = []
        for user_id, data in self.economy_data.items():
            user_id = int(user_id)
            if user_id in server_members:
                server_data.append((user_id, data["coins"]))
        
        # Sort by coins (descending)
        server_data.sort(key=lambda x: x[1], reverse=True)
        
        # Create the leaderboard embed
        embed = discord.Embed(
            title="💰 Richest Users",
            description="The users with the most coins in this server:",
            color=discord.Color.gold()
        )
        
        # Add top 10 users to the leaderboard
        for i, (user_id, coins) in enumerate(server_data[:10], 1):
            member = server_members[user_id]
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"**{coins}** 🪙",
                inline=False
            )
        
        # If leaderboard is empty
        if not server_data:
            embed.description = "No one has earned any coins yet!"
        
        await ctx.send(embed=embed)
    
    @commands.command(name="economy")
    async def economy_help(self, ctx):
        """Display information about economy commands.
        
        Usage: !economy
        """
        embed = discord.Embed(
            title="💰 Economy Commands",
            description="Here are all the economy commands you can use:",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Balance (`!balance`, `!bal`)",
            value="Check your coin balance or someone else's. Usage: `!balance [user]`",
            inline=False
        )
        
        embed.add_field(
            name="📆 Daily (`!daily`)",
            value="Claim your daily reward of coins. Resets every 24 hours.",
            inline=False
        )
        
        embed.add_field(
            name="💼 Work (`!work`)",
            value="Work to earn some coins. Available once per hour.",
            inline=False
        )
        
        embed.add_field(
            name="🎁 Give (`!give`)",
            value="Give coins to another user. Usage: `!give <user> <amount>`",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Gamble (`!gamble`, `!bet`)",
            value="Gamble your coins for a chance to win more. Usage: `!gamble <amount>`",
            inline=False
        )
        
        embed.add_field(
            name="📊 Leaderboard (`!leaderboard`, `!lb`)",
            value="Display the richest users in the server.",
            inline=False
        )
        
        embed.add_field(
            name="🛒 Shop (`!shop`)",
            value="Browse items available for purchase with coins.",
            inline=False
        )
        
        embed.add_field(
            name="🛍️ Buy (`!buy`)",
            value="Purchase an item from the shop. Usage: `!buy <item_id>`",
            inline=False
        )
        
        embed.add_field(
            name="🎒 Inventory (`!inventory`, `!inv`)",
            value="View your inventory or someone else's. Usage: `!inventory [user]`",
            inline=False
        )
        
        # Only show admin commands if the user is an administrator
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Commands",
                value="Type `!admin` to see all administrative commands, including economy management.",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shop")
    async def shop(self, ctx):
        """Display the shop where you can buy items with coins.
        
        Usage: !shop
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Define available shop items
        shop_items = [
            {"id": "vip", "name": "VIP Status", "price": 5000, "description": "Get a special VIP role in the server."},
            {"id": "namecolor", "name": "Name Color", "price": 2000, "description": "Change your name color with a custom role."},
            {"id": "lootbox", "name": "Loot Box", "price": 500, "description": "A mystery box with random coin rewards (250-1000)."},
            {"id": "lucky", "name": "Lucky Charm", "price": 1500, "description": "Increases your gambling odds for 24 hours."},
            {"id": "badge", "name": "Profile Badge", "price": 3000, "description": "A special badge for your profile."}
        ]
        
        embed = discord.Embed(
            title="🛒 Shop",
            description="Buy items with your coins! Use `!buy <item>` to purchase.",
            color=discord.Color.blue()
        )
        
        for item in shop_items:
            embed.add_field(
                name=f"{item['name']} - {item['price']} 🪙",
                value=f"{item['description']}\nID: `{item['id']}`",
                inline=False
            )
        
        # Get user balance
        user_data = self.get_user_data(ctx.author.id)
        embed.set_footer(text=f"Your balance: {user_data['coins']} 🪙")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="buy")
    async def buy(self, ctx, item_id: str):
        """Buy an item from the shop.
        
        Usage: !buy <item_id>
        Example: !buy lootbox
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Define available shop items
        shop_items = {
            "vip": {"name": "VIP Status", "price": 5000, "description": "Get a special VIP role in the server."},
            "namecolor": {"name": "Name Color", "price": 2000, "description": "Change your name color with a custom role."},
            "lootbox": {"name": "Loot Box", "price": 500, "description": "A mystery box with random coin rewards (250-1000)."},
            "lucky": {"name": "Lucky Charm", "price": 1500, "description": "Increases your gambling odds for 24 hours."},
            "badge": {"name": "Profile Badge", "price": 3000, "description": "A special badge for your profile."}
        }
        
        # Check if the item exists
        if item_id.lower() not in shop_items:
            await ctx.send(f"❌ Item not found! Use `!shop` to see available items.")
            return
        
        # Get the item and user data
        item = shop_items[item_id.lower()]
        user_data = self.get_user_data(ctx.author.id)
        
        # Check if the user has enough coins
        if user_data["coins"] < item["price"]:
            await ctx.send(f"❌ You don't have enough coins to buy {item['name']}! You need {item['price']} 🪙.")
            return
        
        # Process the purchase based on item type
        purchase_result = await self.process_purchase(ctx, item_id.lower(), item)
        
        if purchase_result["success"]:
            # Deduct coins and save
            user_data["coins"] -= item["price"]
            
            # Add item to inventory if it's not a consumable
            if not purchase_result.get("consumable", False):
                if "inventory" not in user_data:
                    user_data["inventory"] = []
                user_data["inventory"].append(item_id.lower())
            
            self.save_data()
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Purchase Successful",
                description=f"You bought **{item['name']}** for **{item['price']}** coins!",
                color=discord.Color.green()
            )
            
            if "message" in purchase_result:
                embed.add_field(name="Result", value=purchase_result["message"], inline=False)
            
            embed.add_field(name="New Balance", value=f"**{user_data['coins']}** 🪙", inline=False)
            
            await ctx.send(embed=embed)
        else:
            # Purchase failed
            await ctx.send(f"❌ {purchase_result.get('message', 'Purchase failed due to an error.')}")
    
    async def process_purchase(self, ctx, item_id, item):
        """Process a purchase based on the item type."""
        if item_id == "lootbox":
            # Lootbox gives random coins
            reward = random.randint(250, 1000)
            user_data = self.get_user_data(ctx.author.id)
            user_data["coins"] += reward
            
            return {
                "success": True,
                "consumable": True,
                "message": f"You opened the loot box and found **{reward}** coins inside! 🎉"
            }
        
        elif item_id == "vip":
            # Try to give VIP role
            vip_role = discord.utils.get(ctx.guild.roles, name="VIP")
            
            # Create role if it doesn't exist
            if not vip_role:
                try:
                    vip_role = await ctx.guild.create_role(
                        name="VIP",
                        color=discord.Color.gold(),
                        hoist=True,
                        reason="VIP Purchase"
                    )
                except discord.Forbidden:
                    return {
                        "success": False,
                        "message": "I don't have permission to create roles."
                    }
            
            # Add role to user
            try:
                await ctx.author.add_roles(vip_role, reason="VIP Purchase")
                return {
                    "success": True,
                    "message": f"You now have the {vip_role.mention} role! ✨"
                }
            except discord.Forbidden:
                return {
                    "success": False,
                    "message": "I don't have permission to add roles."
                }
        
        elif item_id == "namecolor":
            # Ask for color
            await ctx.send("Please type a color name (e.g., red, blue, green, etc.) or a hex code (e.g., #FF0000):")
            
            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel
            
            try:
                # Wait for response
                color_msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                color_input = color_msg.content.strip().lower()
                
                # Convert color name to hex
                color_map = {
                    "red": discord.Color.red(),
                    "blue": discord.Color.blue(),
                    "green": discord.Color.green(),
                    "gold": discord.Color.gold(),
                    "purple": discord.Color.purple(),
                    "orange": discord.Color.orange(),
                    "teal": discord.Color.teal()
                }
                
                if color_input in color_map:
                    color = color_map[color_input]
                elif color_input.startswith('#') and len(color_input) == 7:
                    # Convert hex to RGB
                    try:
                        color_value = int(color_input[1:], 16)
                        color = discord.Color(color_value)
                    except ValueError:
                        return {
                            "success": False,
                            "message": "Invalid hex color code."
                        }
                else:
                    return {
                        "success": False,
                        "message": "Invalid color name or hex code."
                    }
                
                # Create or update color role
                role_name = f"{ctx.author.name}'s Color"
                color_role = discord.utils.get(ctx.guild.roles, name=role_name)
                
                if color_role:
                    try:
                        await color_role.edit(color=color, reason="Name Color Purchase")
                    except discord.Forbidden:
                        return {
                            "success": False,
                            "message": "I don't have permission to edit roles."
                        }
                else:
                    try:
                        color_role = await ctx.guild.create_role(
                            name=role_name,
                            color=color,
                            reason="Name Color Purchase"
                        )
                    except discord.Forbidden:
                        return {
                            "success": False,
                            "message": "I don't have permission to create roles."
                        }
                
                # Add role to user and position it
                try:
                    await ctx.author.add_roles(color_role, reason="Name Color Purchase")
                    
                    # Move role to just below the bot's highest role for visibility
                    bot_role = ctx.guild.get_member(self.bot.user.id).top_role
                    await color_role.edit(position=bot_role.position - 1)
                    
                    return {
                        "success": True,
                        "message": f"Your name color has been changed! ✨"
                    }
                except discord.Forbidden:
                    return {
                        "success": False,
                        "message": "I don't have permission to add roles or move them."
                    }
                
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "message": "You took too long to respond."
                }
        
        elif item_id == "lucky":
            # Add lucky charm status (24 hour boost to gambling)
            user_data = self.get_user_data(ctx.author.id)
            user_data["lucky_until"] = (datetime.now() + timedelta(days=1)).isoformat()
            
            return {
                "success": True,
                "message": "You now have a Lucky Charm! Your gambling odds are increased for the next 24 hours. 🍀"
            }
        
        elif item_id == "badge":
            # Add badge to user data
            user_data = self.get_user_data(ctx.author.id)
            
            if "badges" not in user_data:
                user_data["badges"] = []
            
            # Different badge types
            badges = ["🥇", "👑", "💎", "🏆", "⭐"]
            
            # Pick a random badge they don't already have
            available_badges = [b for b in badges if b not in user_data["badges"]]
            
            if not available_badges:
                # If they have all badges, allow duplicates
                badge = random.choice(badges)
            else:
                badge = random.choice(available_badges)
            
            user_data["badges"].append(badge)
            
            return {
                "success": True,
                "message": f"You received a new badge: {badge}"
            }
        
        # Default response for unimplemented items
        return {
            "success": True,
            "message": f"You purchased {item['name']}!"
        }
    
    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, member: discord.Member = None):
        """View your inventory or someone else's.
        
        Usage: !inventory [user]
        Example: !inventory @User
        """
        # Check if the command is being used in a designated economy channel
        if not await self.economy_channel_check(ctx):
            return
        
        # Use the mentioned user or the command author
        target = member or ctx.author
        user_data = self.get_user_data(target.id)
        
        # Create inventory embed
        embed = discord.Embed(
            title=f"🎒 {target.display_name}'s Inventory",
            color=discord.Color.blue()
        )
        
        # Check if user has an inventory
        if "inventory" not in user_data or not user_data["inventory"]:
            embed.description = "This inventory is empty."
        else:
            # Count items
            item_counts = {}
            for item in user_data["inventory"]:
                if item in item_counts:
                    item_counts[item] += 1
                else:
                    item_counts[item] = 1
            
            # Add items to embed
            for item, count in item_counts.items():
                # Get item name based on ID
                item_names = {
                    "vip": "VIP Status",
                    "namecolor": "Name Color",
                    "lucky": "Lucky Charm",
                    "badge": "Profile Badge"
                }
                
                name = item_names.get(item, item.capitalize())
                embed.add_field(name=name, value=f"Quantity: {count}", inline=True)
        
        # Add badges if they exist
        if "badges" in user_data and user_data["badges"]:
            badges = " ".join(user_data["badges"])
            embed.add_field(name="Badges", value=badges, inline=False)
        
        # Add lucky charm status if active
        if "lucky_until" in user_data:
            try:
                lucky_until = datetime.fromisoformat(user_data["lucky_until"])
                if datetime.now() < lucky_until:
                    time_left = lucky_until - datetime.now()
                    hours, remainder = divmod(time_left.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    embed.add_field(
                        name="🍀 Lucky Charm",
                        value=f"Active for {hours}h {minutes}m",
                        inline=False
                    )
            except:
                pass
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="addcoins")
    @commands.has_permissions(administrator=True)
    async def add_coins(self, ctx, member: discord.Member, amount: int):
        """Add coins to a user's balance (Admin only).
        
        Usage: !addcoins <user> <amount>
        Example: !addcoins @User 1000
        Requires Administrator permission.
        """
        # Validate the amount
        if amount <= 0:
            await ctx.send("❌ You must add a positive amount of coins.")
            return
        
        # Get user data
        user_data = self.get_user_data(member.id)
        
        # Add coins
        user_data["coins"] += amount
        self.save_data()
        
        embed = discord.Embed(
            title="💰 Coins Added",
            description=f"Added **{amount}** coins to {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"**{user_data['coins']}** 🪙", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="removecoins")
    @commands.has_permissions(administrator=True)
    async def remove_coins(self, ctx, member: discord.Member, amount: int):
        """Remove coins from a user's balance (Admin only).
        
        Usage: !removecoins <user> <amount>
        Example: !removecoins @User 1000
        Requires Administrator permission.
        """
        # Validate the amount
        if amount <= 0:
            await ctx.send("❌ You must remove a positive amount of coins.")
            return
        
        # Get user data
        user_data = self.get_user_data(member.id)
        
        # Check if user has enough coins
        if user_data["coins"] < amount:
            user_data["coins"] = 0
            self.save_data()
            await ctx.send(f"⚠️ User had fewer coins than the amount. Balance set to 0.")
            return
        
        # Remove coins
        user_data["coins"] -= amount
        self.save_data()
        
        embed = discord.Embed(
            title="💰 Coins Removed",
            description=f"Removed **{amount}** coins from {member.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="New Balance", value=f"**{user_data['coins']}** 🪙", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="setcoins")
    @commands.has_permissions(administrator=True)
    async def set_coins(self, ctx, member: discord.Member, amount: int):
        """Set a user's coin balance to a specific amount (Admin only).
        
        Usage: !setcoins <user> <amount>
        Example: !setcoins @User 1000
        Requires Administrator permission.
        """
        # Validate the amount
        if amount < 0:
            await ctx.send("❌ You must set a non-negative amount of coins.")
            return
        
        # Get user data
        user_data = self.get_user_data(member.id)
        
        # Set coins
        user_data["coins"] = amount
        self.save_data()
        
        embed = discord.Embed(
            title="💰 Coins Set",
            description=f"Set {member.mention}'s balance to **{amount}** coins",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="giveall")
    @commands.has_permissions(administrator=True)
    async def give_all(self, ctx, amount: int):
        """Give coins to all members in the server (Admin only).
        
        Usage: !giveall <amount>
        Example: !giveall 100
        Requires Administrator permission.
        """
        # Validate the amount
        if amount <= 0:
            await ctx.send("❌ You must give a positive amount of coins.")
            return
        
        # Get all server members
        members = ctx.guild.members
        
        # Filter out bots
        human_members = [member for member in members if not member.bot]
        
        # Add coins to each member
        for member in human_members:
            user_data = self.get_user_data(member.id)
            user_data["coins"] += amount
        
        # Save after all updates
        self.save_data()
        
        embed = discord.Embed(
            title="💰 Mass Coin Distribution",
            description=f"Added **{amount}** coins to **{len(human_members)}** members!",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the Economy cog to the bot."""
    await bot.add_cog(Economy(bot)) 