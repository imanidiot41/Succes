import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import aiohttp
import base64
from datetime import datetime, timezone, timedelta

# ===== YOUR CONFIGURATION =====
YOUR_USER_ID = 1380109644558503977           # Only you can use commands
SUCCESS_CHANNEL_ID = 1488400266075045898     # Channel where stealer sends success messages
PH_TIMEZONE = timezone(timedelta(hours=8))   # Philippines time
DATA_FILE = 'successes.json'

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)

# ---- GitHub API helper functions ----
async def github_request(endpoint, method='GET', data=None):
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return None, "GITHUB_TOKEN not set. Add it to Railway variables."
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f'https://api.github.com/{endpoint}'
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, json=data) as resp:
            if resp.status in (200, 201):
                return await resp.json(), None
            else:
                error_text = await resp.text()
                return None, f'GitHub error {resp.status}: {error_text}'

# ===== GITHUB COG WITH 3 PREDEFINED REPOS =====
class GitHubCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Predefined repos
        self.predefined_repos = [
            "imanidiot41/proyx",
            "imanidiot41/TestMm2",
            "imanidiot41/Succes"
        ]

    # --- Autocomplete for repositories ---
    async def repo_autocomplete(self, interaction: discord.Interaction, current: str):
        return [r for r in self.predefined_repos if current.lower() in r.lower()]

    # --- Autocomplete for files in a repo ---
    async def file_autocomplete(self, interaction: discord.Interaction, current: str, repo: str):
        if not repo:
            return []
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return []
        headers = {'Authorization': f'token {token}'}
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.github.com/repos/{repo}/contents', headers=headers) as resp:
                if resp.status == 200:
                    contents = await resp.json()
                    files = [item['path'] for item in contents if item['type'] == 'file']
                    return [f for f in files if current.lower() in f.lower()][:25]
        return []

    # --- CREATE FILE ---
    @app_commands.command(name='git-create', description='Create a new file in a chosen GitHub repo')
    @app_commands.autocomplete(repository=repo_autocomplete)
    async def git_create(self, interaction: discord.Interaction, repository: str, name: str, code: str, commit_message: str = None):
        await interaction.response.defer(ephemeral=True)
        if not commit_message:
            commit_message = f'Create {name} via bot'
        payload = {
            "message": commit_message,
            "content": base64.b64encode(code.encode()).decode()
        }
        result, error = await github_request(f'repos/{repository}/contents/{name}', 'PUT', payload)
        if error:
            await interaction.followup.send(f'❌ Failed: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ `{name}` created in `{repository}`!', ephemeral=True)

    # --- EDIT FILE ---
    @app_commands.command(name='git-edit', description='Edit an existing file in a chosen GitHub repo')
    @app_commands.autocomplete(repository=repo_autocomplete)
    async def git_edit(self, interaction: discord.Interaction, repository: str, file: str, code: str, commit_message: str = None):
        await interaction.response.defer(ephemeral=True)

        file_info, error = await github_request(f'repos/{repository}/contents/{file}')
        if error:
            await interaction.followup.send(f'❌ Could not fetch file: {error}', ephemeral=True)
            return
        sha = file_info.get('sha')
        if not sha:
            await interaction.followup.send('❌ Could not get file SHA.', ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Update {file} via bot'

        payload = {
            "message": commit_message,
            "content": base64.b64encode(code.encode()).decode(),
            "sha": sha
        }
        result, error = await github_request(f'repos/{repository}/contents/{file}', 'PUT', payload)
        if error:
            await interaction.followup.send(f'❌ Failed to update: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ `{file}` updated in `{repository}`!', ephemeral=True)

    # --- DELETE FILE ---
    @app_commands.command(name='git-delete', description='Delete a file from a chosen GitHub repo')
    @app_commands.autocomplete(repository=repo_autocomplete)
    async def git_delete(self, interaction: discord.Interaction, repository: str, file: str, commit_message: str = None):
        await interaction.response.defer(ephemeral=True)

        file_info, error = await github_request(f'repos/{repository}/contents/{file}')
        if error:
            await interaction.followup.send(f'❌ Could not fetch file: {error}', ephemeral=True)
            return
        sha = file_info.get('sha')
        if not sha:
            await interaction.followup.send('❌ Could not get file SHA.', ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Delete {file} via bot'

        payload = {"message": commit_message, "sha": sha}
        result, error = await github_request(f'repos/{repository}/contents/{file}', 'DELETE', payload)
        if error:
            await interaction.followup.send(f'❌ Failed to delete: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ `{file}` deleted from `{repository}`!', ephemeral=True)

# ===== DATA MANAGEMENT =====
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

# ===== BOT EVENTS =====
@bot.event
async def on_message(message):
    if message.channel.id == SUCCESS_CHANNEL_ID and "✅ Trade completed" in message.content:
        data = load_data()
        today = get_today()
        data[today] = data.get(today, 0) + 1
        save_data(data)
        await message.add_reaction("💰")
        print(f"📊 +1 success ({data[today]} total today)")
    await bot.process_commands(message)

@bot.after_invoke
async def delete_command_message(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

# ===== BOT COMMANDS =====
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

# ===== CLEAR COMMAND =====
@app_commands.command(name='clear', description='Clear messages in this channel')
async def clear(interaction: discord.Interaction, amount: int = 50):
    if interaction.user.id != YOUR_USER_ID:
        await interaction.response.send_message("❌ You cannot use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Cleared {len(deleted)} messages.", ephemeral=True)

# ===== DAILY RESET (updated with once-per-day safeguard) =====
last_reset_date = None  # tracks the last day the reset ran

@tasks.loop(seconds=60)  # check every minute
async def reset_at_midnight():
    global last_reset_date
    now = datetime.now(PH_TIMEZONE)
    today = get_today()

    if now.hour == 0 and now.minute == 0:  # exactly 12:00 AM PH time
        if last_reset_date != today:  # ensure only once per day
            data = load_data()
            if today not in data:
                data[today] = 0
                save_data(data)
                print(f"🔄 Daily reset at {today}")

            channel = bot.get_channel(SUCCESS_CHANNEL_ID)
            if channel:
                await channel.send("🔄 **Day reset!** New successes will count for today. Use `/calculate` to track.")

            last_reset_date = today  # update the last reset date

@reset_at_midnight.before_loop
async def before_reset():
    await bot.wait_until_ready()

# ===== BOT ON_READY =====
@bot.event
async def on_ready():
    print(f'✅ Bot online! Logged in as {bot.user}')
    print(f'📅 PH Time: {datetime.now(PH_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")}')
    await bot.add_cog(GitHubCommands(bot))

    # Register slash commands
    bot.tree.add_command(clear)
    await bot.tree.sync()
    
    reset_at_midnight.start()  # <-- starts the daily reset task

# ===== RUN BOT =====
bot.run(os.getenv('DISCORD_TOKEN'))
