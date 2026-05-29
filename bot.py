import discord # pyright: ignore[reportMissingImports]
from discord.ext import commands # pyright: ignore[reportMissingImports]
import aiohttp
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

conn = sqlite3.connect("daddybot_memory.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS read_books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_title TEXT UNIQUE
    )
""")
conn.commit()

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and listening!")
    print("========================")

@bot.command()
async def ping(ctx):
    print(f"received ping from {ctx.author.name}")
    await ctx.send("Pong, Daddy! It works!")

@bot.command()
async def weather(ctx, *, city: str):
    api_key = os.getenv("WEATHER_API_KEY")

    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=3"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:

            if response.status == 200:
                data = await response.json()

                temp = data['current']['temp_f']
                humidity = data['current']['humidity']
                condition = data['current']['condition']['text'].lower()
                actual_city_name = data['location']['name']

                report = f"** 3-day forecast for {actual_city_name}**\n\n"

                for day_in_matrix in data['forecast']['forecastday']:

                    date = day_in_matrix['date']
                    max_temp = day_in_matrix['day']['maxtemp_f']
                    min_temp = day_in_matrix['day']['mintemp_f']
                    chance_of_rain = day_in_matrix['day']['daily_chance_of_rain']
                    forecast_condition = day_in_matrix['day']['condition']['text']

                    report += f":calendar: **{date}:** {forecast_condition} | :hotsprings: **{max_temp}°F** | :snowflake: **{min_temp}°F** | :cloud_with_rain: **{chance_of_rain}%**\n"
 
                await ctx.send(report)

            else:
                await ctx.send(f"{city} doesn't actually exist bro.")
@bot.command()
async def read(ctx, *, book_title: str):
    conn = sqlite3.connect("daddybot_memory.db")
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO read_books (book_title) VALUES (?)", (book_title.lower(),))
        conn.commit()
        await ctx.send(f"Added **{book_title}** to my memory of books you've read! I won't forget.")

    except sqlite3.IntegrityError:
        await ctx.send(f"You've already read **{book_title}**!")
    
    finally:
        conn.close()



@bot.command()
async def book_rec(ctx, *, book_title: str):

    await ctx.send(f"A cute librarian is headed to the stack to look for things similar to **{book_title}**")
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3.1:8b",
        "prompt": (
            f"You are an elite, well-read librarian. The user absolutely loves the book or series '{book_title}'. "
            f"Provide exactly 5 highly accurate book or book-series recommendations that match that exact vibe, energy, or genre. "
            f"For each recommendation, provide the Title, Author, and a 1-sentence punchy explanation of why they will love it. "
            f"Do not include an introductory greeting or an outro sentence. Just give the list."
        ),
        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                ai_recommendations = data.get('response', 'My brain glitched. Try again.')
                await ctx.send(ai_recommendations)
            else:
                await ctx.send(f"I don't see anything like **{book_title}** in my library....What's something else you like that I can give recommendations off of?")


bot.run(os.getenv("DISCORD_TOKEN"))

