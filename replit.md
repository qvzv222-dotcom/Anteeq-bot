# Telegram Chat Administration Bot

## Overview
A comprehensive Telegram bot for managing chat groups with advanced features including user ranks, nicknames, warnings, mutes, bans, customizable access control, and persistent PostgreSQL storage. Running on Replit only with pure polling architecture.

## Recent Changes
- **2025-11-29**: Chat Code System with Settings Import ✅
  - Created "!код чата" command - generates code once per chat
  - Added code-based settings import/export (excludes punishments & ranks)
  - Implemented functions: get_chat_code, get_chat_id_by_code, export_chat_settings, import_chat_settings
  - Users can share configs between groups via chat codes
  
- **2025-11-28**: FINAL FIX - SQLite Database ✅
  - Migrated from PostgreSQL to **SQLite** (no more network/freezing issues!)
  - Database file: `~/.telegram_bot.db` (stored locally on Replit)
  - All data persists automatically
  - Bot fully operational and tested
  - **WORKFLOW:** `Test Bot` → Executes `python test_main.py` (polls Telegram API)
  - Health check Flask server on port 5000

## Project Architecture

### REPLIT-ONLY STRUCTURE

**Files on Replit:**
- `test_main.py` - Bot code (uses TEST_BOT_TOKEN)
- `test_db.py` - Database operations
- `profanity_list.py` - Profanity filter
- `requirements.txt` - Python dependencies

**Database:**
- SQLite locally stored (`~/.telegram_bot.db`)
- Zero network dependencies - 100% reliable
- Auto-initialized on first bot start

**Single Workflow:**
- `Test Bot` → Executes `python test_main.py` (port 5000)

**Tech Stack:**
- Language: Python 3.11
- Bot Framework: python-telegram-bot (async/await with APScheduler)
- Database: PostgreSQL (Replit built-in)
- HTTP Server: Flask (port 5000 for health checks)
- Deployment: Replit only

### Key Features
1. **Rank System**: 6 levels (0-5) from Participant to Alliance Head
2. **Nickname Management**: Users can set custom nicknames, admins manage others
3. **Warning System**: Track warnings with automatic ban at 3 warnings, 7-day expiration
4. **Mute/Ban System**: Permanent mutes (last indefinitely until `размут` command) and permanent bans
5. **Access Control**: Customizable command permissions by rank
6. **Chat Settings**: Welcome messages, rules configuration
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
- `TEST_BOT_TOKEN` - Telegram Bot API token (secret) ✅

### Creator Setup (Security)
- **Hidden Command:** `/start setcreator admin123` (in private chat with bot)
- This sets the user as creator rank 5 with full privileges
- Creator username list removed for security
- Password-protected setup prevents unauthorized creator assignment

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

### 📋 Chat Settings (Ранг 3.2 - приветствие, 3.3 - правила)
- `правила` - Show chat rules
- `+правила [text]` - Set chat rules (admin only)
- `приветствие` - Show welcome message
- `+приветствие [text]` - Set welcome message (admin only)
- `!код чата` - Show chat code for exporting settings
- `!импорт [код]` - Import settings from another chat via code

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
- ✅ Replit: Bot files (test_main.py, test_db.py, profanity_list.py)
- ✅ Database: PostgreSQL on Replit
- ✅ Workflow: Test Bot running 24/7 on Replit
- ✅ Single deployment target: Replit only

## User Preferences
- **Communication:** Russian language only (agent should speak Russian with user)
- Russian-language commands exclusively
- HTML-formatted clickable Telegram profile links (tg://user?id=)
- Moscow timezone (UTC+3) for all timestamps
- Clean architecture: everything on GitHub, nothing extra on Replit
- Production-first approach: code pushed to GitHub deploys automatically to Render
