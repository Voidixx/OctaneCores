
# 🚀 OctaneScore - Advanced Rocket League Discord Bot

**OctaneScore** is a comprehensive Discord bot designed for Rocket League communities, featuring advanced matchmaking, regional queues, and statistical tracking.

## ✨ Features

### 🎮 Core Functionality
- **Smart Matchmaking** - Region-based queue system with automatic team balancing
- **Multi-Mode Support** - Soccar, Hoops, Rumble, Dropshot, Snow Day, Heatseeker
- **Team Size Options** - 1v1, 2v2, 3v3 matches
- **Map Selection** - Choose specific maps or random selection
- **Regional Servers** - NA-East/West, EU, Asia, Oceania, South America, Middle East

### 📊 Statistics & Ranking
- **MMR System** - Skill-based rating with dynamic adjustments
- **Rank Progression** - Bronze to Supersonic Legend rankings
- **Match History** - Complete record of all played matches
- **Leaderboards** - Server-wide competitive rankings
- **Personal Stats** - Wins, losses, goals, assists, saves tracking

### 🎯 User Experience
- **Dashboard UI** - No slash commands needed for matchmaking
- **Profile Linking** - Connect Discord to Rocket League accounts
- **Real-time Notifications** - Match found alerts with room details
- **Result Reporting** - Easy match result submission
- **Queue Management** - Join/leave queues with one click

## 🚀 Quick Start

### Setup Commands
1. `/dashboard` - Create the main matchmaking dashboard (Admin only)
2. Players click "🔗 Link Profile" to connect their RL account
3. Select preferences and join queue
4. Get matched and play!

### Player Commands
- `/stats [user]` - View personal or other player statistics
- `/leaderboard` - See top-ranked players
- `/queue_status` - Check current queue activity

## 🎮 How It Works

1. **Profile Linking** - Players connect their RL username, platform, and region
2. **Queue Selection** - Choose game mode, map, team size via dropdowns
3. **Automatic Matching** - Bot pairs players every 30 seconds
4. **Room Creation** - Private match credentials provided automatically
5. **Result Reporting** - Winners submit results to update MMR/stats

## 🌍 Supported Regions
- 🇺🇸 North America (East/West)
- 🇪🇺 Europe  
- 🇯🇵 Asia
- 🇦🇺 Oceania
- 🇧🇷 South America
- 🌍 Middle East

## 🎮 Game Modes
- ⚽ **Soccar** - Classic Rocket League
- 🏀 **Hoops** - Basketball mode
- 💥 **Rumble** - Power-ups enabled
- 💎 **Dropshot** - Destructible floor
- 🏒 **Snow Day** - Hockey with puck
- 🎯 **Heatseeker** - Auto-targeting ball

## 🏆 Ranking System

| Rank | MMR Range |
|------|-----------|
| Bronze I-III | 0-399 |
| Silver I-III | 400-699 |
| Gold I-III | 700-999 |
| Platinum I-III | 1000-1299 |
| Diamond I-III | 1300-1599 |
| Champion I-III | 1600-1899 |
| Grand Champion I-III | 1900-2199 |
| Supersonic Legend | 2200+ |

## 📋 Installation

1. **Add Bot Token** - Set `BOT_TOKEN` in Replit Secrets
2. **Run Bot** - Execute `python main.py`
3. **Setup Dashboard** - Use `/dashboard` in your Discord server
4. **Invite Players** - Share the dashboard channel

## 🛠️ Technical Details

- **Built with** - discord.py 2.0+
- **Storage** - JSON file-based data persistence
- **Architecture** - Event-driven with background task queue processing
- **Deployment** - Optimized for Replit hosting with 24/7 uptime

## 📊 Data Models

### Player Profile
```json
{
  "discord_id": "123456789",
  "rl_username": "RocketPlayer",
  "platform": "Epic",
  "region": "NA-East", 
  "mmr": 1200,
  "rank": "Diamond II",
  "stats": {"wins": 25, "losses": 18, "goals": 67},
  "match_history": [...]
}
```

### Match Object
```json
{
  "match_id": "match_12345",
  "mode": "Soccar",
  "map_name": "DFH Stadium",
  "region": "NA-East",
  "team_size": "2v2",
  "players": ["player1", "player2", "player3", "player4"],
  "status": "Active",
  "room_name": "OS1234",
  "room_password": "567"
}
```

## 🎯 Perfect For

- **Rocket League Communities** - Organized competitive play
- **Discord Servers** - Enhanced member engagement  
- **Esports Teams** - Practice match coordination
- **Content Creators** - Viewer tournaments and events

---

**Ready to elevate your Rocket League Discord server?** Set up OctaneScore today and provide your community with professional-grade matchmaking!
