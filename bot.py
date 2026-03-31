import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timezone, timedelta
import asyncio

# ===== YOUR CONFIGURATION =====
YOUR_USER_ID = 1380109644558503977           # Only you can use commands
SUCCESS_CHANNEL_ID = 1488400266075045898     # Channel where stealer sends success messages
PH_TIMEZONE = timezone(timedelta(hours=8))   # Philippines time
DATA_FILE = 'successes.json'
SCRIPT_FILE = 'script.lua'                   # Lua file path

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
        if message.content.startswith("✅ Trade completed"):
            data = load_data()
            today = get_today()
            data[today] = data.get(today, 0) + 1
            save_data(data)
            await message.add_reaction("💰")
            print(f"📊 +1 success ({data[today]} total today)")
    await bot.process_commands(message)

# ----- Auto-delete user's command message after responding -----
async def safe_delete(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

# ===== COMMANDS =====
@bot.command()
@commands.check(is_me)
async def calculate(ctx):
    data = load_data()
    today = get_today()
    successes = data.get(today, 0)
    earnings = successes * 2
    embed = discord.Embed(title="📊 Daily Success Report", color=discord.Color.green())
    embed.add_field(name="Date", value=today)
    embed.add_field(name="Successes", value=str(successes), inline=True)
    embed.add_field(name="Earnings", value=f"₱{earnings}", inline=True)
    await ctx.send(embed=embed)
    await safe_delete(ctx)

@bot.command()
@commands.check(is_me)
async def total(ctx):
    data = load_data()
    total_successes = sum(data.values())
    total_earnings = total_successes * 2
    embed = discord.Embed(title="🏆 All-Time Stats", color=discord.Color.gold())
    embed.add_field(name="Total Successes", value=str(total_successes))
    embed.add_field(name="Total Earnings", value=f"₱{total_earnings}")
    await ctx.send(embed=embed)
    await safe_delete(ctx)

@bot.command()
@commands.check(is_me)
async def history(ctx, days: int = 7):
    data = load_data()
    today_date = datetime.now(PH_TIMEZONE).date()
    lines = []
    for i in range(days):
        date = (today_date - timedelta(days=i)).strftime('%Y-%m-%d')
        count = data.get(date, 0)
        lines.append(f"{date}: **{count}** successes (₱{count*2})")
    embed = discord.Embed(title=f"📈 Last {days} Days", description="\n".join(lines), color=discord.Color.blue())
    await ctx.send(embed=embed)
    await safe_delete(ctx)

# ===== NEW COMMAND: /script =====
@bot.command()
@commands.check(is_me)
async def script(ctx):
    try:
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        if len(content) > 1900:
            # Too long → send as a file
            await ctx.send("📄 Script is too long, sending as a file:", file=discord.File(SCRIPT_FILE))
        else:
            # Short → send in a code block (copyable on mobile)
            await ctx.send(f"```lua\n{content}\n```")
    except FileNotFoundError:
        await ctx.send("❌ Lua script not found!")
    await safe_delete(ctx)

# ===== FIXED MIDNIGHT RESET TASK =====
@tasks.loop(minutes=1)
async def reset_at_midnight():
    now = datetime.now(PH_TIMEZONE)

    if now.hour == 0 and now.minute == 0:
        data = load_data()
        today = get_today()
        if today not in data:
            data[today] = 0
            save_data(data)
            print(f"🔄 Daily reset at {today}")

        channel = bot.get_channel(SUCCESS_CHANNEL_ID)
        if channel:
            await channel.send("🔄 **Day reset!** New successes will count for today. Use `/calculate` to track.")

@reset_at_midnight.before_loop
async def before_reset():
    await bot.wait_until_ready()

# ===== RUN =====
bot.run(os.getenv('DISCORD_TOKEN'))
