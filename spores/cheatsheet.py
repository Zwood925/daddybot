import discord
from discord.ext import commands

class CheatSheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # The 'aliases' list means all of these words trigger the exact same command!
    @commands.command(aliases=['commands', 'guide', 'helpme'])
    async def cheatsheet(self, ctx):
        guide = (
            "📖 **DADDYBOT COMMAND CHEAT SHEET** 📖\n\n"
            "**📚 THE LIBRARY**\n"
            "`!read [book title]` - Log a finished book and rate it\n"
            "`!stats` - Shows the family books read scorecard\n"
            "`!book_rec [book title]` - Get a few book recommendations based on a title\n\n"

            "**📦 THE INVENTORY MATRIX**\n"
            "`!box add [box_id]` - Register a new physical tote (e.g., !box add GREEN-4)\n"
            "`!box stash [box_id] [item]` - Put an item inside a box\n"
            "`!box locate [box_id]` - See exactly what is inside a specific box\n"
            "`!box remove [box_id] [item]` - Take an item out of a box\n"
            "`!box delete [box_id]` - Burn a box and wipe it from the matrix\n"
            "`!find [item]` - Search the entire house for a specific item\n\n"
            
            "**🎬 THE FAMILY FILTER** *(Coming Soon)*\n"
            "`!movie [title]` - Ask the AI if a movie is safe for the kids\n"
        )
        
        await ctx.send(guide)

async def setup(bot):
    await bot.add_cog(CheatSheet(bot))