# Telegram Chat Administration Bot

## Overview
A comprehensive Telegram bot for managing chat groups with advanced features including user ranks, nicknames, warnings, mutes, bans, customizable access control, and persistent PostgreSQL storage. Running 24/7 on Render.com with pure polling architecture and Docker containerization.

## Recent Changes
- **2025-11-23**: Successfully migrated to Render.com for reliable 24/7 hosting ✅
  - Uploaded code to GitHub repository (qvzv222-dotcom/Anteeq-bot)
  - Created Dockerfile and render.yaml for automatic deployments
  - Deployed Docker container on Render free tier
  - Bot is live at https://anteeq-bot.onrender.com
  - Removed Flask keep-alive complexity - pure polling is more stable
  - Bot successfully responding to all commands
  - Environment variables configured: BOT_TOKEN, DATABASE_URL

- **2025-11-22**: Enhanced keep-alive mechanism
  - Added aggressive background pinger thread (every 30 seconds)
  - Implemented dual-threaded approach for maximum uptime
  
- **2025-11-21**: Initial project setup on Replit
  - Installed Python 3.11 and python-telegram-bot library
  - Created main.py with complete bot functionality
  - Set up PostgreSQL database for persistent storage
  - Added .gitignore for Python project

## Project Architecture

### Deployment & Uptime Strategy
**Current: Polling + Flask Keep-Alive (Production-Ready)**
- Bot uses polling to receive updates from Telegram API (reliable on free tier)
- Flask micro-server runs on port 5000 with `/health` endpoint
- UptimeRobot pings the `/health` endpoint every 5 minutes
- External monitoring prevents Replit free tier from hibernating the project
- Survives Replit restarts - automatically reconnects to Telegram polling

**Tech Stack:**
- Language: Python 3.11
- Bot Framework: python-telegram-bot (async/await with job queue)
- Database: PostgreSQL (Replit built-in Neon)
- HTTP Server: Flask (threaded)
- Uptime Monitoring: UptimeRobot (free tier)
- Optional: pyngrok support for tunneling (if needed for webhook approach)

### Key Features
1. **Rank System**: 6 levels (0-5) from Participant to Alliance Head
2. **Nickname Management**: Users can set custom nicknames, admins manage others
3. **Warning System**: Track warnings with automatic ban at 3 warnings, 7-day expiration
4. **Mute/Ban System**: Time-based mutes (configurable duration) and permanent bans
5. **Access Control**: Customizable command permissions by rank
6. **Chat Settings**: Welcome messages, rules, settings import/export via chat codes
7. **Creator System**: Special rank 5 privileges with "will" command inheritance
8. **Reward System**: Award and manage user awards/achievements
9. **Profanity Filter**: Auto-warn on profanity, configurable max warnings
10. **Member Gathering**: "Сбор" command to ping all members
11. **Nickname Listing**: "Ники" command shows all nicknames with clickable links
12. **Creator Display**: "Кто создатель" shows chat creator with profile link

### Database Schema
- **users_ranks**: user_id, chat_id, rank (persistent user ranks)
- **nicks**: user_id, chat_id, nickname (persistent nicknames)
- **warns**: user_id, chat_id, from_user_id, reason, warn_date, warn_number
- **mutes**: user_id, chat_id, mute_until (timestamp)
- **bans**: user_id, chat_id, ban_reason
- **awards**: user_id, chat_id, award_name, date_given
- **chat_settings**: chat_id, welcome_message, rules, access_control (JSON)
- **chat_creators**: chat_id, creator_id (chat creator information)

### File Structure
```
.
├── main.py              # Main bot with all command handlers and Flask server
├── db.py                # Database operations (PostgreSQL)
├── profanity_list.py    # Profanity filter word list
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules
└── replit.md           # This file - project documentation
```

### Environment Variables Required
- `BOT_TOKEN` - Telegram Bot API token (from @BotFather)
- `DATABASE_URL` - PostgreSQL connection string (auto-provided by Replit)
- Optional: `DEEPSEEK_API_KEY` - For AI features

### Creator Usernames (Auto Rank 5)
- mearlock
- Dean_Brown1
- Dashyha262

## Command List (Russian-language)

### Admin Commands
- `админы` - Show all administrators
- `кто создатель` - Show chat creator
- `сбор` - Ping all members ("gather")
- `назначить @user X` - Set user rank (0-5)
- `варн @user [reason]` - Warn user (auto-ban at 3)
- `мут @user [duration]` - Mute user for duration
- `бан @user [reason]` - Ban user permanently
- `кик @user` - Kick user from chat

### User Commands
- `+ник my_nickname` - Set your nickname
- `-ник` - Remove your nickname
- `ник [@user]` - Check your or another user's nickname
- `ники` - List all nicknames in chat
- `профиль` - Show your profile with rank and stats
- `правила` - Show chat rules
- `приветствие` - Show welcome message

### Moderation Commands
- `+маты` - Enable profanity filter
- `-маты` - Disable profanity filter
- `!преды X` - Set max warnings before auto-ban (default 3)
- `снять варн @user` - Remove warning
- `снять все варны @user` - Remove all warnings

### Settings Commands
- `+правила [text]` - Set chat rules
- `+приветствие [text]` - Set welcome message
- `!код чата` - Get chat backup code
- `!импорт [code]` - Import chat settings
- `!завещание [@user]` - Set rank inheritance for when you leave

### Reward Commands
- `!наградить @user [award_name]` - Give award to user
- `!снять награды @user` - Remove all awards
- `Наградной список` - Show participants with awards

## User Preferences
- Uses Russian-language commands exclusively
- HTML-formatted clickable Telegram profile links (tg://user?id=)
- Moscow timezone (UTC+3) for all timestamps
- Bot is protected from being punished (can't warn/mute/ban itself)
- Dynamic welcome messages with actual chat name

## Uptime Configuration

### UptimeRobot Setup (Required for 24/7 uptime)
1. Create account at https://uptimerobot.com
2. Create new HTTP(S) monitor:
   - **URL**: `https://your-replit-url.replit.dev/health`
   - **Type**: HTTP(s)
   - **Interval**: 5 minutes
   - **Name**: "Telegram Bot Keep-alive"
3. Monitor will ping the `/health` endpoint every 5 minutes
4. This prevents Replit free tier from hibernating the bot

### Workflow Configuration
- **Workflow name**: `Telegram Bot`
- **Command**: `python main.py`
- **Output type**: `console`
- Auto-restarts on file changes and package installations

## How It Works

### Polling Loop
1. Application starts and initializes database
2. Flask server starts on port 5000 in background thread
3. Bot begins polling Telegram API for updates
4. When message arrives, appropriate handler processes it
5. UptimeRobot pings `/health` endpoint every 5 minutes
6. Replit sees external traffic → keeps project active

### Keep-Alive Mechanism
- Flask `/` and `/health` endpoints respond to any request
- `/health` returns JSON with current timestamp and status
- UptimeRobot external pings count as "user activity" for Replit
- Even if Replit restarts the container, polling automatically resumes

## Future Improvements
- Scheduled auto-mute expiration (using job queue)
- Statistics and analytics dashboard
- Backup/export functionality with encryption
- Integration with other monitoring services
- Webhook support (requires permanent URL via ngrok/cloudflare)
