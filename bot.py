import discord # pyright: ignore[reportMissingImports]
from discord.ext import commands # pyright: ignore[reportMissingImports]
import os
from dotenv import load_dotenv
import sqlite3
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def load_extensions():
    for filename in os.listdir("./spores"):
        if filename.endswith(".py"):
            await bot.load_extension(f"spores.{filename[:-3]}")

async def setup_hook():
    await load_extensions()

bot.setup_hook = setup_hook

conn = sqlite3.connect("daddybot_memory.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS read_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT,
        author TEXT,
        book_title TEXT,
        rating INTEGER,
        what_i_liked TEXT,
        UNIQUE(user_name, book_title)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS boxes (
        box_id TEXT PRIMARY KEY,
        color_code TEXT,
        container_type TEXT,
        theme TEXT,
        location TEXT,
        status TEXT,
               
    )
""")       

cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        box_id TEXT,
        FOREIGN KEY(box_id) REFERENCES boxes(box_id)
    )
""")


conn.commit()
conn.close()

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and listening!")
    print("========================")


bot.run(os.getenv("DISCORD_TOKEN"))

