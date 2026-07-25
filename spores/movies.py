import discord
from discord.ext import commands
import aiohttp
import json

class FamilyFilter(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

        self.system_prompt="""
    You are a highly protective AI media filter for the Wood family.

        Evaluate the requested movie based on these rules:

        1. Potty humor and slapstick violence are OK.

        2. Glorifying Demonic, occult, or dark magic themes are not cool.

        3. We operate from a Christian worldview but are not crazy stuck up.

        4. We don't like blatant agendas being pushed through kid's movies.


        A list of movies that we are ok with include;

        Gaurdians of the Galaxy, Despicable Me, Luca, and Goat. (We are not opposed to some violence or stupid potty humor, or even mild profanity)


        Movies we have said no to;

        Minions and Monsters (the whole premise of summoning and playing with a demon)

        Stranger things (season one was ok, but it got way too intense with the violence and sexual stuff for kids)

               

        Give a brief summary, list potential triggers, and give a final PASS/FAIL.

        """  
    @commands.command()
    async def movie(self, ctx, *, title: str):

        await ctx.send(f"Let me check {title} and see if it's good for the Wood family!")

        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.1:8b",
            "prompt": f"{self.system_prompt}\n\nMovie to evaluate: {title}\n",
            "stream": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_review = data.get('response')

                    if len(ai_review) > 2000:
                        for i in range(0, len(ai_review), 1900):
                            await ctx.send(ai_review[i:i+1900])
                    else:
                        await ctx.send(ai_review)
                else:
                    await ctx.send(f"I'm having some issues right now.....We all have issues. I'm not apologizing. Shut up.")

async def setup(bot):
    await bot.add_cog(FamilyFilter(bot))
