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
    """Make an authenticated request to GitHub API"""
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

# ---- Autocomplete functions for repositories and files ----
async def get_user_repos(ctx: discord.Interaction, current: str):
    """Return list of repositories the user has access to"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return []
    headers = {'Authorization': f'token {token}'}
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.github.com/user/repos', headers=headers, params={'per_page': 50, 'sort': 'full_name'}) as resp:
            if resp.status == 200:
                repos = await resp.json()
                # Filter by current input
                matches = [r['full_name'] for r in repos if current.lower() in r['full_name'].lower()]
                return matches[:25]
            return []

async def get_repo_files(ctx: discord.Interaction, current: str, repo_fullname: str):
    """Return list of file paths in a repository (simple, non-recursive)"""
    token = os.getenv('GITHUB_TOKEN')
    if not token or not repo_fullname:
        return []
    headers = {'Authorization': f'token {token}'}
    # Get contents of root directory (you can extend to recursive later)
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.github.com/repos/{repo_fullname}/contents', headers=headers) as resp:
            if resp.status == 200:
                contents = await resp.json()
                files = [item['path'] for item in contents if item['type'] == 'file']
                # Filter by current input
                matches = [f for f in files if current.lower() in f.lower()]
                return matches[:25]
            return []

# ---- Command group for GitHub ----
class GitHubCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- /git create ----------
    @app_commands.command(name='git-create', description='Create a new file in a GitHub repository')
    @app_commands.autocomplete(repository=get_user_repos)
    async def git_create(self, interaction: discord.Interaction, repository: str, path: str, content: str, commit_message: str = None):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != YOUR_USER_ID:
            await interaction.followup.send("❌ You don't have permission.", ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Create {path} via bot'

        # Prepare payload for GitHub API
        payload = {
            'message': commit_message,
            'content': base64.b64encode(content.encode()).decode(),
        }
        result, error = await github_request(f'repos/{repository}/contents/{path}', 'PUT', payload)
        if error:
            await interaction.followup.send(f'❌ Failed to create file: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ File `{path}` created in `{repository}`!', ephemeral=True)

    # ---------- /git edit ----------
    @app_commands.command(name='git-edit', description='Edit an existing file in a GitHub repository')
    @app_commands.autocomplete(repository=get_user_repos)
    async def git_edit(self, interaction: discord.Interaction, repository: str, path: str, content: str, commit_message: str = None):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != YOUR_USER_ID:
            await interaction.followup.send("❌ You don't have permission.", ephemeral=True)
            return

        # First get the current file's SHA (required for update)
        file_info, error = await github_request(f'repos/{repository}/contents/{path}')
        if error:
            await interaction.followup.send(f'❌ Could not fetch file: {error}', ephemeral=True)
            return
        sha = file_info.get('sha')
        if not sha:
            await interaction.followup.send('❌ Could not get file SHA.', ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Update {path} via bot'

        payload = {
            'message': commit_message,
            'content': base64.b64encode(content.encode()).decode(),
            'sha': sha
        }
        result, error = await github_request(f'repos/{repository}/contents/{path}', 'PUT', payload)
        if error:
            await interaction.followup.send(f'❌ Failed to update file: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ File `{path}` updated in `{repository}`!', ephemeral=True)

    # ---------- /git delete ----------
    @app_commands.command(name='git-delete', description='Delete a file from a GitHub repository')
    @app_commands.autocomplete(repository=get_user_repos)
    async def git_delete(self, interaction: discord.Interaction, repository: str, path: str, commit_message: str = None):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != YOUR_USER_ID:
            await interaction.followup.send("❌ You don't have permission.", ephemeral=True)
            return

        # Get SHA of the file to delete
        file_info, error = await github_request(f'repos/{repository}/contents/{path}')
        if error:
            await interaction.followup.send(f'❌ Could not fetch file: {error}', ephemeral=True)
            return
        sha = file_info.get('sha')
        if not sha:
            await interaction.followup.send('❌ Could not get file SHA.', ephemeral=True)
            return

        if not commit_message:
            commit_message = f'Delete {path} via bot'

        payload = {
            'message': commit_message,
            'sha': sha
        }
        result, error = await github_request(f'repos/{repository}/contents/{path}', 'DELETE', payload)
        if error:
            await interaction.followup.send(f'❌ Failed to delete file: {error}', ephemeral=True)
        else:
            await interaction.followup.send(f'✅ File `{path}` deleted from `{repository}`!', ephemeral=True)

# ===== REST OF YOUR EXISTING BOT CODE (unchanged) =====
# [All the counting, /calculate, /total, /history, midnight reset stays exactly as before]

# --- Add the cog ---
async def setup():
    await bot.add_cog(GitHubCommands(bot))

# --- Load data functions (same as before) ---
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
    await setup()  # Load GitHub commands
    await bot.tree.sync()  # Sync slash commands
    reset_at_midnight.start()

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
        channel = bot.get_channel(SUCCESS_CHANNEL_ID)
        if channel:
            await channel.send("🔄 **Day reset!** New successes will count for today. Use `/calculate` to track.")

@reset_at_midnight.before_loop
async def before_reset():
    await bot.wait_until_ready()

# ===== RUN =====
bot.run(os.getenv('DISCORD_TOKEN'))
