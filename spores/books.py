import discord
from discord.ext import commands
import sqlite3
import aiohttp
import asyncio

class Books(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def read(self, ctx, *, book_title: str):
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
                # TRAP AVOIDED: Notice it is self.bot.wait_for now!
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)

                if msg.content.lower() == 'skip':
                    author = None
                else:
                    author = msg.content

                await ctx.send("How many stars would you give it? (1-5, or Skip)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)

                if msg.content.lower() == 'skip':
                    rating = None
                else:
                    rating = msg.content

                await ctx.send("What series is this a part of? (Or Skip to leave blank)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)

                if msg.content.lower() == 'skip':
                    series = None
                else:
                    series = msg.content

                await ctx.send("What did you like about it? (Or Skip to leave blank)")
                msg = await self.bot.wait_for('message', check=check, timeout=120.0)

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

    @commands.command()
    async def stats(self, ctx):
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM read_books WHERE user_name = 'zwood925'")
            zwood_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM read_books WHERE user_name = 'swood_38102'")
            kittykat_count = cursor.fetchone()[0]

            total_books = zwood_count + kittykat_count

            await ctx.send(
                f"**THE VAULT SCOREBOARD**\n\n"
                f"**Daddy** has read {zwood_count} books.\n"
                f"**KittyKat** has read {kittykat_count} books.\n"
                f"**Total** books in the vault: {total_books}"  
            )
        finally:
            conn.close()

    @commands.command()
    async def book_rec(self, ctx, *, book_title: str):
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
                        for i in range(0, len(ai_recommendations), 1900):
                            await ctx.send(ai_recommendations[i:i+1900])
                    else:
                        await ctx.send(ai_recommendations)
                else:
                    await ctx.send(f"I don't see anything like **{book_title}** in my library....What's something else you like that I can give recommendations off of?")

async def setup(bot):
    await bot.add_cog(Books(bot))