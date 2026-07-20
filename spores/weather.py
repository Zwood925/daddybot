import discord
from discord.ext import commands
import os
import aiohttp

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def weather(self, ctx, *, city: str):
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

async def setup(bot):
    await bot.add_cog(Weather(bot))
