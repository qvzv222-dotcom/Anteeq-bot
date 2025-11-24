# Telegram Chat Administration Bot

## Overview
A comprehensive Telegram bot for managing chat groups with advanced features including user ranks, nicknames, warnings, mutes, bans, customizable access control, and persistent PostgreSQL storage. Running 24/7 on Render.com with pure polling architecture and Docker containerization.

## Recent Changes
- **2025-11-24**: Complete cleanup - production bot only ✅
  - Removed ALL test bot files from Replit (test_main.py, test_db.py, test_profanity_list.py)
  - Kept ONLY: main.py, db.py, profanity_list.py on Replit (copied from GitHub)
  - Entire codebase stored on GitHub: qvzv222-dotcom/Anteeq-bot
  - Production Bot workflow runs main.py with BOT_TOKEN
  - **WORKFLOW:** Download from GitHub → Run on Replit → Render auto-deploys

## Project Architecture

### CLEAN STRUCTURE: Everything on GitHub

**Files on GitHub (Source of Truth):**
- `main.py` - Production bot code
- `db.py` - Database operations
- `profanity_list.py` - Profanity filter
- `Dockerfile` - Docker config
- `render.yaml` - Render deployment
- `requirements.txt` - Dependencies
- `.gitignore` - Git ignore rules

**Files on Replit (Local Copy):**
- Same 3 Python files: `main.py`, `db.py`, `profanity_list.py`
- Copied from GitHub to run locally
- Production Bot workflow executes main.py

**Deployment Flow:**
1. **Edit code:** Modify on Replit (test locally first)
2. **Push to GitHub:** `git add -A && git commit -m "..." && git push`
3. **Render auto-deploys:** Docker builds and runs on render.com
4. **Both running:** Replit (workflow) + Render (production) with same code

**Single Workflow:**
- `Production Bot` → Executes `python main.py` on Replit (port 5000)

**Tech Stack:**
- Language: Python 3.11
- Bot Framework: python-telegram-bot (async/await with APScheduler)
- Database: PostgreSQL (Replit Neon + Render)
- HTTP Server: Flask (port 5000 for health checks)
- Deployment: Render.com Docker (24/7 production)
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

### File Structure (GitHub)
```
.
├── main.py              # Production bot code
├── db.py                # Database operations
├── profanity_list.py    # Profanity filter word list
├── Dockerfile           # Docker configuration for Render
├── render.yaml          # Render deployment config
├── requirements.txt     # Python dependencies
├── .gitignore           # Git ignore rules
└── replit.md            # This file - project documentation
```

### Environment Variables Required
- `BOT_TOKEN` - Production Telegram Bot API token (GitHub secret)
- `DATABASE_URL` - PostgreSQL connection string (Render + Replit)

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

### 👑 Administration (Ранг 3 and above)
- `администраторы` or `админы` - List all admins with ranks
- `кто создатель` - Show chat creator with profile link
- `сбор` - Ping all chat members (gather command)
- `назначить [rank]` - Assign rank to user (0-5, reply required, ранг 1.3)
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

## Development Workflow

### To Add New Features:
1. **Edit main.py, db.py, profanity_list.py** on Replit
2. **Test locally** with Production Bot workflow
3. **Push to GitHub:**
   ```bash
   git add main.py db.py profanity_list.py
   git commit -m "Add new feature: [description]"
   git push
   ```
4. **Render auto-deploys** - production bot updates within minutes

### Current Status:
- ✅ Replit: Clean (only 3 production files)
- ✅ GitHub: Single source of truth (main.py, db.py, profanity_list.py)
- ✅ Render: 24/7 production bot
- ✅ All code from GitHub

## User Preferences
- Russian-language commands exclusively
- HTML-formatted clickable Telegram profile links (tg://user?id=)
- Moscow timezone (UTC+3) for all timestamps
- Clean architecture: everything on GitHub, nothing extra on Replit
- Production-first approach: code pushed to GitHub deploys automatically to Render
