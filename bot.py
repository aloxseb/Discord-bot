import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guild_messages = True

# Initialize bot with prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected to Discord."""
    logger.info(f'{bot.user.name} has connected to Discord!')
    logger.info(f'Bot ID: {bot.user.id}')
    logger.info(f'Currently connected to {len(bot.guilds)} server(s)')
    await bot.change_presence(activity=discord.Game(name="Subscribe cheytho illea poyi sub cheyye <3."))

async def load_extensions():
    """Load all cogs from the cogs directory."""
    cogs_dir = "cogs"
    
    # Ensure cogs directory exists
    if not os.path.exists(cogs_dir):
        logger.warning(f"Cogs directory '{cogs_dir}' not found. Creating it...")
        os.makedirs(cogs_dir)
        return
    
    # List of cogs to load
    cogs = [
        'cogs.fun',
        'cogs.games',
        'cogs.giveaway',
        'cogs.counting',
        'cogs.announcements',
        'cogs.music',  # Keep the music cog
        'cogs.moderation',  # Keep the moderation cog
        'cogs.selfroles',  # Add the new selfroles cog
        'cogs.economy',  # Add the new economy cog
        'cogs.admin',  # Add the new admin cog
        'cogs.help'  # Add the new help cog
    ]
    
    # Load each cog
    for extension in cogs:
        try:
            await bot.load_extension(extension)
            logger.info(f"Loaded extension: {extension}")
        except Exception as e:
            logger.error(f"Failed to load extension {extension}:")
            logger.error(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for command errors."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Type `!help` for a list of commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have enough permissions to execute this command.")
    else:
        logger.error(f"Unhandled error in command {ctx.command}:")
        logger.error(traceback.format_exc())
        await ctx.send("An error occurred while executing the command.")

@bot.event
async def setup_hook():
    """Setup hook that gets called before the bot starts running."""
    await load_extensions()

async def main():
    """Main async function to start the bot."""
    # Check if token is available
    if not TOKEN:
        logger.critical("No bot token found in .env file. Please add your token.")
        return
    
    logger.info("Starting bot...")
    
    # Start the bot with the token
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main()) 