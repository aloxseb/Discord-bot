import discord
import random
import aiohttp
import logging
from discord.ext import commands

# Configure logging
logger = logging.getLogger('discord_bot.fun')

# Import the in_game_channel check from the games cog
from cogs.games import in_game_channel

class Fun(commands.Cog):
    """Fun commands for entertainment."""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        
        # 8Ball responses
        self.responses = [
            # Positive responses
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes – definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            # Neutral responses
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            # Negative responses
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        
        # Truth questions
        self.truths = [
            "What's the most embarrassing thing you've ever done?",
            "What's a secret you've never told anyone?",
            "What's your biggest fear?",
            "What's the most childish thing you still do?",
            "What's the biggest mistake you've ever made?",
            "What's a lie you've told that got you in trouble?",
            "What's the worst thing you've ever done?",
            "What's the strangest dream you've had?",
            "What's your guilty pleasure?",
            "What's the dumbest thing you've done in front of a crowd?",
            "What's something you're afraid to tell your parents?",
            "What's the strangest place you've fallen asleep?",
            "What's your most embarrassing childhood memory?",
            "What's the weirdest thing you've done when alone?",
            "What's a weird food combination you enjoy?",
            "If you had to date someone in this server, who would it be?",
            "What's the longest you've gone without showering?",
            "What's the most embarrassing thing in your search history?",
            "What's the most embarrassing song on your playlist?",
            "Have you ever pretended to be sick to get out of something?"
        ]
        
        # Dare challenges
        self.dares = [
            "Send a screenshot of your most recent DMs.",
            "Text someone you haven't talked to in at least 6 months.",
            "Send the most unflattering selfie you have.",
            "Call someone and sing them Happy Birthday, even if it's not their birthday.",
            "Send your most recent emoji as a reaction to the next 5 messages.",
            "Send a voice message singing your favorite song.",
            "Text your crush and tell them you like their hair.",
            "Change your profile picture to whatever the group chooses for 24 hours.",
            "Make up a short song about the person above you in the chat.",
            "Send a message in all capital letters for the next hour.",
            "Do 10 push-ups right now.",
            "Record yourself telling a dad joke in the most serious voice.",
            "Send a message to the 3rd person in your contact list asking for a strange favor.",
            "Put your status as 'I love [name of someone in the server]' for 1 hour.",
            "Send a DM to someone random saying 'I know what you did'.",
            "Take a selfie with a random household object on your head.",
            "Type with your elbows for the next 5 minutes.",
            "Send a screenshot of your camera roll.",
            "Send your best pickup line to the last person you texted.",
            "Start all your sentences with the letter Z for the next 10 minutes."
        ]
        
        # Roasts (clean and funny)
        self.roasts = [
            "I'd roast you, but my mom said I'm not allowed to burn trash.",
            "You're the reason the gene pool needs a lifeguard.",
            "If I wanted to kill myself, I'd climb up to your ego and jump down to your IQ.",
            "You must have been born on a highway because that's where most accidents happen.",
            "I'm jealous of people who don't know you.",
            "You're not completely useless, you can always serve as a bad example.",
            "I'd agree with you but then we'd both be wrong.",
            "You're like a cloud. When you disappear, it's a beautiful day.",
            "I'd tell you to go outside, but that would just make everyone else's day worse.",
            "You have an entire life to be stupid. Why not take today off?",
            "I'm not saying I hate you, but I would unplug your life support to charge my phone.",
            "You're the human equivalent of a participation award.",
            "I'm sorry I hurt your feelings when I called you stupid. I thought you already knew.",
            "Your face makes onions cry.",
            "You're so dense, light bends around you.",
            "I'd explain it to you, but I don't have any crayons with me.",
            "If you were any less intelligent, we'd have to water you twice a week.",
            "You're not pretty enough to have such an ugly personality.",
            "Keep rolling your eyes. Maybe you'll find a brain back there.",
            "You're about as useful as a screen door on a submarine."
        ]
    
    async def cog_load(self):
        """Initialize aiohttp session when cog is loaded."""
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """Clean up aiohttp session when cog is unloaded."""
        if self.session:
            await self.session.close()
            self.session = None
    
    @commands.command(name="fun")
    async def fun_list(self, ctx):
        """Display a list of all available fun commands.
        
        Usage: !fun
        """
        embed = discord.Embed(
            title="🎡 Fun Commands",
            description="Here are all the fun commands you can use:",
            color=discord.Color.magenta()
        )
        
        embed.add_field(
            name="🎱 Magic 8-Ball (`!8ball`)",
            value="Ask the Magic 8-Ball a question. Usage: `!8ball <question>`",
            inline=False
        )
        
        embed.add_field(
            name="🔎 Truth (`!truth`)",
            value="Get a random truth question for truth or dare games.",
            inline=False
        )
        
        embed.add_field(
            name="🔥 Dare (`!dare`)",
            value="Get a random dare challenge for truth or dare games.",
            inline=False
        )
        
        embed.add_field(
            name="😂 Memes (`!meme`)",
            value="Get a random meme from Reddit.",
            inline=False
        )
        
        embed.add_field(
            name="😄 Jokes (`!joke`)",
            value="Get a random joke to brighten your day.",
            inline=False
        )
        
        embed.add_field(
            name="🔥 Roast (`!roast`)",
            value="Roast someone with a funny insult. Usage: `!roast @user`",
            inline=False
        )
        
        # Show admin reference for admins
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Commands",
                value="Type `!admin` to see all administrative commands, including game channel management.",
                inline=False
            )
        
        embed.set_footer(text="Fun commands can only be used in designated channels")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="8ball")
    @in_game_channel()
    async def eight_ball(self, ctx, *, question=None):
        """Ask the Magic 8 Ball a question.
        
        Usage: !8ball <question>
        Example: !8ball Will I win the lottery?
        """
        if not question:
            await ctx.send("❌ You need to ask a question!\nUsage: `!8ball <question>`")
            return
        
        # Create an embed for the response
        embed = discord.Embed(title="🎱 Magic 8 Ball", color=discord.Color.blue())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(self.responses), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="truth")
    @in_game_channel()
    async def truth(self, ctx):
        """Get a random truth question.
        
        Usage: !truth
        """
        # Create an embed for the response
        embed = discord.Embed(
            title="🔎 Truth",
            description=random.choice(self.truths),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dare")
    @in_game_channel()
    async def dare(self, ctx):
        """Get a random dare challenge.
        
        Usage: !dare
        """
        # Create an embed for the response
        embed = discord.Embed(
            title="🔥 Dare",
            description=random.choice(self.dares),
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="meme")
    @in_game_channel()
    async def meme(self, ctx):
        """Fetch a random meme from Reddit.
        
        Usage: !meme
        """
        # Show typing indicator while fetching meme
        async with ctx.typing():
            try:
                # Fetch meme from Reddit API (r/memes)
                async with self.session.get('https://meme-api.com/gimme') as response:
                    if response.status != 200:
                        await ctx.send("❌ Failed to fetch a meme. Try again later.")
                        return
                    
                    data = await response.json()
                    
                    # Create an embed for the meme
                    embed = discord.Embed(
                        title=data['title'],
                        url=data['postLink'],
                        color=discord.Color.orange()
                    )
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"From r/{data['subreddit']} | 👍 {data['ups']}")
                    
                    await ctx.send(embed=embed)
            
            except Exception as e:
                logger.error(f"Error fetching meme: {str(e)}")
                await ctx.send("❌ An error occurred while fetching a meme. Try again later.")
    
    @commands.command(name="joke")
    @in_game_channel()
    async def joke(self, ctx):
        """Get a random joke.
        
        Usage: !joke
        """
        # Show typing indicator while fetching joke
        async with ctx.typing():
            try:
                # Fetch joke from JokeAPI (clean, safe jokes only)
                url = 'https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&type=single'
                
                async with self.session.get(url) as response:
                    if response.status != 200:
                        await ctx.send("❌ Failed to fetch a joke. Try again later.")
                        return
                    
                    data = await response.json()
                    
                    # Create an embed for the joke
                    embed = discord.Embed(
                        title="😂 Random Joke",
                        description=data['joke'] if 'joke' in data else f"{data['setup']}\n\n{data['delivery']}",
                        color=discord.Color.purple()
                    )
                    
                    await ctx.send(embed=embed)
            
            except Exception as e:
                logger.error(f"Error fetching joke: {str(e)}")
                await ctx.send("❌ An error occurred while fetching a joke. Try again later.")
    
    @commands.command(name="roast")
    @in_game_channel()
    async def roast(self, ctx, user: discord.Member = None):
        """Roast a user with a funny insult.
        
        Usage: !roast @user
        Example: !roast @John
        """
        if user is None:
            await ctx.send("❌ You need to specify a user to roast!\nUsage: `!roast @user`")
            return
        
        # Don't roast the bot
        if user.id == self.bot.user.id:
            await ctx.send("Nice try, but I'm not going to roast myself! 😎")
            return
        
        # Create an embed for the roast
        embed = discord.Embed(
            title=f"🔥 Roasting {user.display_name}",
            description=random.choice(self.roasts),
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the Fun cog to the bot."""
    await bot.add_cog(Fun(bot)) 