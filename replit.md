# Telegram Chat Administration Bot

## Overview
A comprehensive Telegram bot for managing chat groups with advanced features including user ranks, nicknames, warnings, mutes, bans, customizable access control, and persistent PostgreSQL storage. Running 24/7 on Render.com with pure polling architecture and Docker containerization.

## Recent Changes
- **2025-11-23**: Dual-bot development setup ✅
  - Created test_bot.py for safe development and testing
  - Test bot uses TEST_BOT_TOKEN (separate from production BOT_TOKEN)
  - Test bot workflow runs on port 5001 (production on 5000)
  - Development workflow: Test new features locally → GitHub → Render production deploy
  - Both bots can run simultaneously for parallel testing

- **2025-11-23**: Successfully migrated to Render.com for reliable 24/7 hosting ✅
  - Uploaded code to GitHub repository (qvzv222-dotcom/Anteeq-bot)
  - Created Dockerfile and render.yaml for automatic deployments
  - Deployed Docker container on Render free tier
  - Bot is live at https://anteeq-bot.onrender.com
  - Removed Flask keep-alive complexity - pure polling is more stable
  - Bot successfully responding to all commands
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
