import discord # pyright: ignore[reportMissingImports]
from discord.ext import commands # pyright: ignore[reportMissingImports]
import sqlite3
import asyncio

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def box(self, ctx):
        await ctx.send("📦 **Inventory Matrix**\nUse `!box add [box_id]` to register a new tote, or `!box locate [box_id]` to find one.")

    @box.command()
    async def add(self, ctx, box_id: str):
        box_id = box.id.capitalize()

        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO boxes (box_id) VALUES (?)", (box_id,))
            conn.commit()
            await ctx.send(f"Added box **{box_id}** to the inventory matrix.") 

        except sqlite3.IntegrityError:
            await ctx.send(f"Box **{box_id}** already exists in the inventory matrix. Use '!box edit' if you want to change it!")
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(Inventory(bot))
        