import discord # pyright: ignore[reportMissingImports]
from discord.ext import commands # pyright: ignore[reportMissingImports]
import aiohttp
import os
from dotenv import load_dotenv
import sqlite3
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

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
    current_user = ctx.author.name
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    conn = sqlite3.connect("daddybot_memory.db")
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO read_books (user_name, book_title) VALUES (?, ?)", (current_user, book_title.lower(),))
        conn.commit()
        await ctx.send(f"Added **{book_title}** to my memory of books you've read! I won't forget.")
        await ctx.send("Who is the author? (Or Skip to leave blank)")

        try:
            msg = await bot.wait_for('message', check=check, timeout=60.0)

            if msg.content.lower() == 'skip':
                author = None
            else:
                author = msg.content

            await ctx.send("How many stars would you give it? (1-5, or Skip)")
            msg = await bot.wait_for('message', check=check, timeout=60.0)

            if msg.content.lower() == 'skip':
                rating = None
            else:
                rating = msg.content

            await ctx.send("What series is this a part of? (Or Skip to leave blank)")
            msg = await bot.wait_for('message', check=check, timeout=60.0)

            if msg.content.lower() == 'skip':
                series = None
            else:
                series = msg.content

            await ctx.send("What did you like about it? (Or Skip to leave blank)")
            msg = await bot.wait_for('message', check=check, timeout=120.0)

            if msg.content.lower() == 'skip':
                what_i_liked = None
            else:
                what_i_liked = msg.content

            cursor.execute("""
                UPDATE read_books
                SET author = ?, rating = ?, what_i_liked = ?, series = ?
                WHERE user_name = ? AND book_title = ?
            """, (author, rating, what_i_liked, series, current_user, book_title.lower()))

            conn.commit()
            await ctx.send(f"Awesome! I've updated **{book_title}** with all the details in the vault.")

        except asyncio.TimeoutError:
            await ctx.send("You took too long. We'll just leave the rest blank for now.")
            return

    except sqlite3.IntegrityError:
        await ctx.send(f"You've already read **{book_title}**!")
    
    finally:
        conn.close()

@bot.command()
async def stats(ctx):
    conn = sqlite3.connect("daddybot_memory.db")
    cursor = conn.cursor()

    try:
        # Count each user books
        cursor.execute("SELECT COUNT(*) FROM read_books WHERE user_name = 'zwood925'")
        zwood_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM read_books WHERE user_name = 'swood_38102'")
        kittykat_count = cursor.fetchone()[0]

        total_books = zwood_count + kittykat_count

        # send scoreboard to Discord
        await ctx.send(
            f"**THE VAULT SCOREBOARD**\n\n"
            f"**Daddy** has read {zwood_count} books.\n"
            f"**KittyKat** has read {kittykat_count} books.\n"
            f"**Total** books in the vault: {total_books}"  
        )

    finally:
        conn.close()


@bot.command()
async def book_rec(ctx, *, book_title: str):

    await ctx.send(f"A cute librarian is headed to the stack to look for things similar to **{book_title}**")

    conn = sqlite3.connect("daddybot_memory.db")
    cursor = conn.cursor()

    try:
        current_user = ctx.author.name
        partner_user = 'swood_38102' if current_user == 'zwood925' else 'zwood925'

        cursor.execute("SELECT book_title FROM read_books WHERE user_name = ?", (current_user,))
        user_books = [row[0] for row in cursor.fetchall()]
        avoid_list = ", ".join(user_books) if user_books else "None"

        cursor.execute("SELECT book_title FROM read_books WHERE user_name = ?", (partner_user,))
        partner_books = [row[0] for row in cursor.fetchall()]
        priority_list = ", ".join(partner_books) if partner_books else "None"

    finally:
        conn.close()

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3.1:8b",
        "prompt": (
            f"You are an elite, well-read librarian. The user wants book recommendations based on the vibe, energy, and genre of '{book_title}'.\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"1. DO NOT recommend any of these books, because the user has already read them: {avoid_list}\n"
            f"2. HIGHLY CONSIDER recommending books from this list, because the user's partner read them and loved them: {priority_list}\n"
            f"3. Provide exactly 5 highly accurate recommendations.\n"
            f"4. For each, provide the Title, Author, and a 4-sentence punchy explanation of why they will love it.\n"
            f"5. Do not include an introductory greeting or an outro sentence. Just give the list."
        ),

        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                ai_recommendations = data.get('response', 'My brain glitched. Try again.')

                if len(ai_recommendations) > 2000:
                    # Loop through the string and slice it into 1900-character chunks
                    for i in range(0, len(ai_recommendations), 1900):
                        await ctx.send(ai_recommendations[i:i+1900])
                else:
                    await ctx.send(ai_recommendations)
            else:
                await ctx.send(f"I don't see anything like **{book_title}** in my library....What's something else you like that I can give recommendations off of?")


bot.run(os.getenv("DISCORD_TOKEN"))

