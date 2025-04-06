# Discord Bot

A feature-rich Discord bot with modular functionality.

## Features

### Command Lists
* `!games` - Display a list of all available games
* `!fun` - Display a list of all available fun commands
* `!music` - Display a list of all available music commands
* `!mod` - Display a list of all available moderation commands
* `!economy` - Display a list of all available economy commands
* `!admin` - Display all administrative commands (Admin only)

### Fun Commands
* `!8ball <question>` - Ask the Magic 8-Ball a question
* `!truth` - Get a random truth question
* `!dare` - Get a random dare challenge
* `!meme` - Get a random meme from Reddit
* `!joke` - Get a random joke
* `!roast @user` - Roast the mentioned user

### Games
* `!rps` - Play Rock-Paper-Scissors with the bot
* `!tictactoe @user` - Play Tic-Tac-Toe with another user
* `!numguess [max_number]` - Start a number guessing game (default max: 100)
* `!hangman` - Play a game of Hangman
* `!gamechannels` - List all channels where games can be played

### Economy System
* `!balance [user]` - Check your coin balance or someone else's
* `!daily` - Claim your daily reward of coins (resets every 24 hours)
* `!work` - Work to earn some coins (available once per hour)
* `!give <user> <amount>` - Give coins to another user
* `!gamble <amount>` - Gamble your coins for a chance to win more
* `!leaderboard` - Display the richest users in the server
* `!shop` - Browse items available for purchase with coins
* `!buy <item_id>` - Purchase an item from the shop
* `!inventory [user]` - View your inventory or someone else's

### Economy Channel Management
* `!seteconomychannel [#channel]` - Set a channel for economy commands (Admin only)
* `!removeeconomychannel` - Remove the economy channel restriction (Admin only)

### Counting Game
* `!countsetup #channel` - Set up a counting channel (Admin only)
* `!countreset` - Reset the count in the counting channel (Admin only)
* `!countstrict [on/off]` - Toggle strict mode (one user can't count twice in a row) (Admin only)
* `!countfail [message/restart/continue]` - Set what happens when someone breaks the count (Admin only)

### Giveaways
* `!gstart <time> <winners> <prize>` - Start a new giveaway (Admin only)
* `!gend <message_id>` - End a giveaway early (Admin only)
* `!greroll <message_id>` - Reroll the winners of a giveaway (Admin only)

### Announcements
* `!announce #channel <message>` - Send an announcement to a channel (Admin only)
* `!poll #channel <question> | <option1> | <option2> [| <option3>...]` - Create a poll (Admin only)
* `!msg #channel <message>` - Make the bot send a message to a specific channel (Admin only)

### Self-Roles
* `!selfroles create <title> | <description>` - Create a new self-role message (Admin only)
* `!selfroles add <message_id> <emoji> <role>` - Add a role to a self-role message (Admin only)
* `!selfroles remove <message_id> <emoji>` - Remove a role from a self-role message (Admin only)
* `!selfroles list` - List all self-role messages (Admin only)
* `!selfroles clear <message_id>` - Remove all roles from a message (Admin only)
* `!selfroles delete <message_id>` - Delete a self-role message completely (Admin only)

### Music Commands
* `!play <song>` - Play a song from YouTube
* `!pause` - Pause the current song
* `!resume` - Resume playback
* `!skip` - Skip to the next song
* `!stop` - Stop playback and clear the queue
* `!queue` - Show the current queue
* `!volume <0-100>` - Set the volume

### Music Channel Management
* `!setmusicchannel [#channel]` - Set a channel for music commands (Admin only)
* `!removemusicchannel` - Remove the music channel restriction (Admin only)

### Moderation
* `!kick @user [reason]` - Kick a user from the server
* `!ban @user [reason]` - Ban a user from the server
* `!unban <user_id>` - Unban a user
* `!mute @user <time> [reason]` - Temporarily mute a user
* `!clear <amount>` - Clear a specified number of messages

### Game Channel Management
* `!setgamechannel [#channel]` - Set a channel for games and fun commands (Admin only)
* `!removegamechannel [#channel]` - Remove a channel from game channels (Admin only)

### Admin Commands
All administrative commands have been centralized under the `!admin` command. Only users with Administrator permissions can access these commands.

#### Economy Administration
* `!seteconomychannel [#channel]` - Set a channel for economy commands
* `!removeeconomychannel` - Remove the economy channel restriction
* `!addcoins <user> <amount>` - Add coins to a user's balance
* `!removecoins <user> <amount>` - Remove coins from a user's balance
* `!setcoins <user> <amount>` - Set a user's coin balance to a specific amount
* `!giveall <amount>` - Give coins to all members in the server

#### Channel Management
* `!setmusicchannel [#channel]` - Set a channel for music commands
* `!removemusicchannel` - Remove the music channel restriction
* `!setgamechannel [#channel]` - Set a channel for games and fun commands
* `!removegamechannel [#channel]` - Remove a channel from game channels

#### Giveaways
* `!gstart <time> <winners> <prize>` - Start a new giveaway
* `!gend <message_id>` - End a giveaway early
* `!greroll <message_id>` - Reroll the winners of a giveaway

#### Announcements
* `!announce #channel <message>` - Send an announcement to a channel
* `!poll #channel <question> | <option1> | <option2> [| <option3>...]` - Create a poll
* `!msg #channel <message>` - Make the bot send a message to a specific channel

#### Counting Game
* `!countsetup #channel` - Set up a counting channel
* `!countreset` - Reset the count in the counting channel
* `!countstrict [on/off]` - Toggle strict mode (one user can't count twice in a row)
* `!countfail [message/restart/continue]` - Set what happens when someone breaks the count

#### Self-Roles Management
* `!selfroles create <title> | <description>` - Create a new self-role message
* `!selfroles add <message_id> <emoji> <role>` - Add a role to a self-role message
* `!selfroles remove <message_id> <emoji>` - Remove a role from a self-role message
* `!selfroles list` - List all self-role messages
* `!selfroles clear <message_id>` - Clear roles from a message
* `!selfroles delete <message_id>` - Delete a self-role message completely

## Setup

### Requirements
- Python 3.8 or higher
- discord.py library
- FFmpeg (for music commands)

### Installation
1. Clone this repository
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add your bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   ```
4. Run the bot:
   ```
   python bot.py
   ```

## Hosting the Bot

### Hosting on Replit
1. Create a new Replit project and import your bot code
2. Make sure the `.replit` file is included in your project
3. Set up environment secrets:
   - Click on "Secrets" in the left sidebar
   - Add `BOT_TOKEN` with your Discord bot token as the value
4. Click "Run" and your bot should start

### Hosting on Railway
1. Create a new project on Railway
2. Connect your GitHub repository with the bot code
3. Railway will automatically detect the Procfile and use our start.sh script
4. Add the following environment variables:
   - `BOT_TOKEN` with your Discord bot token as the value
5. Deploy the bot

Railway will automatically install FFmpeg during the startup process using the start.sh script.

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License. 