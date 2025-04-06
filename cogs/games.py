import discord
import random
import asyncio
import string
import logging
from discord.ext import commands
from discord import app_commands

# Configure logging
logger = logging.getLogger('discord_bot.games')

# Custom check for channel restrictions
def in_game_channel():
    """Check if the command is being used in an allowed game channel."""
    async def predicate(ctx):
        # Get allowed channels from bot config or use default
        if hasattr(ctx.bot, 'game_channels') and ctx.bot.game_channels:
            allowed_channels = ctx.bot.game_channels
        else:
            # If no channels are configured, store this channel as allowed
            if not hasattr(ctx.bot, 'game_channels'):
                ctx.bot.game_channels = []
            if ctx.channel.id not in ctx.bot.game_channels:
                ctx.bot.game_channels.append(ctx.channel.id)
            return True
        
        # Check if the current channel is in the allowed list
        if ctx.channel.id in allowed_channels:
            return True
        
        # If this is an admin, inform them
        if ctx.author.guild_permissions.administrator:
            channels_mention = ", ".join([f"<#{channel_id}>" for channel_id in allowed_channels])
            if not channels_mention:
                channels_mention = "No channels set yet. Use !setgamechannel command to set game channels."
            
            await ctx.send(
                f"❌ Games can only be played in designated channels: {channels_mention}\n"
                f"As an administrator, you can use `!setgamechannel` to add a new game channel.",
                delete_after=10
            )
        else:
            await ctx.send(
                "❌ Games can only be played in designated channels. Please use the appropriate channel.",
                delete_after=10
            )
        
        return False
    
    return commands.check(predicate)

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label=' ', row=y)
        self.x = x
        self.y = y
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToeView = self.view
        state = view.board[self.y][self.x]
        
        if state in (view.X, view.O):
            return
        
        if view.current_player == view.X:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = f"It is {view.player2.mention}'s turn (O)"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = f"It is {view.player1.mention}'s turn (X)"
        
        winner = view.check_winner()
        if winner is not None:
            if winner == view.X:
                content = f"{view.player1.mention} won!"
            elif winner == view.O:
                content = f"{view.player2.mention} won!"
            else:
                content = "It's a tie!"
            
            for child in view.children:
                child.disabled = True
            
            view.stop()
            
            # Schedule message deletion after 10 seconds
            if view.ctx:
                view.delete_after = True
        
        await interaction.response.edit_message(content=content, view=view)

class TicTacToeView(discord.ui.View):
    X = -1
    O = 1
    Tie = 2
    
    def __init__(self, player1, player2, ctx=None):
        super().__init__(timeout=600.0)  # 10 minute timeout
        self.current_player = self.X
        self.player1 = player1
        self.player2 = player2
        self.ctx = ctx
        self.message = None
        self.delete_after = False
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        
        # Add the buttons to the view
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(y, x))
    
    def check_winner(self):
        # Check rows
        for row in self.board:
            value = sum(row)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X
        
        # Check columns
        for col in range(3):
            value = self.board[0][col] + self.board[1][col] + self.board[2][col]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X
        
        # Check main diagonal
        value = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if value == 3:
            return self.O
        elif value == -3:
            return self.X
        
        # Check other diagonal
        value = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if value == 3:
            return self.O
        elif value == -3:
            return self.X
        
        # Check for a tie
        if all(self.board[i][j] != 0 for i in range(3) for j in range(3)):
            return self.Tie
        
        return None
    
    async def on_timeout(self):
        # Disable all buttons when the game times out
        for child in self.children:
            child.disabled = True
        
        try:
            await self.message.edit(content="Game timed out!", view=self)
            # Delete after timeout as well
            await asyncio.sleep(10)
            await self.message.delete()
        except:
            pass

class HangmanGame:
    def __init__(self):
        self.word_list = [
            "python", "javascript", "discord", "gaming", "computer", 
            "keyboard", "internet", "server", "developer", "algorithm",
            "function", "variable", "database", "network", "software",
            "hardware", "interface", "programming", "application", "security"
        ]
        self.max_attempts = 6
        self.games = {}  # Store active games by channel_id: {word, guessed, attempts}
    
    def start_game(self, channel_id):
        """Start a new game of hangman in the specified channel."""
        word = random.choice(self.word_list).lower()
        self.games[channel_id] = {
            'word': word,
            'guessed': set(),
            'attempts': self.max_attempts
        }
        return self.games[channel_id]
    
    def guess(self, channel_id, letter):
        """Process a guess for an active game."""
        if channel_id not in self.games:
            return None
        
        game = self.games[channel_id]
        letter = letter.lower()
        
        # Already guessed this letter
        if letter in game['guessed']:
            return {
                'already_guessed': True,
                'game': game
            }
        
        game['guessed'].add(letter)
        
        # Check if the letter is in the word
        if letter not in game['word']:
            game['attempts'] -= 1
        
        # Check for win/loss conditions
        status = self.get_game_status(channel_id)
        
        return {
            'already_guessed': False,
            'game': game,
            'status': status
        }
    
    def get_game_status(self, channel_id):
        """Check if the game is won, lost, or still in progress."""
        if channel_id not in self.games:
            return None
        
        game = self.games[channel_id]
        word = game['word']
        guessed = game['guessed']
        
        # The game is lost if no attempts remain
        if game['attempts'] <= 0:
            return 'lost'
        
        # The game is won if all letters in the word have been guessed
        if all(letter in guessed for letter in word):
            return 'won'
        
        # The game is still in progress
        return 'in_progress'
    
    def get_display_word(self, channel_id):
        """Get the current display representation of the word."""
        if channel_id not in self.games:
            return None
        
        game = self.games[channel_id]
        return ' '.join(letter if letter in game['guessed'] else '_' for letter in game['word'])
    
    def get_hangman_display(self, channel_id):
        """Get the ASCII art for the hangman."""
        if channel_id not in self.games:
            return None
        
        game = self.games[channel_id]
        stages = [
            """
```
  +---+
  |   |
      |
      |
      |
      |
========
```""",
            """
```
  +---+
  |   |
  O   |
      |
      |
      |
========
```""",
            """
```
  +---+
  |   |
  O   |
  |   |
      |
      |
========
```""",
            """
```
  +---+
  |   |
  O   |
 /|   |
      |
      |
========
```""",
            """
```
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
========
```""",
            """
```
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
========
```""",
            """
```
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
========
```"""
        ]
        
        return stages[self.max_attempts - game['attempts']]
    
    def end_game(self, channel_id):
        """End a game and return the final state."""
        if channel_id not in self.games:
            return None
        
        game = self.games[channel_id]
        del self.games[channel_id]
        return game

class Games(commands.Cog):
    """Mini-games for entertainment."""
    
    def __init__(self, bot):
        self.bot = bot
        self.hangman = HangmanGame()
        self.rps_games = {}  # Track active RPS games by user ID
        self.guess_games = {}  # Track active number guessing games by channel ID
    
    # Error handler for the cog
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle permission errors for game channel management commands."""
        if isinstance(error, commands.MissingPermissions):
            if ctx.command.name in ['setgamechannel', 'removegamechannel']:
                await ctx.send("❌ You need Administrator permission to manage game channels.", delete_after=10)
                return
        
        # Let other errors propagate to the global error handler
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            ctx.command_failed = True
    
    # Helper method to schedule message deletion
    async def delete_after_delay(self, message, delay=10):
        """Delete a message after the specified delay in seconds."""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except:
            pass  # Message may already be deleted or bot lacks permissions
    
    # Command to set a channel as a game channel
    @commands.command(name="setgamechannel")
    @commands.has_permissions(administrator=True)
    async def set_game_channel(self, ctx, channel: discord.TextChannel = None):
        """Set a channel as a designated game channel.
        
        Usage: !setgamechannel [#channel]
        Example: !setgamechannel #games
        If no channel is specified, the current channel will be used.
        Requires Administrator permission.
        """
        # Use the provided channel or the current one
        channel = channel or ctx.channel
        
        # Initialize game_channels list if it doesn't exist
        if not hasattr(self.bot, 'game_channels'):
            self.bot.game_channels = []
        
        # Add the channel if it's not already in the list
        if channel.id not in self.bot.game_channels:
            self.bot.game_channels.append(channel.id)
            await ctx.send(f"✅ {channel.mention} has been set as a game channel!")
        else:
            await ctx.send(f"ℹ️ {channel.mention} is already a game channel.")
    
    # Command to remove a game channel
    @commands.command(name="removegamechannel")
    @commands.has_permissions(administrator=True)
    async def remove_game_channel(self, ctx, channel: discord.TextChannel = None):
        """Remove a channel from the list of game channels.
        
        Usage: !removegamechannel [#channel]
        Example: !removegamechannel #games
        If no channel is specified, the current channel will be used.
        Requires Administrator permission.
        """
        # Use the provided channel or the current one
        channel = channel or ctx.channel
        
        # Check if game_channels exists and the channel is in it
        if hasattr(self.bot, 'game_channels') and channel.id in self.bot.game_channels:
            self.bot.game_channels.remove(channel.id)
            await ctx.send(f"✅ {channel.mention} has been removed from game channels!")
        else:
            await ctx.send(f"ℹ️ {channel.mention} is not a game channel.")
    
    # Command to list all game channels
    @commands.command(name="gamechannels")
    async def list_game_channels(self, ctx):
        """List all channels where games can be played.
        
        Usage: !gamechannels
        """
        if hasattr(self.bot, 'game_channels') and self.bot.game_channels:
            channels = "\n".join([f"• <#{channel_id}>" for channel_id in self.bot.game_channels])
            embed = discord.Embed(
                title="🎮 Game Channels",
                description=f"Games can be played in the following channels:\n{channels}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No game channels have been set. Games can be played in any channel.")
    
    # Rock-Paper-Scissors command
    @commands.command(name="rps")
    @in_game_channel()
    async def rock_paper_scissors(self, ctx):
        """Play Rock-Paper-Scissors with the bot.
        
        Usage: !rps
        """
        # Create the embedded message with buttons
        embed = discord.Embed(
            title="Rock, Paper, Scissors",
            description="Choose your move:",
            color=discord.Color.blue()
        )
        
        # Create a view with buttons for RPS choices
        view = discord.ui.View(timeout=30.0)
        
        # Add buttons for each choice
        for choice, emoji in [("Rock", "🪨"), ("Paper", "📄"), ("Scissors", "✂️")]:
            button = discord.ui.Button(label=choice, style=discord.ButtonStyle.primary, emoji=emoji)
            
            async def make_choice(interaction, choice=choice):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("This isn't your game!", ephemeral=True)
                    return
                
                # Bot makes a random choice
                bot_choice = random.choice(["Rock", "Paper", "Scissors"])
                
                # Determine the winner
                if choice == bot_choice:
                    result = "It's a tie!"
                    color = discord.Color.yellow()
                elif (choice == "Rock" and bot_choice == "Scissors") or \
                     (choice == "Paper" and bot_choice == "Rock") or \
                     (choice == "Scissors" and bot_choice == "Paper"):
                    result = f"You win! {choice} beats {bot_choice}."
                    color = discord.Color.green()
                else:
                    result = f"You lose! {bot_choice} beats {choice}."
                    color = discord.Color.red()
                
                # Create a result embed
                result_embed = discord.Embed(
                    title="Rock, Paper, Scissors - Result",
                    description=f"You chose: {choice}\nBot chose: {bot_choice}\n\n{result}",
                    color=color
                )
                
                # Disable all buttons
                for item in view.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=result_embed, view=view)
                
                # Schedule message deletion after 10 seconds
                self.bot.loop.create_task(self.delete_after_delay(interaction.message))
            
            button.callback = make_choice
            view.add_item(button)
        
        await ctx.send(embed=embed, view=view)
    
    # Tic-Tac-Toe command
    @commands.command(name="tictactoe", aliases=["ttt"])
    @in_game_channel()
    async def tic_tac_toe(self, ctx, opponent: discord.Member = None):
        """Play Tic-Tac-Toe with another user.
        
        Usage: !tictactoe @user
        Example: !tictactoe @SomeUser
        """
        if opponent is None:
            await ctx.send("❌ You need to specify an opponent!\nUsage: `!tictactoe @user`")
            return
        
        if opponent.id == ctx.author.id:
            await ctx.send("❌ You can't play against yourself!")
            return
        
        if opponent.bot:
            await ctx.send("❌ You can't play against a bot!")
            return
        
        # Create and send the game
        view = TicTacToeView(ctx.author, opponent, ctx)
        message = await ctx.send(f"Tic Tac Toe: {ctx.author.mention} (X) vs {opponent.mention} (O)\n"
                      f"It is {ctx.author.mention}'s turn (X)", view=view)
        view.message = message
        
        # Set up task to check for game end and delete message
        async def check_and_delete():
            await asyncio.sleep(1)  # Small initial delay
            while not view.is_finished():
                await asyncio.sleep(1)
            
            if view.delete_after:
                await asyncio.sleep(10)  # 10 second delay after game ends
                try:
                    await message.delete()
                except:
                    pass
        
        # Start the background task
        self.bot.loop.create_task(check_and_delete())
    
    # Number Guessing Game
    @commands.command(name="numguess", aliases=["ng"])
    @in_game_channel()
    async def number_guess(self, ctx, max_number: int = 100):
        """Start a number guessing game.
        
        Usage: !numguess [max_number]
        Example: !numguess 100
        """
        if max_number < 10:
            await ctx.send("❌ The maximum number must be at least 10!")
            return
        
        if max_number > 1000000:
            await ctx.send("❌ The maximum number must be less than 1,000,000!")
            return
        
        # Check if there's already a game in this channel
        if ctx.channel.id in self.guess_games:
            await ctx.send("❌ There's already a number guessing game running in this channel!")
            return
        
        # Generate a random number
        number = random.randint(1, max_number)
        attempts = 0
        max_attempts = max(5, int(max_number ** 0.5))  # Scale attempts with the max number
        
        # Store the game
        self.guess_games[ctx.channel.id] = {
            'number': number,
            'attempts': attempts,
            'max_attempts': max_attempts,
            'guesses': [],
            'messages': []  # Track messages for deletion
        }
        
        # Send the game instructions
        embed = discord.Embed(
            title="🔢 Number Guessing Game",
            description=f"I'm thinking of a number between 1 and {max_number}.\n"
                       f"You have {max_attempts} attempts to guess it.\n"
                       f"Type your guess as a number!",
            color=discord.Color.blue()
        )
        
        instruction_msg = await ctx.send(embed=embed)
        self.guess_games[ctx.channel.id]['messages'].append(instruction_msg)
        
        # Set up a check for valid guesses
        def check(message):
            # Must be in the same channel and not from a bot
            if message.channel.id != ctx.channel.id or message.author.bot:
                return False
            
            # Try to convert the content to an integer
            try:
                guess = int(message.content)
                return 1 <= guess <= max_number
            except ValueError:
                return False
        
        # Game loop
        game = self.guess_games[ctx.channel.id]
        while game['attempts'] < game['max_attempts']:
            try:
                # Wait for a valid guess
                guess_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                guess = int(guess_msg.content)
                game['attempts'] += 1
                game['guesses'].append(guess)
                
                # Check if the guess is correct
                if guess == game['number']:
                    embed = discord.Embed(
                        title="🎉 Correct!",
                        description=f"{guess_msg.author.mention} guessed the number {guess} correctly in "
                                  f"{game['attempts']} attempts!",
                        color=discord.Color.green()
                    )
                    result_msg = await ctx.send(embed=embed)
                    game['messages'].append(result_msg)
                    
                    # Schedule message deletion
                    for msg in game['messages']:
                        self.bot.loop.create_task(self.delete_after_delay(msg))
                    
                    del self.guess_games[ctx.channel.id]
                    return
                
                # Give a hint
                if guess < game['number']:
                    hint = "higher"
                else:
                    hint = "lower"
                
                embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"{guess_msg.author.mention} guessed {guess}.\n"
                              f"The number is {hint}.\n"
                              f"Attempts: {game['attempts']}/{game['max_attempts']}",
                    color=discord.Color.red()
                )
                hint_msg = await ctx.send(embed=embed)
                game['messages'].append(hint_msg)
            
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏱️ Timeout",
                    description=f"No valid guesses in 60 seconds. The number was {game['number']}.",
                    color=discord.Color.orange()
                )
                timeout_msg = await ctx.send(embed=embed)
                game['messages'].append(timeout_msg)
                
                # Schedule message deletion
                for msg in game['messages']:
                    self.bot.loop.create_task(self.delete_after_delay(msg))
                
                del self.guess_games[ctx.channel.id]
                return
        
        # If we get here, they've used all their attempts
        embed = discord.Embed(
            title="❌ Game Over",
            description=f"You've used all {game['max_attempts']} attempts.\n"
                      f"The number was {game['number']}.",
            color=discord.Color.red()
        )
        gameover_msg = await ctx.send(embed=embed)
        game['messages'].append(gameover_msg)
        
        # Schedule message deletion
        for msg in game['messages']:
            self.bot.loop.create_task(self.delete_after_delay(msg))
        
        del self.guess_games[ctx.channel.id]
    
    # Hangman Game
    @commands.command(name="hangman")
    @in_game_channel()
    async def hangman(self, ctx):
        """Start a game of Hangman.
        
        Usage: !hangman
        """
        # Check if there's already a game in this channel
        if ctx.channel.id in self.hangman.games:
            await ctx.send("❌ There's already a hangman game running in this channel!")
            return
        
        # Start a new game
        game = self.hangman.start_game(ctx.channel.id)
        display = self.hangman.get_display_word(ctx.channel.id)
        hangman_art = self.hangman.get_hangman_display(ctx.channel.id)
        
        # Create the initial embed
        embed = discord.Embed(
            title="🎮 Hangman",
            description=f"Guess the word by typing a letter!\n"
                      f"Word: `{display}`\n"
                      f"Attempts left: {game['attempts']}/{self.hangman.max_attempts}\n"
                      f"Guessed letters: None",
            color=discord.Color.blue()
        )
        embed.add_field(name="Hangman", value=hangman_art, inline=False)
        
        # Keep track of all game messages for deletion later
        game_messages = []
        initial_msg = await ctx.send(embed=embed)
        game_messages.append(initial_msg)
        
        # Set up a check for valid guesses
        def check(message):
            # Must be in the same channel and not from a bot
            if message.channel.id != ctx.channel.id or message.author.bot:
                return False
            
            # Check if it's a single letter
            content = message.content.strip().lower()
            return len(content) == 1 and content in string.ascii_lowercase
        
        # Game loop
        while ctx.channel.id in self.hangman.games:
            try:
                # Wait for a valid guess
                guess_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                letter = guess_msg.content.strip().lower()
                
                # Process the guess
                result = self.hangman.guess(ctx.channel.id, letter)
                
                if result['already_guessed']:
                    already_msg = await ctx.send(f"❌ {guess_msg.author.mention}, you already guessed the letter '{letter}'!")
                    game_messages.append(already_msg)
                    continue
                
                # Get updated game state
                game = result['game']
                display = self.hangman.get_display_word(ctx.channel.id)
                hangman_art = self.hangman.get_hangman_display(ctx.channel.id)
                guessed_letters = ', '.join(sorted(game['guessed'])) or "None"
                
                # Check game status
                if result['status'] == 'won':
                    embed = discord.Embed(
                        title="🎉 You Won!",
                        description=f"Congratulations, {guess_msg.author.mention}! You guessed the word: **{game['word']}**\n"
                                  f"Attempts left: {game['attempts']}/{self.hangman.max_attempts}\n"
                                  f"Guessed letters: {guessed_letters}",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Hangman", value=hangman_art, inline=False)
                    win_msg = await ctx.send(embed=embed)
                    game_messages.append(win_msg)
                    self.hangman.end_game(ctx.channel.id)
                    
                    # Schedule message deletion
                    for msg in game_messages:
                        self.bot.loop.create_task(self.delete_after_delay(msg))
                
                elif result['status'] == 'lost':
                    embed = discord.Embed(
                        title="❌ Game Over",
                        description=f"Sorry, you ran out of attempts! The word was: **{game['word']}**\n"
                                  f"Attempts left: 0/{self.hangman.max_attempts}\n"
                                  f"Guessed letters: {guessed_letters}",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Hangman", value=hangman_art, inline=False)
                    lose_msg = await ctx.send(embed=embed)
                    game_messages.append(lose_msg)
                    self.hangman.end_game(ctx.channel.id)
                    
                    # Schedule message deletion
                    for msg in game_messages:
                        self.bot.loop.create_task(self.delete_after_delay(msg))
                
                else:
                    # Game continues
                    embed = discord.Embed(
                        title="🎮 Hangman",
                        description=f"Word: `{display}`\n"
                                  f"Attempts left: {game['attempts']}/{self.hangman.max_attempts}\n"
                                  f"Guessed letters: {guessed_letters}",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Hangman", value=hangman_art, inline=False)
                    progress_msg = await ctx.send(embed=embed)
                    game_messages.append(progress_msg)
            
            except asyncio.TimeoutError:
                if ctx.channel.id in self.hangman.games:
                    game = self.hangman.games[ctx.channel.id]
                    embed = discord.Embed(
                        title="⏱️ Timeout",
                        description=f"No valid guesses in 60 seconds. The word was: **{game['word']}**.",
                        color=discord.Color.orange()
                    )
                    timeout_msg = await ctx.send(embed=embed)
                    game_messages.append(timeout_msg)
                    self.hangman.end_game(ctx.channel.id)
                    
                    # Schedule message deletion
                    for msg in game_messages:
                        self.bot.loop.create_task(self.delete_after_delay(msg))
    
    @commands.command(name="games")
    async def games_list(self, ctx):
        """Display a list of all available games and how to play them.
        
        Usage: !games
        """
        embed = discord.Embed(
            title="🎮 Available Games",
            description="Here are all the games you can play with the bot:",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎲 Rock Paper Scissors (`!rps`)",
            value="Play Rock-Paper-Scissors against the bot. Simply type `!rps rock`, `!rps paper`, or `!rps scissors`.",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Tic-Tac-Toe (`!tictactoe`)",
            value="Challenge another member to a game of Tic-Tac-Toe. Usage: `!tictactoe @user`",
            inline=False
        )
        
        embed.add_field(
            name="🔢 Number Guessing (`!numguess`)",
            value="Guess a number between 1 and a maximum value. Usage: `!numguess [max_number]` (default max: 100)",
            inline=False
        )
        
        embed.add_field(
            name="📝 Hangman (`!hangman`)",
            value="Play a game of Hangman with the bot. Usage: `!hangman` to start, then guess letters by typing a single letter",
            inline=False
        )
        
        # Show !gamechannels command
        embed.add_field(
            name="📋 Game Channels (`!gamechannels`)",
            value="Check which channels are designated for games. Usage: `!gamechannels`",
            inline=False
        )
        
        # Show admin reference for admins
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Commands",
                value="Type `!admin` to see all administrative commands, including game channel management.",
                inline=False
            )
        
        embed.set_footer(text="Games can only be played in designated game channels")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the Games cog to the bot."""
    await bot.add_cog(Games(bot)) 