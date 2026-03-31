import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timezone, timedelta

# ===== YOUR CONFIGURATION =====
YOUR_USER_ID = 1380109644558503977           # Only you can use commands
SUCCESS_CHANNEL_ID = 1488400266075045898     # Channel where stealer sends success messages
PH_TIMEZONE = timezone(timedelta(hours=8))   # Philippines time (UTC+8)
DATA_FILE = 'successes.json'

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_today():
    return datetime.now(PH_TIMEZONE).strftime('%Y-%m-%d')

# Only allow you to use commands
def is_me(ctx):
    return ctx.author.id == YOUR_USER_ID

@bot.event
async def on_ready():
    print(f'✅ Bot online! Logged in as {bot.user}')
    print(f'📅 PH Time: {datetime.now(PH_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")}')
    reset_at_midnight.start()

@bot.event
async def on_message(message):
    # Listen in the success channel for trade completion messages
    if message.channel.id == SUCCESS_CHANNEL_ID:
        # You can customize the trigger phrase
        if "✅ Trade completed" in message.content or "Successfully stole" in message.content:
            data = load_data()
            today = get_today()
            if today not in data:
                data[today] = 0
            data[today] += 1
            save_data(data)
            await message.add_reaction("💰")
            print(f"📊 +1 success ({data[today]} total today)")
    await bot.process_commands(message)

@bot.command()
@commands.check(is_me)
async def calculate(ctx):
    """Today's successes and earnings (₱2 each)"""
    data = load_data()
    today = get_today()
    successes = data.get(today, 0)
    earnings = successes * 2
    embed = discord.Embed(title="📊 Daily Success Report", color=discord.Color.green())
    embed.add_field(name="Date", value=today)
    embed.add_field(name="Successes", value=str(successes), inline=True)
    embed.add_field(name="Earnings", value=f"₱{earnings}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
@commands.check(is_me)
async def total(ctx):
    """All-time successes and earnings"""
    data = load_data()
    total_successes = sum(data.values())
    total_earnings = total_successes * 2
    embed = discord.Embed(title="🏆 All-Time Stats", color=discord.Color.gold())
    embed.add_field(name="Total Successes", value=str(total_successes))
    embed.add_field(name="Total Earnings", value=f"₱{total_earnings}")
    await ctx.send(embed=embed)

@bot.command()
@commands.check(is_me)
async def history(ctx, days: int = 7):
    """Last X days (default 7)"""
    data = load_data()
    today_date = datetime.now(PH_TIMEZONE).date()
    lines = []
    for i in range(days):
        date = (today_date - timedelta(days=i)).strftime('%Y-%m-%d')
        count = data.get(date, 0)
        lines.append(f"{date}: **{count}** successes (₱{count*2})")
    embed = discord.Embed(title=f"📈 Last {days} Days", description="\n".join(lines), color=discord.Color.blue())
    await ctx.send(embed=embed)

@tasks.loop(hours=24)
async def reset_at_midnight():
    now = datetime.now(PH_TIMEZONE)
    if now.hour == 0 and now.minute == 0:
        data = load_data()
        today = get_today()
        if today not in data:
            data[today] = 0
            save_data(data)
            print(f"🔄 Daily reset at {today}")
        # Optional: send a message in the channel to confirm reset
        channel = bot.get_channel(SUCCESS_CHANNEL_ID)
        if channel:
            await channel.send("🔄 **New day!** Use `/calculate` to see today's successes.")

@reset_at_midnight.before_loop
async def before_reset():
    await bot.wait_until_ready()

# ===== RUN =====
bot.run(os.getenv('DISCORD_TOKEN'))
