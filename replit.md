# Telegram Chat Administration Bot

## Overview
A comprehensive Telegram bot for managing chat groups with advanced features including user ranks, nicknames, warnings, mutes, bans, customizable access control, and persistent PostgreSQL storage. Running 24/7 on Render.com with pure polling architecture and Docker containerization.

## Recent Changes
- **2025-11-23**: Separated test and production bots into independent workflows ✅
  - Removed workflow conflicts (test_bot + main.py couldn't run simultaneously)
  - Created **Production Bot** workflow - runs main.py on Replit
  - Test Bot now runs manually from terminal: `python test_bot.py`
  - Test bot uses TEST_BOT_TOKEN, production uses BOT_TOKEN (separate tokens)
  - Workflow: Test features in test_bot.py → Copy code to main.py → `git push` → Render auto-deploys
  - No more conflicts between development and production!

- **2025-11-23**: Improved access control command (дк) with all 24 commands ✅
  - Added beautiful colored sections (🔴🟡🟢🔵🟣) for 5 command categories
  - Shows all commands with their shortcuts and current required rank
  - Now displays: "дк {команда} {требуемый ранг}" with emoji indicators

- **2025-11-23**: Fixed link filter to not block user mentions ✅
  - Removed aggressive `@\w+` pattern that was blocking "@username" mentions
  - Kept only real link patterns: http://, www., t.me/
  - Added automatic warning system for banned links
  - Links now auto-warn user and can trigger auto-ban like profanity

- **2025-11-23**: Successfully migrated to Render.com for reliable 24/7 hosting ✅
  - Uploaded code to GitHub repository (qvzv222-dotcom/Anteeq-bot)
  - Created Dockerfile and render.yaml for automatic deployments
  - Deployed Docker container on Render free tier
  - Bot is live at https://anteeq-bot.onrender.com
  - Environment variables configured: BOT_TOKEN, DATABASE_URL

## Project Architecture

### Deployment & Development Workflow
**Production:** Polling + Flask Keep-Alive on Render.com
- Bot uses polling to receive updates from Telegram API
- Flask micro-server runs on port 5000 with `/health` endpoint
- Deployed on Render free tier (~100 GB bandwidth/month, works 24/7)

**Development/Testing:** Local test_bot.py on Replit
- TEST_BOT_TOKEN for safe feature testing
- Flask on port 5001 (no conflicts with production)
- Workflow: `Test Bot` - python test_bot.py

**Tech Stack:**
- Language: Python 3.11
- Bot Framework: python-telegram-bot (async/await with job queue)
- Database: PostgreSQL (Replit built-in Neon - shared with production)
- HTTP Server: Flask (threaded)
- Deployment: Render.com (Docker)
- Version Control: GitHub (qvzv222-dotcom/Anteeq-bot)

### Key Features
1. **Rank System**: 6 levels (0-5) from Participant to Alliance Head
2. **Nickname Management**: Users can set custom nicknames, admins manage others
3. **Warning System**: Track warnings with automatic ban at 3 warnings, 7-day expiration
4. **Mute/Ban System**: Permanent mutes (last indefinitely until `размут` command) and permanent bans
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
- **mutes**: user_id, chat_id, mute_reason, mute_date (permanent mutes - no expiration)
- **bans**: user_id, chat_id, ban_reason
- **awards**: user_id, chat_id, award_name, date_given
- **chat_settings**: chat_id, welcome_message, rules, access_control (JSON)
- **chat_creators**: chat_id, creator_id (chat creator information)

### File Structure
```
.
├── main.py              # Production bot (Render)
├── test_bot.py          # Test bot for development (Replit)
├── db.py                # Database operations (PostgreSQL)
├── profanity_list.py    # Profanity filter word list
├── Dockerfile           # Docker configuration for Render
├── render.yaml          # Render deployment config
├── requirements.txt     # Python dependencies
├── .gitignore           # Git ignore rules
└── replit.md            # This file - project documentation
```

### Environment Variables Required
- `BOT_TOKEN` - Production Telegram Bot API token (Render only)
- `TEST_BOT_TOKEN` - Test Telegram Bot API token (Replit only)
- `DATABASE_URL` - PostgreSQL connection string (shared, auto-provided by Replit)
- Optional: `DEEPSEEK_API_KEY` - For AI features

### Creator Usernames (Auto Rank 5)
- mearlock
- Dean_Brown1
- Dashyha262

## Command List (Russian-language)

### System Commands
- `/start` - Start bot (private chat only)
- `помощь` or `команды` - Show help with inline buttons
- `кто ты` - Bot response: "Шо"
- `кто я` - Show your profile info

### 👤 Nickname Management (Ранг 2.1)
- `+ник [nickname]` - Set your nickname
- `-ник` - Remove your nickname
- `ник` - Check your current nickname
- `ник [@user]` - Check another user's nickname
- `ники` - List all nicknames in chat with clickable links
- `+ник другому [nickname]` - Set nickname for another user (reply required)
- `-ник другому` - Remove nickname from another user (reply required)

### ⚠️ Warning System (Ранг 1.1 - варн, 1.2 - мут/размут, 1.3 - бан/кик)
- `преды` - Show your warnings
- `преды [кол-во]` - Show warnings for replied user
- `варн [reason]` - Warn user (reply required, auto-ban at 3 warnings)
- `снять варн` - Remove last warning from user (reply required)
- `снять пред` - Alias for removing warning
- `снять все варны` - Remove all warnings from user (reply required)
- `мут [duration] [unit] [reason]` - Mute user permanently (reply required)
- `размут` - Unmute user (reply required)
- `говори` - Alias for unmuting
- `бан [reason]` - Ban user permanently (reply required)
- `разбан` - Unban user (reply required)
- `кик` - Kick user from chat (reply required)

### 📋 Chat Settings (Ранг 3.2 - приветствие, 3.3 - правила, 3.4 - роли)
- `правила` - Show chat rules
- `+правила [text]` - Set chat rules (admin only)
- `приветствие` - Show welcome message
- `+приветствие [text]` - Set welcome message (admin only)
- `!код чата` - Generate chat backup code (admin only, ранг 3.5)
- `!импорт [code]` - Import chat settings (creator only, currently unavailable)

### 👑 Administration (Ранг 3 and above)
- `администраторы` or `админы` - List all admins with ranks
- `кто создатель` - Show chat creator with profile link
- `сбор` - Ping all chat members (gather command)
- `назначить [rank]` - Assign rank to user (0-5, reply required, ранг 1.3)
- `!завещание [@user]` - Transfer creator status to user (creator only)
- `-завещание` - Remove creator status (creator only)
- `дк` - Show access control settings (ранг 3.7)
- `дк [section] [rank]` - Change access control for specific command section

### 🎁 Reward System (Ранг 4)
- `!наградить @user [award_name]` - Give award to user (reply required)
- `!снять награды` - Remove all awards from user (reply required)
- `Наградной список` - Show all users with awards

### 🚫 Moderation Filters
- `+маты` - Enable profanity filter (ранг 3.8)
- `-маты` - Disable profanity filter (ранг 3.8)
- `!преды [number]` - Set max warnings before auto-ban (default 3, ранг 3.8)

### 📊 History & Logs (Ранг 3.6)
- `история наказаний` - Show full chat punishment journal (chat-wide)
- `очистить историю наказаний` - Clear entire punishment history (creator only)
- `наказания` - Show your personal punishment history (any user)

### 🔒 Access Control (ДК) Sections
Access levels 0-5: Участник → Модератор → Наборщик → Заместитель → Глава клана → Глава альянса

**Command Sections:**
- `1.1` - Warn command (default: rank 1)
- `1.2` - Mute/Unmute commands (default: rank 1)
- `1.3` - Ban/Kick/Assign rank commands (default: rank 1)
- `1.4` - View other users' warnings (default: rank 1)
- `1.5` - Set/Remove creator status (default: rank 5)
- `2.1` - Nickname management for self (default: rank 2)
- `2.2` - Nickname management for others (default: rank 2)
- `3.1` - Manage chat roles/ranks (default: rank 3)
- `3.2` - Set welcome message (default: rank 3)
- `3.3` - Set chat rules (default: rank 3)
- `3.4` - Manage role settings (default: rank 3)
- `3.5` - Generate chat code (default: rank 3)
- `3.6` - View punishment history (default: rank 3)
- `3.7` - Access control management (default: rank 3)
- `3.8` - Profanity filter management (default: rank 3)
- `4` - Reward system (default: rank 4)

## Development Workflow

### Adding New Features
1. **Edit test_bot.py** on Replit to test new commands/features
2. **Test in a private chat** or test group with test bot
3. **Copy working code to main.py** once verified
4. **Commit and push to GitHub**:
   ```bash
   git add main.py
   git commit -m "Add new feature: [description]"
   git push
   ```
5. **Render automatically deploys** - production bot updates within minutes

### Running Both Bots Simultaneously
- Production bot: Workflow `Telegram Bot` (python main.py) → Render deployment
- Test bot: Workflow `Test Bot` (python test_bot.py) → Local testing

### Database Notes
- Both bots share same PostgreSQL database
- Changes in test_bot.py affect production data (be careful!)
- Test in isolated chats to avoid data pollution

## Render Free Tier Details

### Limits
- **Bandwidth**: 100 GB/month (for Telegram bot = essentially unlimited)
- **Uptime**: 24/7 (no sleep like Replit free tier)
- **Build time**: 500 minutes/month shared
- **Cost**: Completely FREE for single bot

### Scaling Notes
- Single bot can handle 1000+ users without issues
- Bandwidth (18 MB/month typical) uses only 0.018% of 100 GB limit
- Perfect for hobby/small-medium projects

## User Preferences
- Russian-language commands exclusively
- HTML-formatted clickable Telegram profile links (tg://user?id=)
- Moscow timezone (UTC+3) for all timestamps
- Safe testing workflow with separate test bot
- Development-first approach: test locally before pushing to production
