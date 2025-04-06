import os
import logging
import json
import discord
import aiohttp
import random
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Default to Gemini API if no API URL is provided
AI_API_URL = os.getenv('AI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent')
# Add a Gemini API key (needs to be set in .env)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Configure logging
logger = logging.getLogger('discord_bot.ai')

class AI(commands.Cog):
    """Cog for AI-powered chat functionality in Manglish."""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.use_api = True  # Toggle for API vs local response
    
    async def cog_load(self):
        """Initialize aiohttp session when cog is loaded."""
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """Clean up aiohttp session when cog is unloaded."""
        if self.session:
            await self.session.close()
            self.session = None
    
    @commands.command(name="ai")
    async def ai_command(self, ctx, *, message=None):
        """
        Get an AI-generated response in Manglish (Malayalam + English).
        
        Usage: !ai <your message here>
        Example: !ai how are you?
        """
        # Check if message is provided
        if not message:
            await ctx.send("Eda, entha chodhikkande? Please type something after !ai.")
            return
        
        # Show typing indicator
        async with ctx.typing():
            try:
                # Try to get an API response if enabled
                if self.use_api:
                    try:
                        response = await self.get_api_response(message)
                    except Exception as e:
                        logger.error(f"API error, falling back to local: {str(e)}")
                        response = self.generate_local_manglish(message)
                else:
                    # Use local generation
                    response = self.generate_local_manglish(message)
                
                await ctx.send(response)
            except Exception as e:
                logger.error(f"Error getting response: {str(e)}")
                await ctx.send("Sorry, I couldn't get a response. Try again later!")
    
    async def get_api_response(self, message):
        """Get AI response from an external API."""
        system_instruction = "You are a friendly assistant who always responds in Manglish (Malayalam + English mix). Your tone is natural, friendly and sometimes funny. Use Malayalam words and phrases mixed with English in a way that's commonly spoken in Kerala. Don't translate word-by-word but respond naturally, as someone would speak in a conversation."
        
        # Check which API we're using
        if "googleapis.com" in AI_API_URL:
            # Google Gemini API
            url = f"{AI_API_URL}?key={GEMINI_API_KEY}"
            
            # Construct the Google Gemini payload
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": message
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "parts": [
                        {
                            "text": system_instruction
                        }
                    ]
                },
                "generationConfig": {
                    "temperature": 0.7,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 200
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Send request to the API
            async with self.session.post(
                url,
                json=payload,
                headers=headers
            ) as response:
                # Check if the request was successful
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API error: {response.status}, {error_text}")
                    logger.error(f"Request URL: {url}")
                    logger.error(f"Request payload: {json.dumps(payload)}")
                    raise Exception(f"API error: {response.status}")
                
                # Parse the response
                response_text = await response.text()
                data = json.loads(response_text)
                
                # Extract the Gemini response
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            return parts[0]["text"].strip()
                    
                    # If we can't extract the response properly
                    raise Exception("Failed to parse Gemini response")
                else:
                    raise Exception("No candidates in Gemini response")
                    
        elif "huggingface.co" in AI_API_URL:
            # HuggingFace API handling (same as before)
            # Add your HuggingFace code here
            raise Exception("HuggingFace API not implemented")
        else:
            # Fallback API handling
            raise Exception("Unsupported API URL")

    def generate_local_manglish(self, message):
        """Generate a Manglish response locally without using external APIs."""
        # Simple responses for common questions
        message = message.lower()
        
        greetings = ["hello", "hi", "hey", "halo", "greetings", "welcome"]
        if any(greeting in message for greeting in greetings):
            responses = [
                "Hai mone! Sugam aano?", 
                "Hello machane! Enthokke und?",
                "Eda! Sugalle?",
                "Hai hai! Enthu vishesham?",
                "Enna mwone, engane irikkunu?"
            ]
            return random.choice(responses)
        
        if "how are you" in message:
            responses = [
                "Njan adipoli aanu, mone! Ninakko?",
                "Njan kollam. Nee engane und?",
                "Pwoli mood aanu machane!",
                "Njan super aanu! Ninne pole!",
                "Enik oru kuzhappavum illa. Chill aanu!"
            ]
            return random.choice(responses)
        
        if "help" in message:
            return "Enthaa help venel? Njan ithuvare ready aanu mone!"
        
        if "thank" in message:
            responses = [
                "Athinenthu thanks machane! No mention!",
                "Welcome mone! Ennum varuo!",
                "Santhosham aayi!",
                "Ath oru cheriya karyam alle! Welcome!"
            ]
            return random.choice(responses)
            
        # For other queries, generate a generic response
        generic_responses = [
            "Athu sheriyaanu mone! Pinne engane?",
            "Adipoli! Njan angane thanne vicharichhu!",
            "Sherikkum? Athokke kollam!",
            "Machane, athu njan arinjirunnilla!",
            "Eda, athu enthu sambhavam aanu?",
            "Kollam! Njan kure naal aayi athu aalochikkunnu.",
            "Enthinaa ithra tension? Chill aaku mone!",
            "Aaha! Athokke pwoli idea aanu!",
            "Njan ariyilla mone, pakshe sounds interesting!"
        ]
        
        return random.choice(generic_responses)

    @commands.command(name="toggle_api")
    @commands.has_permissions(administrator=True)
    async def toggle_api(self, ctx):
        """Toggle between API and local response (admin only)"""
        self.use_api = not self.use_api
        mode = "API" if self.use_api else "local"
        await ctx.send(f"Switched to {mode} response mode.")

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(AI(bot)) 