# Telegram Chat Administration Bot

## Overview
A comprehensive Telegram bot for managing chat groups with advanced features including user ranks, nicknames, warnings, mutes, bans, and customizable access control.

## Recent Changes
- **2025-11-21**: Initial project setup on Replit
  - Installed Python 3.11 and python-telegram-bot library
  - Created main.py with complete bot functionality
  - Added .gitignore for Python project

## Project Architecture

### Key Features
1. **Rank System**: 6 levels (0-5) from Participant to Alliance Head
2. **Nickname Management**: Users can set their own nicknames, admins can manage others
3. **Warning System**: Track warnings with automatic ban at 3 warnings
4. **Mute/Ban System**: Time-based mutes and permanent bans
5. **Access Control**: Customizable permissions for different features by rank
6. **Chat Settings**: Welcome messages, rules, and settings import/export via chat codes
7. **Creator System**: Special privileges with inheritance via "will" command

### Structure
- `main.py` - Complete bot implementation with all commands and handlers
- Uses in-memory storage (data resets on restart)
- Command handlers for Russian-language commands

### Environment Variables Required
- `BOT_TOKEN` - Telegram Bot API token (from @BotFather)

### Creator Usernames
The following usernames have automatic rank 5 access:
- mearlock
- Dean_Brown1
- Dashyha262

## User Preferences
None specified yet.

## Next Steps
- Add PostgreSQL database for persistent data storage
- Implement scheduled tasks for automatic mute expiration
- Add statistics and logging features
- Create backup/export functionality
