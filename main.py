import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv  # ✅ Import dotenv
import json
import asyncio
import random
import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
from flask import Flask, render_template

load_dotenv()  # ✅ Load .env file

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable not found!")
    print("Please add your Discord bot token to the Secrets tab.")
    exit(1)

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable members intent
bot = commands.Bot(command_prefix="!", intents=intents)

# Data Models
@dataclass
class Player:
    discord_id: str
    rl_username: str
    platform: str
    region: str
    mmr: int
    rank: str
    stats: Dict[str, int]
    match_history: List[Dict]

@dataclass 
class Match:
    match_id: str
    mode: str
    map_name: str
    region: str
    team_size: str
    players: List[str]
    status: str
    created_at: str
    room_name: str = ""
    room_password: str = ""

# Constants
REGIONS = [
    ("NA-East", "🇺🇸 North America East"),
    ("NA-West", "🇺🇸 North America West"), 
    ("EU", "🇪🇺 Europe"),
    ("ASIA", "🇯🇵 Asia"),
    ("OCE", "🇦🇺 Oceania"),
    ("SAM", "🇧🇷 South America"),
    ("ME", "🌍 Middle East")
]

MODES = [
    ("Soccar", "⚽ Soccar"),
    ("Hoops", "🏀 Hoops"),
    ("Rumble", "💥 Rumble"),
    ("Dropshot", "💎 Dropshot"),
    ("Snow Day", "🏒 Snow Day"),
    ("Heatseeker", "🎯 Heatseeker")
]

TEAM_SIZES = [
    ("1v1", "⚡ 1v1 Duel"),
    ("2v2", "🤝 2v2 Doubles"),
    ("3v3", "👥 3v3 Standard")
]

MAPS = {
    "Soccar": ["DFH Stadium", "Mannfield", "Champions Field", "Neo Tokyo", "Urban Central", "Beckwith Park"],
    "Hoops": ["Dunk House", "The Block"],
    "Rumble": ["DFH Stadium", "Mannfield", "Champions Field"],
    "Dropshot": ["Core 707", "Throwback Stadium"],
    "Snow Day": ["Snowy DFH Stadium", "Wintry Mannfield"],
    "Heatseeker": ["DFH Stadium", "Mannfield", "Champions Field"]
}

RANKS = [
    (0, "Bronze I"), (200, "Bronze II"), (300, "Bronze III"),
    (400, "Silver I"), (500, "Silver II"), (600, "Silver III"),
    (700, "Gold I"), (800, "Gold II"), (900, "Gold III"),
    (1000, "Platinum I"), (1100, "Platinum II"), (1200, "Platinum III"),
    (1300, "Diamond I"), (1400, "Diamond II"), (1500, "Diamond III"),
    (1600, "Champion I"), (1700, "Champion II"), (1800, "Champion III"),
    (1900, "Grand Champion I"), (2000, "Grand Champion II"), (2100, "Grand Champion III"),
    (2200, "Supersonic Legend")
]

# Global Data Storage
players: Dict[str, Player] = {}
queues: Dict[str, Dict[str, Dict[str, List[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
matches: Dict[str, Match] = {}
dashboard_messages: List[Dict] = []
leaderboard_messages: List[Dict] = []
welcome_channels: List[int] = []
clip_channels: List[int] = []

# Utility Functions
def load_data():
    global players, matches, welcome_channels, clip_channels
    try:
        with open("players.json", "r") as f:
            data = json.load(f)
            players = {k: Player(**v) for k, v in data.items()}
    except FileNotFoundError:
        players = {}

    try:
        with open("matches.json", "r") as f:
            data = json.load(f)
            matches = {k: Match(**v) for k, v in data.items()}
    except FileNotFoundError:
        matches = {}

    try:
        with open("welcome_channels.json", "r") as f:
            welcome_channels = json.load(f)
    except FileNotFoundError:
        welcome_channels = []

    try:
        with open("clip_channels.json", "r") as f:
            clip_channels = json.load(f)
    except FileNotFoundError:
        clip_channels = []

def save_data():
    with open("players.json", "w") as f:
        json.dump({k: asdict(v) for k, v in players.items()}, f, indent=2)

    with open("matches.json", "w") as f:
        json.dump({k: asdict(v) for k, v in matches.items()}, f, indent=2)

    with open("welcome_channels.json", "w") as f:
        json.dump(welcome_channels, f, indent=2)

    with open("clip_channels.json", "w") as f:
        json.dump(clip_channels, f, indent=2)

def get_rank(mmr: int) -> str:
    for threshold, rank in reversed(RANKS):
        if mmr >= threshold:
            return rank
    return "Bronze I"

def update_player_mmr(player_id: str, won: bool, opponent_mmr: int):
    if player_id not in players:
        return

    player = players[player_id]
    k_factor = 32
    expected = 1 / (1 + 10 ** ((opponent_mmr - player.mmr) / 400))
    actual = 1 if won else 0
    mmr_change = int(k_factor * (actual - expected))

    player.mmr = max(0, player.mmr + mmr_change)
    player.rank = get_rank(player.mmr)

    if won:
        player.stats["wins"] += 1
    else:
        player.stats["losses"] += 1

# Flask web app for dashboard
app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html", players=players, matches=matches)

def run_web_dashboard():
    app.run(debug=True)

# Discord UI Components
class PlayerLinkModal(discord.ui.Modal, title="Link Your Rocket League Profile"):
    def __init__(self):
        super().__init__()

    rl_username = discord.ui.TextInput(
        label="Rocket League Username", 
        placeholder="Enter your RL username (display name only)...",
        max_length=100
    )
    platform = discord.ui.TextInput(
        label="Platform", 
        placeholder="Epic, Steam, PlayStation, Xbox, Switch...",
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        region = select.values[0]

        # Create new player
        player = Player(
            discord_id=str(self.user_id),
            rl_username=self.rl_username,
            platform=self.platform,
            region=region,
            mmr=1000,
            rank="Gold I",
            stats={"wins": 0, "losses": 0, "goals": 0, "assists": 0, "saves": 0},
            match_history=[]
        )

        players[str(self.user_id)] = player
        save_data()

        # Auto-assign Verified Player role
        try:
            member = interaction.guild.get_member(self.user_id)
            if member:
                verified_role = None
                for role in interaction.guild.roles:
                    if role.name == "Verified Player":
                        verified_role = role
                        break

                if verified_role:
                    await member.add_roles(verified_role, reason="Profile linked - verified player")
        except:
            pass

        embed = discord.Embed(
            title="✅ Profile Linked Successfully!",
            description=f"**{self.rl_username}** is now linked to your Discord account!\n\n"
                       f"🎉 **You now have full access to the server!**",
            color=0x00ff00
        )
        embed.add_field(name="Platform", value=self.platform, inline=True)
        embed.add_field(name="Region", value=dict(REGIONS)[region], inline=True)
        embed.add_field(name="Starting MMR", value="1000", inline=True)
        embed.add_field(name="Starting Rank", value="Gold I", inline=True)
        embed.add_field(
            name="🚀 What's Next?",
            value="• You can now join competitive queues\n"
                  "• Access all server channels\n"
                  "• View and use voice channels\n"
                  "• Post clips and chat with the community",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=None)

class RegionSelectView(discord.ui.View):
    def __init__(self, rl_username: str, platform: str, user_id: int):
        super().__init__(timeout=300)
        self.rl_username = rl_username
        self.platform = platform
        self.user_id = user_id

    @discord.ui.select(placeholder="Choose your region...", options=[
        discord.SelectOption(label=name, value=code, description=f"Play in {name}") for code, name in REGIONS
    ])
    async def region_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        region = select.values[0]

        # Create new player
        player = Player(
            discord_id=str(self.user_id),
            rl_username=self.rl_username,
            platform=self.platform,
            region=region,
            mmr=1000,
            rank="Gold I",
            stats={"wins": 0, "losses": 0, "goals": 0, "assists": 0, "saves": 0},
            match_history=[]
        )

        players[str(self.user_id)] = player
        save_data()

        # Auto-assign Verified Player role
        try:
            member = interaction.guild.get_member(self.user_id)
            if member:
                verified_role = None
                for role in interaction.guild.roles:
                    if role.name == "Verified Player":
                        verified_role = role
                        break

                if verified_role:
                    await member.add_roles(verified_role, reason="Profile linked - verified player")
        except:
            pass

        embed = discord.Embed(
            title="✅ Profile Linked Successfully!",
            description=f"**{self.rl_username}** is now linked to your Discord account!\n\n"
                       f"🎉 **You now have full access to the server!**",
            color=0x00ff00
        )
        embed.add_field(name="Platform", value=self.platform, inline=True)
        embed.add_field(name="Region", value=dict(REGIONS)[region], inline=True)
        embed.add_field(name="Starting MMR", value="1000", inline=True)
        embed.add_field(name="Starting Rank", value="Gold I", inline=True)
        embed.add_field(
            name="🚀 What's Next?",
            value="• You can now join competitive queues\n"
                  "• Access all server channels\n"
                  "• View and use voice channels\n"
                  "• Post clips and chat with the community",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=None)

class QueueDashboard(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_mode = None
        self.selected_map = None
        self.selected_team_size = None
        self.selected_region = None

    @discord.ui.button(label="🔗 Link Profile", style=discord.ButtonStyle.primary, row=0, custom_id="link_profile")
    async def link_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        if user_id not in players:
            modal = PlayerLinkModal()
            await interaction.response.send_modal(modal)
        else:
            player = players[str(interaction.user.id)]
            embed = discord.Embed(title="📊 Your Profile", color=0x00ffcc)
            embed.add_field(name="RL Username", value=player.rl_username, inline=True)
            embed.add_field(name="Platform", value=player.platform, inline=True)
            embed.add_field(name="Region", value=dict(REGIONS)[player.region], inline=True)
            embed.add_field(name="Rank", value=f"{player.rank} ({player.mmr} MMR)", inline=True)
            embed.add_field(name="W/L", value=f"{player.stats['wins']}/{player.stats['losses']}", inline=True)
            embed.add_field(name="Goals", value=player.stats['goals'], inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.select(placeholder="🎮 Select Game Mode...", options=[
        discord.SelectOption(label=name, value=code, emoji=emoji.split()[0]) for code, emoji_name in MODES for emoji, name in [emoji_name.split(' ', 1)]
    ], row=1, custom_id="mode_select")
    async def mode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_mode = select.values[0]
        await interaction.response.send_message(f"✅ Selected mode: **{dict(MODES)[self.selected_mode]}**", ephemeral=True)

    @discord.ui.select(placeholder="🗺️ Select Map...", options=[
        discord.SelectOption(label="Random", value="Random", emoji="🎲"),
        discord.SelectOption(label="DFH Stadium", value="DFH Stadium", emoji="🏟️"),
        discord.SelectOption(label="Mannfield", value="Mannfield", emoji="🌿"),
        discord.SelectOption(label="Champions Field", value="Champions Field", emoji="🏆"),
        discord.SelectOption(label="Neo Tokyo", value="Neo Tokyo", emoji="🌸")
    ], row=2, custom_id="map_select")
    async def map_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_map = select.values[0]
        await interaction.response.send_message(f"✅ Selected map: **{self.selected_map}**", ephemeral=True)

    @discord.ui.select(placeholder="👥 Select Team Size...", options=[
        discord.SelectOption(label=name, value=code, emoji=emoji.split()[0]) for code, emoji_name in TEAM_SIZES for emoji, name in [emoji_name.split(' ', 1)]
    ], row=3, custom_id="team_size_select")
    async def team_size_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_team_size = select.values[0]
        await interaction.response.send_message(f"✅ Selected team size: **{dict(TEAM_SIZES)[self.selected_team_size]}**", ephemeral=True)

    @discord.ui.button(label="🚀 Join Queue", style=discord.ButtonStyle.success, row=4, custom_id="join_queue")
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)

        if user_id not in players:
            await interaction.response.send_message("❌ Please link your profile first!", ephemeral=True)
            return

        if not all([self.selected_mode, self.selected_map, self.selected_team_size]):
            await interaction.response.send_message("❌ Please select mode, map, and team size!", ephemeral=True)
            return

        player = players[user_id]
        region = player.region

        # Remove from any existing queues
        for r in queues:
            for m in queues[r]:
                for t in queues[r][m]:
                    if user_id in queues[r][m][t]:
                        queues[r][m][t].remove(user_id)

        # Add to new queue
        queues[region][self.selected_mode][self.selected_team_size].append(user_id)

        queue_count = len(queues[region][self.selected_mode][self.selected_team_size])
        needed = int(self.selected_team_size[0]) * 2  # 1v1 = 2, 2v2 = 4, 3v3 = 6

        embed = discord.Embed(title="🔍 Searching for Match", color=0x00ffcc)
        embed.add_field(name="Mode", value=dict(MODES)[self.selected_mode], inline=True)
        embed.add_field(name="Map", value=self.selected_map, inline=True)
        embed.add_field(name="Team Size", value=dict(TEAM_SIZES)[self.selected_team_size], inline=True)
        embed.add_field(name="Region", value=dict(REGIONS)[region], inline=True)
        embed.add_field(name="Queue Status", value=f"{queue_count}/{needed} players", inline=True)

        if queue_count >= needed:
            embed.add_field(name="Status", value="🎮 **Match starting soon!**", inline=False)
        else:
            embed.add_field(name="Status", value=f"⏳ Waiting for {needed - queue_count} more players", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Leave Queue", style=discord.ButtonStyle.danger, row=4, custom_id="leave_queue")
    async def leave_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)

        # Remove from all queues
        removed = False
        for r in queues:
            for m in queues[r]:
                for t in queues[r][m]:
                    if user_id in queues[r][m][t]:
                        queues[r][m][t].remove(user_id)
                        removed = True

        if removed:
            embed = discord.Embed(title="❌ Left Queue", description="You have been removed from all queues.", color=0xff0000)
        else:
            embed = discord.Embed(title="ℹ️ Not in Queue", description="You are not currently in any queue.", color=0x808080)

        await interaction.response.send_message(embed=embed, ephemeral=True)

class MatchResultView(discord.ui.View):
    def __init__(self, match: Match):
        super().__init__(timeout=300)
        self.match = match

    @discord.ui.button(label="🟠 Orange Team Won", style=discord.ButtonStyle.primary)
    async def orange_won(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_result(interaction, "Orange")

    @discord.ui.button(label="🔵 Blue Team Won", style=discord.ButtonStyle.primary)
    async def blue_won(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_result(interaction, "Blue")

    async def process_result(self, interaction: discord.Interaction, winner: str):
        # Update player MMRs and stats
        team_size = int(self.match.team_size[0])
        orange_team = self.match.players[:team_size]
        blue_team = self.match.players[team_size:]

        # Calculate average MMRs for rating calculation
        orange_avg = sum(players[p].mmr for p in orange_team if p in players) / len(orange_team)
        blue_avg = sum(players[p].mmr for p in blue_team if p in players) / len(blue_team)

        # Update MMRs
        for player_id in orange_team:
            if player_id in players:
                won = winner == "Orange"
                update_player_mmr(player_id, won, blue_avg)

                # Add match to history
                players[player_id].match_history.append({
                    "match_id": self.match.match_id,
                    "result": "win" if won else "loss",
                    "mode": self.match.mode,
                    "map": self.match.map_name,
                    "team_size": self.match.team_size,
                    "region": self.match.region,
                    "timestamp": datetime.datetime.now().isoformat()
                })

        for player_id in blue_team:
            if player_id in players:
                won = winner == "Blue"
                update_player_mmr(player_id, won, orange_avg)

                # Add match to history
                players[player_id].match_history.append({
                    "match_id": self.match.match_id,
                    "result": "win" if won else "loss",
                    "mode": self.match.mode,
                    "map": self.match.map_name,
                    "team_size": self.match.team_size,
                    "region": self.match.region,
                    "timestamp": datetime.datetime.now().isoformat()
                })

        # Update match status
        matches[self.match.match_id].status = "Completed"
        save_data()

        embed = discord.Embed(title="🏆 Match Results Recorded", color=0x00ff00)
        embed.add_field(name="Winner", value=f"{winner} Team", inline=True)
        embed.add_field(name="Match ID", value=self.match.match_id, inline=True)
        embed.add_field(name="Mode", value=f"{self.match.mode} {self.match.team_size}", inline=True)

        await interaction.response.edit_message(embed=embed, view=None)

# Bot Events
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    load_data()

    # Add persistent views to make dashboards work after restart
    bot.add_view(QueueDashboard())
    print("🔄 Persistent views loaded")

    # Restore existing dashboard and leaderboard messages
    await restore_persistent_messages()

    # Start background tasks
    queue_checker.start()
    leaderboard_updater.start()
    match_reminder.start()  # Start match reminder task
    save_data_task.start()  # Start periodic data saving

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"📱 Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_member_join(member):
    """Assign Member role and check account linking"""
    # Assign default member role
    try:
        member_role = discord.utils.get(member.guild.roles, name="Member")
        if member_role:
            await member.add_roles(member_role, reason="Auto-assign Member role on join")
    except Exception as e:
        print(f"Failed to assign Member role: {e}")

    # Check if the member has linked their profile
    user_id = str(member.id)
    if user_id not in players:
        # Send a DM to the member
        try:
            embed = discord.Embed(
                title="👋 Welcome! Link Your Profile to Get Started",
                description="Welcome to our Rocket League community! To get full access to the server, you need to link your Rocket League profile. This helps us verify your account and allows you to join competitive matches.",
                color=0x00ffcc
            )
            embed.add_field(
                name="🔗 How to Link Your Profile",
                value="1. Go to the `#matchmaking-dashboard` channel in the server.\n"
                      "2. Click the `🔗 Link Profile` button.\n"
                      "3. Follow the instructions to enter your Rocket League username and platform.",
                inline=False
            )
            embed.add_field(
                name="🔒 Privacy Notice",
                value="**OctaneScore NEVER asks for passwords!**\n"
                      "We only need your display name to create match rooms and show stats.",
                inline=False
            )
            embed.set_footer(text="Thank you for joining our community!")
            await member.send(embed=embed)
        except Exception as e:
            print(f"Failed to send DM to new member: {e}")

async def restore_persistent_messages():
    """Restore dashboard and leaderboard functionality after bot restart"""
    # Restore dashboard messages
    for msg_info in dashboard_messages[:]:
        try:
            channel = bot.get_channel(msg_info["channel_id"])
            if channel:
                message = await channel.fetch_message(msg_info["message_id"])
                # Update the view to make buttons work again
                view = QueueDashboard()
                await message.edit(view=view)
                print(f"✅ Restored dashboard in #{channel.name}")
        except Exception as e:
            print(f"❌ Failed to restore dashboard: {e}")
            # Remove invalid message info
            dashboard_messages.remove(msg_info)

    # Force update leaderboards immediately
    if leaderboard_messages:
        await force_update_leaderboards()
        print("✅ Leaderboards updated")

async def force_update_leaderboards():
    """Force update all leaderboard messages"""
    if not players:
        return

    # Sort by MMR
    sorted_players = sorted(players.items(), key=lambda x: x[1].mmr, reverse=True)[:10]

    embed = discord.Embed(title="🏆 Live Leaderboard", color=0xFFD700)
    embed.set_footer(text=f"Last updated: {datetime.datetime.now().strftime('%H:%M:%S')} UTC")

    leaderboard_text = ""
    for i, (user_id, player) in enumerate(sorted_players):
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = player.rl_username

        leaderboard_text += f"{rank_emoji} **{name}** - {player.rank} ({player.mmr} MMR)\n"

    embed.description = leaderboard_text if leaderboard_text else "No players have linked their profiles yet!"

    # Update all leaderboard messages
    for msg_info in leaderboard_messages[:]:
        try:
            channel = bot.get_channel(msg_info["channel_id"])
            if channel:
                message = await channel.fetch_message(msg_info["message_id"])
                await message.edit(embed=embed)
        except:
            # Remove invalid message info
            leaderboard_messages.remove(msg_info)

# Background Tasks
@tasks.loop(seconds=30)
async def queue_checker():
    """Check queues and create matches when enough players are found"""
    for region in list(queues.keys()):
        for mode in list(queues[region].keys()):
            for team_size in list(queues[region][mode].keys()):
                player_list = queues[region][mode][team_size]
                needed = int(team_size[0]) * 2

                if len(player_list) >= needed:
                    # Create match
                    selected_players = player_list[:needed]
                    for p in selected_players:
                        queues[region][mode][team_size].remove(p)

                    match_id = f"match_{random.randint(10000, 99999)}"
                    map_name = random.choice(MAPS.get(mode, ["DFH Stadium"]))
                    room_name = f"OS{random.randint(1000, 9999)}"
                    room_password = f"{random.randint(100, 999)}"

                    match = Match(
                        match_id=match_id,
                        mode=mode,
                        map_name=map_name,
                        region=region,
                        team_size=team_size,
                        players=selected_players,
                        status="Active",
                        created_at=datetime.datetime.now().isoformat(),
                        room_name=room_name,
                        room_password=room_password
                    )

                    matches[match_id] = match
                    save_data()

                    # Notify players
                    await notify_match_found(match)

@tasks.loop(time=datetime.time(hour=12, minute=0))  # Runs daily at 12:00 UTC
async def match_reminder():
    """Reminds players about upcoming matches"""
    now = datetime.datetime.now()
    for match_id, match in matches.items():
        # Assuming 'created_at' is stored in ISO format
        created_at = datetime.datetime.fromisoformat(match.created_at)
        time_difference = now - created_at

        # If match was created more than 20 minutes ago and is still active
        if time_difference > datetime.timedelta(minutes=20) and match.status == "Active":
            # Send reminder
            await remind_match_players(match)

@tasks.loop(seconds=30)
async def leaderboard_updater():
    """Update leaderboard messages every 30 seconds"""
    if not players or not leaderboard_messages:
        return

    # Sort by MMR
    sorted_players = sorted(players.items(), key=lambda x: x[1].mmr, reverse=True)[:10]

    embed = discord.Embed(title="🏆 Live Leaderboard", color=0xFFD700)
    embed.set_footer(text=f"Last updated: {datetime.datetime.now().strftime('%H:%M:%S')} UTC")

    leaderboard_text = ""
    for i, (user_id, player) in enumerate(sorted_players):
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = player.rl_username

        leaderboard_text += f"{rank_emoji} **{name}** - {player.rank} ({player.mmr} MMR)\n"

    embed.description = leaderboard_text if leaderboard_text else "No players have linked their profiles yet!"

    # Update all leaderboard messages
    for msg_info in leaderboard_messages[:]:
        try:
            channel = bot.get_channel(msg_info["channel_id"])
            if channel:
                message = await channel.fetch_message(msg_info["message_id"])
                await message.edit(embed=embed)
        except:
            # Remove invalid message info
            leaderboard_messages.remove(msg_info)

@bot.event
async def on_member_remove(member):
    """Say goodbye when members leave"""
    for channel_id in welcome_channels:
        try:
            channel = bot.get_channel(channel_id)
            if channel and channel.guild.id == member.guild.id:
                embed = discord.Embed(
                    title="👋 Goodbye!",
                    description=f"**{member.display_name}** has left the server.\n\n"
                               f"Thanks for being part of our Rocket League community! 🚗💨\n"
                               f"You're always welcome back on the field! 🏆",
                    color=0xff6b6b
                )
                embed.add_field(
                    name="📊 Member Count",
                    value=f"We now have **{len(member.guild.members)}** members",
                    inline=False
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="See you in the arena! ⚽")

                await channel.send(embed=embed)
        except:
            pass

async def notify_match_found(match: Match):
    """Notify players when a match is found"""
    team_size = int(match.team_size[0])
    orange_team = match.players[:team_size]
    blue_team = match.players[team_size:]

    embed = discord.Embed(title="🎮 Match Found!", color=0x00ff00)
    embed.add_field(name="Match ID", value=match.match_id, inline=True)
    embed.add_field(name="Mode", value=f"{match.mode} {match.team_size}", inline=True)
    embed.add_field(name="Map", value=match.map_name, inline=True)
    embed.add_field(name="Region", value=dict(REGIONS)[match.region], inline=True)

    embed.add_field(name="🟠 Orange Team", value="\n".join([f"<@{p}>" for p in orange_team]), inline=True)
    embed.add_field(name="🔵 Blue Team", value="\n".join([f"<@{p}>" for p in blue_team]), inline=True)

    embed.add_field(name="🔑 Room Details", value=f"**Name:** {match.room_name}\n**Password:** {match.room_password}", inline=False)
    embed.add_field(name="📋 Instructions", value="1. Create private match with above details\n2. Play the match\n3. Report results below", inline=False)

    view = MatchResultView(match)

    # Send to all players
    for player_id in match.players:
        try:
            user = await bot.fetch_user(int(player_id))
            await user.send(embed=embed, view=view)
        except:
            pass

async def remind_match_players(match: Match):
    """Reminds players about an active match"""
    team_size = int(match.team_size[0])
    orange_team = match.players[:team_size]
    blue_team = match.players[team_size:]

    embed = discord.Embed(title="⏰ Match Reminder", color=0xffa500)
    embed.add_field(name="Match ID", value=match.match_id, inline=True)
    embed.add_field(name="Mode", value=f"{match.mode} {match.team_size}", inline=True)
    embed.add_field(name="Map", value=match.map_name, inline=True)
    embed.add_field(name="Region", value=dict(REGIONS)[match.region], inline=True)

    embed.add_field(name="🟠 Orange Team", value="\n".join([f"<@{p}>" for p in orange_team]), inline=True)
    embed.add_field(name="🔵 Blue Team", value="\n".join([f"<@{p}>" for p in blue_team]), inline=True)

    embed.add_field(name="🔑 Room Details", value=f"**Name:** {match.room_name}\n**Password:** {match.room_password}", inline=False)
    embed.add_field(name="📋 Instructions", value="Please ensure you have completed your match and report the results!", inline=False)

    # Send to all players
    for player_id in match.players:
        try:
            user = await bot.fetch_user(int(player_id))
            await user.send(embed=embed)
        except:
            pass

# Slash Commands
@bot.tree.command(name="dashboard", description="Setup the OctaneScore matchmaking dashboard")
async def setup_dashboard(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only administrators can setup dashboards!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🚀 OctaneScore Matchmaking Dashboard",
        description="**Welcome to OctaneScore!** Link your profile and start playing competitive Rocket League matches.",
        color=0x00ffcc
    )

    embed.add_field(
        name="🎯 How It Works",
        value="1️⃣ **Link Profile** - Connect your RL account\n2️⃣ **Select Preferences** - Choose mode, map, team size\n3️⃣ **Join Queue** - Get matched with players\n4️⃣ **Play & Report** - Complete matches and gain MMR",
        inline=False
    )

    embed.add_field(
        name="🔒 Privacy & Security",
        value="**We NEVER ask for passwords!** Only your display name is needed to create match rooms and show stats. Your Epic/Steam login stays private!",
        inline=False
    )

    embed.add_field(
        name="🌍 Supported Regions",
        value="🇺🇸 NA-East/West • 🇪🇺 Europe • 🇯🇵 Asia • 🇦🇺 Oceania • 🇧🇷 South America • 🌍 Middle East",
        inline=False
    )

    embed.add_field(
        name="🎮 Game Modes",
        value="⚽ Soccar • 🏀 Hoops • 💥 Rumble • 💎 Dropshot • 🏒 Snow Day • 🎯 Heatseeker",
        inline=False
    )

    embed.set_footer(text="OctaneScore • Advanced Rocket League Matchmaking")

    view = QueueDashboard()
    message = await interaction.response.send_message(embed=embed, view=view)

    # Track dashboard message
    dashboard_messages.append({
        "channel_id": interaction.channel.id,
        "message_id": (await interaction.original_response()).id,
        "guild_id": interaction.guild.id
    })

@bot.tree.command(name="stats", description="View your OctaneScore statistics")
async def view_stats(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    user_id = str(target.id)

    if user_id not in players:
        await interaction.response.send_message(f"❌ {target.display_name} hasn't linked their profile yet!", ephemeral=True)
        return

    player = players[user_id]

    embed = discord.Embed(title=f"📊 {target.display_name}'s Stats", color=0x00ffcc)
    embed.add_field(name="RL Username", value=player.rl_username, inline=True)
    embed.add_field(name="Platform", value=player.platform, inline=True)
    embed.add_field(name="Region", value=dict(REGIONS)[player.region], inline=True)
    embed.add_field(name="Rank", value=f"{player.rank}", inline=True)
    embed.add_field(name="MMR", value=f"{player.mmr}", inline=True)
    embed.add_field(name="Matches", value=f"{player.stats['wins'] + player.stats['losses']}", inline=True)
    embed.add_field(name="W/L Ratio", value=f"{player.stats['wins']}/{player.stats['losses']}", inline=True)
    embed.add_field(name="Goals", value=f"{player.stats['goals']}", inline=True)
    embed.add_field(name="Assists", value=f"{player.stats['assists']}", inline=True)

    if player.match_history:
        recent = player.match_history[-3:]
        history_text = "\n".join([f"{'✅' if m['result'] == 'win' else '❌'} {m['mode']} {m['team_size']} - {m['map']}" for m in recent])
        embed.add_field(name="Recent Matches", value=history_text, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="View the OctaneScore leaderboard")
async def view_leaderboard(interaction: discord.Interaction):
    if not players:
        await interaction.response.send_message("❌ No players have linked their profiles yet!", ephemeral=True)
        return

    # Sort by MMR
    sorted_players = sorted(players.items(), key=lambda x: x[1].mmr, reverse=True)[:10]

    embed = discord.Embed(title="🏆 OctaneScore Leaderboard", color=0xFFD700)

    leaderboard_text = ""
    for i, (user_id, player) in enumerate(sorted_players):
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = player.rl_username

        leaderboard_text += f"{rank_emoji} **{name}** - {player.rank} ({player.mmr} MMR)\n"

    embed.description = leaderboard_text
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="queue_status", description="Check current queue status")
async def queue_status(interaction: discord.Interaction):
    embed = discord.Embed(title="📊 Queue Status", color=0x00ffcc)

    total_players = 0
    status_text = ""

    for region_code, region_name in REGIONS:
        if region_code in queues:
            region_total = 0
            for mode in queues[region_code]:
                for team_size in queues[region_code][mode]:
                    count = len(queues[region_code][mode][team_size])
                    if count > 0:
                        region_total += count
                        status_text += f"• {dict(MODES)[mode]} {team_size}: {count} players\n"

            if region_total > 0:
                embed.add_field(name=f"{region_name}", value=status_text or "No players", inline=True)
                total_players += region_total
                status_text = ""

    embed.description = f"**Total players in queue: {total_players}**"

    if total_players == 0:
        embed.description = "**No players currently in queue**"
        embed.add_field(name="🎮 Start Playing", value="Use `/dashboard` to set up matchmaking!", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_server", description="Setup OctaneScore server with all channels, roles, and categories")
async def setup_server(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only administrators can setup servers!", ephemeral=True)
        return

    await interaction.response.defer()

    guild = interaction.guild
    setup_log = []

    try:
        # Create roles
        setup_log.append("📋 **Setting up roles...**")

        # OctaneScore Staff role
        staff_role = await guild.create_role(
            name="OctaneScore Staff",
            color=discord.Color.from_rgb(255, 140, 0),
            permissions=discord.Permissions(
                manage_messages=True,
                moderate_members=True,
                kick_members=True,
                ban_members=True
            ),
            hoist=True,
            reason="OctaneScore setup - Staff role"
        )
        setup_log.append(f"✅ Created role: {staff_role.name}")

        # Verified Player role
        verified_role = await guild.create_role(
            name="Verified Player",
            color=discord.Color.from_rgb(0, 255, 204),
            hoist=True,
            reason="OctaneScore setup - Verified player role"
        )
        setup_log.append(f"✅ Created role: {verified_role.name}")

        # Member role
        member_role = await guild.create_role(
            name="Member",
            color=discord.Color.light_grey(),
            hoist=False,
            reason="OctaneScore setup - Default member role"
        )
        setup_log.append(f"✅ Created role: {member_role.name}")

        # Rank roles
        rank_roles = {}
        rank_colors = {
            "Bronze": discord.Color.from_rgb(205, 127, 50),
            "Silver": discord.Color.from_rgb(192, 192, 192),
            "Gold": discord.Color.from_rgb(255, 215, 0),
            "Platinum": discord.Color.from_rgb(0, 206, 209),
            "Diamond": discord.Color.from_rgb(185, 242, 255),
            "Champion": discord.Color.from_rgb(163, 53, 238),
            "Grand Champion": discord.Color.from_rgb(255, 69, 0),
            "Supersonic Legend": discord.Color.from_rgb(255, 0, 255)
        }

        for rank_name, color in rank_colors.items():
            role = await guild.create_role(
                name=rank_name,
                color=color,
                hoist=False,
                reason="OctaneScore setup - Rank role"
            )
            rank_roles[rank_name] = role
            setup_log.append(f"✅ Created rank role: {role.name}")

        # Create categories and channels
        setup_log.append("\n📁 **Setting up categories and channels...**")

        # Main category
        main_category = await guild.create_category(
            "🚀 OCTANESCORE",
            reason="OctaneScore setup - Main category"
        )
        setup_log.append(f"✅ Created category: {main_category.name}")

        # Read-only welcome channel
        welcome_channel = await guild.create_text_channel(
            "welcome",
            category=main_category,
            topic="Welcome to OctaneScore! Read Only - New member welcomes",
            reason="OctaneScore setup - Welcome channel"
        )
        await welcome_channel.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
        setup_log.append(f"✅ Created read-only channel: #{welcome_channel.name}")

        # Welcome discussion/introductions channel
        introductions_channel = await guild.create_text_channel(
            "introductions",
            category=main_category,
            topic="Introduce yourself to the community!",
            reason="OctaneScore setup - Introductions channel"
        )
        setup_log.append(f"✅ Created channel: #{introductions_channel.name}")

        # Dashboard channel
        dashboard_channel = await guild.create_text_channel(
            "matchmaking-dashboard",
            category=main_category,
            topic="Main OctaneScore matchmaking dashboard - Join queues here!",
            reason="OctaneScore setup - Dashboard channel"
        )
        setup_log.append(f"✅ Created channel: #{dashboard_channel.name}")

        # Read-only rules channel
        rules_channel = await guild.create_text_channel(
            "rules",
            category=main_category,
            topic="OctaneScore rules and guidelines - Read Only",
            reason="OctaneScore setup - Rules channel"
        )
        await rules_channel.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
        setup_log.append(f"✅ Created read-only channel: #{rules_channel.name}")

        # Rules discussion channel
        rules_discussion = await guild.create_text_channel(
            "rules-discussion",
            category=main_category,
            topic="Ask questions about rules and guidelines",
            reason="OctaneScore setup - Rules discussion channel"
        )
        setup_log.append(f"✅ Created channel: #{rules_discussion.name}")

        # Stats category
        stats_category = await guild.create_category(
            "📊 STATISTICS",
            reason="OctaneScore setup - Stats category"
        )
        setup_log.append(f"✅ Created category: {stats_category.name}")

        # Read-only leaderboard channel
        leaderboard_channel = await guild.create_text_channel(
            "leaderboard",
            category=stats_category,
            topic="View top players and rankings - Read Only",
            reason="OctaneScore setup - Leaderboard channel"
        )
        # Set permissions to read-only for @everyone
        await leaderboard_channel.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
        setup_log.append(f"✅ Created read-only channel: #{leaderboard_channel.name}")

        # Leaderboard discussion channel
        leaderboard_discussion = await guild.create_text_channel(
            "leaderboard-discussion",
            category=stats_category,
            topic="Discuss rankings and competitive play",
            reason="OctaneScore setup - Leaderboard discussion channel"
        )
        setup_log.append(f"✅ Created channel: #{leaderboard_discussion.name}")

        # Read-only match history channel
        match_history_channel = await guild.create_text_channel(
            "match-history",
            category=stats_category,
            topic="View all completed matches - Read Only",
            reason="OctaneScore setup - Match history channel"
        )
        await match_history_channel.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
        setup_log.append(f"✅ Created read-only channel: #{match_history_channel.name}")

        # Match history discussion channel
        match_discussion = await guild.create_text_channel(
            "match-discussion",
            category=stats_category,
            topic="Discuss matches and gameplay",
            reason="OctaneScore setup - Match discussion channel"
        )
        setup_log.append(f"✅ Created channel: #{match_discussion.name}")

        # Match results channel (for live notifications)
        results_channel = await guild.create_text_channel(
            "live-match-results",
            category=stats_category,
            topic="Live match results and notifications",
            reason="OctaneScore setup - Results channel"
        )
        await results_channel.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
        setup_log.append(f"✅ Created read-only channel: #{results_channel.name}")

        # Community category
        community_category = await guild.create_category(
            "🎮 COMMUNITY",
            reason="OctaneScore setup - Community category"
        )
        setup_log.append(f"✅ Created category: {community_category.name}")

        # General chat
        general_channel = await guild.create_text_channel(
            "general-chat",
            category=community_category,
            topic="General discussion about Rocket League",
            reason="OctaneScore setup - General channel"
        )
        setup_log.append(f"✅ Created channel: #{general_channel.name}")

        # Looking for group
        lfg_channel = await guild.create_text_channel(
            "looking-for-group",
            category=community_category,
            topic="Find teammates and organize matches",
            reason="OctaneScore setup - LFG channel"
        )
        setup_log.append(f"✅ Created channel: #{lfg_channel.name}")

        # Clips channel
        clips_channel = await guild.create_text_channel(
            "rocket-league-clips",
            category=community_category,
            topic="Post your best Rocket League clips here!",
            reason="OctaneScore setup - Clips channel"
        )
        setup_log.append(f"✅ Created channel: #{clips_channel.name}")

        # Voice channels category
        voice_category = await guild.create_category(
            "🔊 VOICE CHANNELS",
            reason="OctaneScore setup - Voice category"
        )
        setup_log.append(f"✅ Created category: {voice_category.name}")

        # General voice channel
        general_voice = await guild.create_voice_channel(
            "General Hangout",
            category=voice_category,
            reason="OctaneScore setup - General voice channel"
        )
        setup_log.append(f"✅ Created voice channel: {general_voice.name}")

        # Match voice channels
        for i in range(1, 6):
            match_voice = await guild.create_voice_channel(
                f"Match Room {i}",
                category=voice_category,
                user_limit=6,
                reason=f"OctaneScore setup - Match voice channel {i}"
            )
            setup_log.append(f"✅ Created voice channel: {match_voice.name}")

        # Team voice channels
        team_voice_1 = await guild.create_voice_channel(
            "Team Orange",
            category=voice_category,
            user_limit=3,
            reason="OctaneScore setup - Orange team voice"
        )
        setup_log.append(f"✅ Created voice channel: {team_voice_1.name}")

        team_voice_2 = await guild.create_voice_channel(
            "Team Blue",
            category=voice_category,
            user_limit=3,
            reason="OctaneScore setup - Blue team voice"
        )
        setup_log.append(f"✅ Created voice channel: {team_voice_2.name}")

        # Training voice channel
        training_voice = await guild.create_voice_channel(
            "Training Session",
            category=voice_category,
            user_limit=8,
            reason="OctaneScore setup - Training voice channel"
        )
        setup_log.append(f"✅ Created voice channel: {training_voice.name}")

        # Support category
        support_category = await guild.create_category(
            "🛠️ SUPPORT",
            reason="OctaneScore setup - Support category"
        )
        setup_log.append(f"✅ Created category: {support_category.name}")

        # Support channel
        support_channel = await guild.create_text_channel(
            "support",
            category=support_category,
            topic="Get help with OctaneScore",
            reason="OctaneScore setup - Support channel"
        )
        setup_log.append(f"✅ Created channel: #{support_channel.name}")

        # Bot commands channel
        commands_channel = await guild.create_text_channel(
            "bot-commands",
            category=support_category,
            topic="Use OctaneScore commands here",
            reason="OctaneScore setup - Commands channel"
        )
        setup_log.append(f"✅ Created channel: #{commands_channel.name}")

        # Setup dashboard in the dashboard channel
        setup_log.append("\n🎮 **Setting up matchmaking dashboard...**")

        embed = discord.Embed(
            title="🚀 OctaneScore Matchmaking Dashboard",
            description="**Welcome to OctaneScore!** Link your profile and start playing competitive Rocket League matches.",
            color=0x00ffcc
        )

        embed.add_field(
            name="🎯 How It Works",
            value="1️⃣ **Link Profile** - Connect your RL account\n2️⃣ **Select Preferences** - Choose mode, map, team size\n3️⃣ **Join Queue** - Get matched with players\n4️⃣ **Play & Report** - Complete matches and gain MMR",
            inline=False
        )

        embed.add_field(
            name="🔒 Privacy & Security",
            value="**We NEVER ask for passwords!** Only your display name is needed to create match rooms and show stats. Your Epic/Steam login stays private!",
            inline=False
        )

        embed.add_field(
            name="🌍 Supported Regions",
            value="🇺🇸 NA-East/West • 🇪🇺 Europe • 🇯🇵 Asia • 🇦🇺 Oceania • 🇧🇷 South America • 🌍 Middle East",
            inline=False
        )

        embed.add_field(
            name="🎮 Game Modes",
            value="⚽ Soccar • 🏀 Hoops • 💥 Rumble • 💎 Dropshot • 🏒 Snow Day • 🎯 Heatseeker",
            inline=False
        )

        embed.set_footer(text="OctaneScore • Advanced Rocket League Matchmaking")

        view = QueueDashboard()
        dashboard_msg = await dashboard_channel.send(embed=embed, view=view)
        setup_log.append(f"✅ Dashboard created in #{dashboard_channel.name}")

        # Track dashboard message
        dashboard_messages.append({
            "channel_id": dashboard_channel.id,
            "message_id": dashboard_msg.id,
            "guild_id": guild.id
        })

        # Create welcome message
        welcome_embed = discord.Embed(
            title="🏆 Welcome to OctaneScore!",
            description="The ultimate Rocket League competitive community!",
            color=0x00ffcc
        )
        welcome_embed.add_field(
            name="🚀 Get Started",
            value=f"Head to {dashboard_channel.mention} to link your profile and start playing!",
            inline=False
        )
        welcome_embed.add_field(
            name="📋 Rules",
            value=f"Check out {rules_channel.mention} for community guidelines.",
            inline=False
        )
        welcome_embed.add_field(
            name="🏆 Rankings",
            value=f"View the leaderboard in {leaderboard_channel.mention}!",
            inline=False
        )

        await welcome_channel.send(embed=welcome_embed)
        setup_log.append(f"✅ Welcome message created in #{welcome_channel.name}")

        # Create rules message
        rules_embed = discord.Embed(
            title="📋 OctaneScore Rules & Guidelines",
            description="Welcome to our competitive Rocket League community! Please read and follow these rules.",
            color=0xff6b6b
        )
        rules_embed.add_field(
            name="🎮 Match Rules",
            value="• Be respectful to all players\n• No toxicity or unsportsmanlike conduct\n• Report match results accurately\n• Join voice chat if available\n• No leaving matches early",
            inline=False
        )
        rules_embed.add_field(
            name="📊 Ranking System",
            value="• MMR is updated based on match results\n• Leaving queues repeatedly may result in penalties\n• Boosting or win trading is prohibited\n• Play fair and earn your rank honestly",
            inline=False
        )
        rules_embed.add_field(
            name="💬 Community Guidelines",
            value="• Keep discussions relevant to Rocket League\n• No spamming or excessive self-promotion\n• Help new players learn and improve\n• Use appropriate channels for different topics",
            inline=False
        )
        rules_embed.add_field(
            name="🛠️ Bot Usage",
            value="• Use bot commands in designated channels\n• Don't spam buttons or commands\n• Report bugs in the support channel\n• Follow matchmaking queue etiquette",
            inline=False
        )
        rules_embed.add_field(
            name="🔒 Privacy & Security",
            value="• **OctaneScore NEVER asks for passwords**\n• We only store your display name and region\n• Your Epic/Steam credentials stay private\n• We only need your username to create match rooms",
            inline=False
        )
        rules_embed.add_field(
            name="❓ Questions?",
            value=f"If you have questions about these rules, ask in {rules_discussion.mention}!",
            inline=False
        )

        await rules_channel.send(embed=rules_embed)
        setup_log.append(f"✅ Rules message created in #{rules_channel.name}")

        # Create auto-updating leaderboard
        leaderboard_embed = discord.Embed(
            title="🏆 Live Leaderboard", 
            description="Leaderboard is loading...",
            color=0xFFD700
        )
        leaderboard_embed.set_footer(text="Updates every 30 seconds")

        leaderboard_msg = await leaderboard_channel.send(embed=leaderboard_embed)
        leaderboard_messages.append({
            "channel_id": leaderboard_channel.id,
            "message_id": leaderboard_msg.id,
            "guild_id": guild.id
        })
        setup_log.append(f"✅ Auto-updating leaderboard created in #{leaderboard_channel.name}")

        # Add welcome channel to tracking
        welcome_channels.append(welcome_channel.id)
        setup_log.append(f"✅ Auto-welcome enabled in #{welcome_channel.name}")

        # Add clips channel to tracking
        clip_channels.append(clips_channel.id)
        setup_log.append(f"✅ Clips channel enabled in #{clips_channel.name}")

        setup_log.append(f"\n🎉 **Server setup complete!**")
        setup_log.append(f"📍 Dashboard: {dashboard_channel.mention}")
        setup_log.append(f"📍 Welcome: {welcome_channel.mention}")
        setup_log.append(f"📍 Introductions: {introductions_channel.mention}")
        setup_log.append(f"📍 Rules: {rules_channel.mention}")
        setup_log.append(f"📍 Rules Discussion: {rules_discussion.mention}")
        setup_log.append(f"📍 Live Leaderboard: {leaderboard_channel.mention}")
        setup_log.append(f"📍 Leaderboard Discussion: {leaderboard_discussion.mention}")
        setup_log.append(f"📍 Match History: {match_history_channel.mention}")
        setup_log.append(f"📍 Match Discussion: {match_discussion.mention}")
        setup_log.append(f"📍 Clips Channel: {clips_channel.mention}")

        # Send setup log
        final_embed = discord.Embed(
            title="✅ OctaneScore Server Setup Complete!",
            description="\n".join(setup_log),
            color=0x00ff00
        )

        await interaction.followup.send(embed=final_embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Setup Error",
            description=f"An error occurred during setup: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed)

@bot.tree.command(name="wipe_server", description="⚠️ DANGER: Completely wipe the server (delete all channels, roles, etc.)")
async def wipe_server(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only administrators can wipe servers!", ephemeral=True)
        return

    # Confirmation embed
    embed = discord.Embed(
        title="⚠️ DANGER ZONE ⚠️",
        description="**This will DELETE EVERYTHING in this server!**\n\n"
                   "This action will:\n"
                   "• Delete ALL channels\n"
                   "• Delete ALL roles (except @everyone)\n"
                   "• Delete ALL categories\n"
                   "• Remove ALL webhooks\n\n"
                   "**THIS CANNOT BE UNDONE!**",
        color=0xff0000
    )

    class WipeConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)

        @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
        async def cancel_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(title="✅ Wipe Cancelled", description="Server wipe has been cancelled.", color=0x00ff00)
            await interaction.response.edit_message(embed=embed, view=None)

        @discord.ui.button(label="💀 CONFIRM WIPE", style=discord.ButtonStyle.danger)
        async def confirm_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()

            guild = interaction.guild
            wipe_log = []

            try:
                wipe_log.append("🗑️ **Starting server wipe...**")

                # Delete all channels
                wipe_log.append("\n📁 **Deleting channels...**")
                for channel in guild.channels:
                    if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel)):
                        try:
                            await channel.delete(reason="Server wipe command")
                            wipe_log.append(f"🗑️ Deleted: {channel.name}")
                        except Exception as e:
                            wipe_log.append(f"❌ Failed to delete {channel.name}: {str(e)}")

                # Delete all roles except @everyone and bot roles
                wipe_log.append("\n👤 **Deleting roles...**")
                for role in guild.roles:
                    if role.name != "@everyone" and not role.managed:
                        try:
                            await role.delete(reason="Server wipe command")
                            wipe_log.append(f"🗑️ Deleted role: {role.name}")
                        except Exception as e:
                            wipe_log.append(f"❌ Failed to delete role {role.name}: {str(e)}")

                # Delete all webhooks
                wipe_log.append("\n🔗 **Deleting webhooks...**")
                webhooks = await guild.webhooks()
                for webhook in webhooks:
                    try:
                        await webhook.delete(reason="Server wipe command")
                        wipe_log.append(f"🗑️ Deleted webhook: {webhook.name}")
                    except Exception as e:
                        wipe_log.append(f"❌ Failed to delete webhook {webhook.name}: {str(e)}")

                wipe_log.append(f"\n💀 **Server wipe complete!**")
                wipe_log.append("Server is now completely clean and ready for setup.")

                # Create a basic channel to send the completion message
                try:
                    completion_channel = await guild.create_text_channel(
                        "server-wiped",
                        topic="Server wipe completed - Use /setup_server to rebuild",
                        reason="Server wipe completion channel"
                    )

                    final_embed = discord.Embed(
                        title="💀 Server Wipe Complete",
                        description="\n".join(wipe_log[-20:]),  # Show last 20 lines to avoid message limits
                        color=0xff0000
                    )
                    final_embed.add_field(
                        name="🚀 Next Steps",
                        value="Use `/setup_server` to rebuild the OctaneScore server structure.",
                        inline=False
                    )

                    await completion_channel.send(embed=final_embed)

                except Exception as e:
                    print(f"Failed to create completion channel: {e}")

                # Clear global data
                global dashboard_messages, leaderboard_messages, welcome_channels, clip_channels
                dashboard_messages = [msg for msg in dashboard_messages if msg["guild_id"] != guild.id]
                leaderboard_messages = [msg for msg in leaderboard_messages if msg["guild_id"] != guild.id]
                # Remove welcome channels for this guild
                guild_channels = [channel.id for channel in guild.channels]
                welcome_channels = [ch_id for ch_id in welcome_channels if ch_id not in guild_channels]
                # Remove clip channels for this guild
                clip_channels = [ch_id for ch_id in clip_channels if ch_id not in guild_channels]

            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Wipe Error",
                    description=f"An error occurred during wipe: {str(e)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed)

    view = WipeConfirmView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Background task to save data periodically
@tasks.loop(minutes=60)
async def save_data_task():
    save_data()
    print("💾 Data saved")

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)
