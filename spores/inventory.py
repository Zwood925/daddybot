import discord
from discord.ext import commands
import sqlite3
import asyncio

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------
    # 1. THE MASTER FOLDER
    # ---------------------------------------------------
    @commands.group(invoke_without_command=True)
    async def box(self, ctx):
        await ctx.send(
            "📦 **THE INVENTORY MATRIX**\n"
            "`!box add [box_id]` - Register a new physical tote\n"
            "`!box stash [box_id] [item]` - Put an item inside a box\n"
            "`!box locate [box_id]` - See exactly what is inside a specific box\n"
            "`!find [item]` - Search the entire matrix for an item"
        )

    # ---------------------------------------------------
    # 2. CREATE A NEW BOX
    # ---------------------------------------------------
    @box.command()
    async def add(self, ctx, box_id: str):
        box_id = box_id.upper()
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
            
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO boxes (box_id) VALUES (?)", (box_id,))
            conn.commit()
            
            await ctx.send(f"📦 **{box_id}** registered! Let's fill out the details.")

            try:
                await ctx.send("What color is the label/tape? (e.g., Green, White, or Skip)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                color_code = None if msg.content.lower() == 'skip' else msg.content

                await ctx.send("What type of container is it? (e.g., Large Tote, Cardboard, Skip)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                container_type = None if msg.content.lower() == 'skip' else msg.content

                await ctx.send("What is the general theme? (e.g., Xmas Decor, Lineman Tools, Skip)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                theme = None if msg.content.lower() == 'skip' else msg.content

                await ctx.send("Where is it physically located right now? (e.g., Garage, Storage Unit, Skip)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                location = None if msg.content.lower() == 'skip' else msg.content
                
                await ctx.send("What's the status? (e.g., Storage, Yard Sale, Active, Skip)")
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                status = None if msg.content.lower() == 'skip' else msg.content

                cursor.execute("""
                    UPDATE boxes 
                    SET color_code = ?, container_type = ?, theme = ?, location = ?, status = ?
                    WHERE box_id = ?
                """, (color_code, container_type, theme, location, status, box_id))
                
                conn.commit()
                await ctx.send(f"✅ All set! **{box_id}** is fully documented and secure in the matrix.")

            except asyncio.TimeoutError:
                await ctx.send("⏳ You took too long! I saved the box ID, but the rest of the details are blank for now.")
                
        except sqlite3.IntegrityError:
            await ctx.send(f"⚠️ **{box_id}** already exists in the matrix!")
        finally:
            conn.close()

    # ---------------------------------------------------
    # 3. ADD ITEMS TO A BOX
    # ---------------------------------------------------
    @box.command()
    async def stash(self, ctx, box_id: str, *, item_name: str):
        box_id = box_id.upper()
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            # First, check if the box actually exists
            cursor.execute("SELECT box_id FROM boxes WHERE box_id = ?", (box_id,))
            if not cursor.fetchone():
                await ctx.send(f"⚠️ Box **{box_id}** doesn't exist! Use `!box add {box_id}` first.")
                return

            # If it exists, add the item
            cursor.execute("INSERT INTO items (item_name, box_id) VALUES (?, ?)", (item_name, box_id))
            conn.commit()
            await ctx.send(f"📥 Stashed **{item_name}** inside **{box_id}**.")
            
        finally:
            conn.close()

    # ---------------------------------------------------
    # 4. LOOK INSIDE A SPECIFIC BOX
    # ---------------------------------------------------
    @box.command()
    async def locate(self, ctx, box_id: str):
        box_id = box_id.upper()
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            # Grab the box details
            cursor.execute("SELECT color_code, container_type, theme, location, status FROM boxes WHERE box_id = ?", (box_id,))
            box_info = cursor.fetchone()

            if not box_info:
                await ctx.send(f"⚠️ I have no record of **{box_id}** in the matrix.")
                return

            # Grab the items inside the box
            cursor.execute("SELECT item_name FROM items WHERE box_id = ?", (box_id,))
            items = cursor.fetchall()

            # Format the output nicely
            color, container, theme, location, status = box_info
            
            response = f"📦 **BOX DOSSIER: {box_id}**\n"
            response += f"**Theme:** {theme} | **Location:** {location} | **Color:** {color}\n"
            response += f"**Container:** {container} | **Status:** {status}\n"
            response += "------------------------\n"
            
            if items:
                response += "**Contents:**\n"
                for item in items:
                    response += f"• {item[0]}\n"
            else:
                response += "*This box is currently empty in the database.*"

            await ctx.send(response)

        finally:
            conn.close()

    # ---------------------------------------------------
    # 5. SEARCH THE ENTIRE HOUSE FOR AN ITEM
    # ---------------------------------------------------
    @commands.command()
    async def find(self, ctx, *, search_term: str):
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            # The SQL JOIN magic: matches the item to the box, and gets the location
            cursor.execute("""
                SELECT items.item_name, boxes.box_id, boxes.location 
                FROM items 
                JOIN boxes ON items.box_id = boxes.box_id 
                WHERE items.item_name LIKE ?
            """, (f"%{search_term}%",))
            
            results = cursor.fetchall()

            if not results:
                await ctx.send(f"🔍 I couldn't find anything matching **'{search_term}'** in the matrix.")
                return

            response = f"🔍 **SEARCH RESULTS FOR '{search_term.upper()}':**\n"
            for row in results:
                item_name, box_id, location = row
                response += f"• **{item_name}** is inside **{box_id}** *(Location: {location})*\n"

            await ctx.send(response)

        finally:
            conn.close()

    # ---------------------------------------------------
    # 6. REMOVE AN ITEM FROM A BOX
    # ---------------------------------------------------
    @box.command()
    async def remove(self, ctx, box_id: str, *, item_name: str):
        box_id = box_id.upper()
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
            # Check if the item is actually in there (forgiving case-search)
            cursor.execute("SELECT item_name FROM items WHERE box_id = ? AND item_name LIKE ?", (box_id, item_name))
            result = cursor.fetchone()

            if not result:
                await ctx.send(f"⚠️ I don't see anything like **{item_name}** inside **{box_id}**.")
                return

            actual_item_name = result[0]

            # Delete the specific item
            cursor.execute("DELETE FROM items WHERE box_id = ? AND item_name = ?", (box_id, actual_item_name))
            conn.commit()
            
            await ctx.send(f"🗑️ Removed **{actual_item_name}** from **{box_id}**.")

        finally:
            conn.close()

    # ---------------------------------------------------
    # 7. DELETE AN ENTIRE BOX
    # ---------------------------------------------------
    @box.command()
    async def delete(self, ctx, box_id: str):
        box_id = box_id.upper()
        conn = sqlite3.connect("daddybot_memory.db")
        cursor = conn.cursor()

        try:
                # Check if box exists
            cursor.execute("SELECT box_id FROM boxes WHERE box_id = ?", (box_id,))
            if not cursor.fetchone():
                await ctx.send(f"⚠️ Box **{box_id}** doesn't exist in the matrix.")
                return

                # Step 1: Delete all items inside the box first (prevents ghost data)
            cursor.execute("DELETE FROM items WHERE box_id = ?", (box_id,))
                
                # Step 2: Delete the actual box
            cursor.execute("DELETE FROM boxes WHERE box_id = ?", (box_id,))
                
            conn.commit()
            await ctx.send(f"🧨 **{box_id}** and everything inside it has been completely wiped from the matrix.")

        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(Inventory(bot))