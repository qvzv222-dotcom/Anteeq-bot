import os
import logging
import random
import string
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import db
from profanity_list import contains_profanity

app = Flask(__name__)

@app.route('/')
def health_check():
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}, 200

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logging.getLogger('httpx').setLevel(logging.WARNING)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("Ошибка: BOT_TOKEN не найден!")
    print("Добавьте BOT_TOKEN в переменные окружения")
    exit(1)

CREATORS = ['mearlock', 'Dean_Brown1', 'Dashyha262']

def generate_chat_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def is_creator_username(username: Optional[str]) -> bool:
    if not username:
        return False
    return username in CREATORS

def get_user_rank(chat_id: int, user_id: int) -> int:
    return db.get_user_rank(chat_id, user_id)

def has_access(chat_id: int, user_id: int, section: str) -> bool:
    access_control = db.get_access_control(chat_id)
    required_rank = access_control.get(section, 5)
    user_rank = get_user_rank(chat_id, user_id)
    return user_rank >= required_rank

async def check_and_set_creator_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.message.chat_id
    creator = db.get_chat_creator(chat_id)
    
    if not creator:
        return
    
    try:
        creator_member = await context.bot.get_chat_member(chat_id, creator)
        if creator_member:
            db.set_user_rank(chat_id, creator, 5)
    except:
        pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    
    try:
        bot = context.bot
        bot_username = bot.username or "YourBotName"
    except:
        bot_username = "YourBotName"
    
    welcome_text = f"""👋 Привет! Я администрационный бот для управления группами в Telegram.

🎯 Основные возможности:
• 👤 Система ников для участников
• ⚠️ Система наказаний (варны, муты, баны)
• 👑 Ранговая система (0-5 уровней)
• 📋 Правила чата и приветствия
• 🎁 Система наград за активность
• 🚫 Фильтр нецензурной лексики

Чтобы добавить меня в группу, нажмите кнопку ниже 👇"""
    
    keyboard = [[InlineKeyboardButton("➕ Добавить в группу", url=f"https://t.me/{bot_username}?startgroup=true")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "help_command":
        keyboard = [
            [InlineKeyboardButton("👤 Ники", callback_data="nicks_help"), InlineKeyboardButton("⚠️ Преды", callback_data="warns_help")],
            [InlineKeyboardButton("📋 Правила", callback_data="rules_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        help_text = """<b>📖 СПРАВКА ПО КОМАНДАМ БОТА</b>

<b>👤 УПРАВЛЕНИЕ НИКАМАМИ</b>
  • <code>+ник [ник]</code> - установить свой ник
  • <code>-ник</code> - удалить свой ник
  • <code>ники</code> - список всех ников

<b>👑 АДМИНИСТРИРОВАНИЕ</b>
  • <code>админы</code> - список администраторов
  • <code>дк</code> - управление правами доступа

<b>⚠️ СИСТЕМА НАКАЗАНИЙ</b>
  • <code>преды</code> - посмотреть свои предупреждения
  • <code>преды [ответ]</code> - показать преды пользователю

<b>📋 ПРАВИЛА И ИНФОРМАЦИЯ</b>
  • <code>правила</code> - показать правила чата
  • <code>приветствие</code> - показать приветствие чата
  • <code>помощь</code> - показать эту справку

Нажмите на кнопки ниже для подробной информации:
""".strip()
        
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    if data == "nicks_help":
        text = """<b>👤 УПРАВЛЕНИЕ НИКАМАМИ</b>

<code>+ник [ник]</code> - установить себе ник
Пример: <code>+ник Assassin</code>

<code>-ник</code> - удалить свой ник

<code>ники</code> - показать список всех ников в чате

Администраторы могут:
  • Устанавливать ники другим пользователям
  • Удалять ники других пользователей"""
    elif data == "warns_help":
        text = """<b>⚠️ СИСТЕМА ПРЕДУПРЕЖДЕНИЙ</b>

Пользователи:
  • <code>преды</code> - посмотреть свои предупреждения
  
Администраторы могут:
  • Давать предупреждения
  • Снимать предупреждения
  • Выдавать мут и бан"""
    elif data == "rules_help":
        text = """<b>📋 ПРАВИЛА И ИНФОРМАЦИЯ</b>

<code>правила</code> - показать правила чата

<code>приветствие</code> - показать приветственное сообщение

Администраторы могут устанавливать правила
и приветствие через команду <code>дк</code>"""
    else:
        return

    keyboard = [
        [InlineKeyboardButton("👤 Ники", callback_data="nicks_help"), InlineKeyboardButton("⚠️ Преды", callback_data="warns_help")],
        [InlineKeyboardButton("📋 Правила", callback_data="rules_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def chat_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.5"):
        await update.message.reply_text("Недостаточно прав")
        return

    existing_code = db.get_chat_code(chat_id)
    if existing_code:
        code = existing_code
    else:
        code = generate_chat_code()
        db.set_chat_code(chat_id, code)

    text = f"""📋 Код чата: <code>{code}</code>

Используйте этот код для импорта настроек чата.
Чтобы импортировать: <code>!импорт {code}</code>"""
    await update.message.reply_text(text, parse_mode='HTML')

async def import_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)
    
    if creator != user_id:
        await update.message.reply_text("Только создатель может импортировать настройки")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: !импорт [код]")
        return

    source_code = parts[1]
    source_chat_id = db.get_chat_id_by_code(source_code)
    
    if not source_chat_id:
        await update.message.reply_text(f"Чат с кодом {source_code} не найден")
        return

    welcome = db.get_welcome_message(source_chat_id)
    rules = db.get_rules(source_chat_id)
    access_control = db.get_access_control(source_chat_id)
    
    db.set_welcome_message(chat_id, welcome)
    db.set_rules(chat_id, rules)
    db.set_access_control(chat_id, access_control)
    
    await update.message.reply_text("✅ Настройки импортированы")

async def set_will(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)

    if creator != user_id:
        await update.message.reply_text("Только создатель может оставить завещание")
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user

    if not target_user:
        await update.message.reply_text("Укажите пользователя через ответ на сообщение")
        return

    db.set_chat_creator(chat_id, target_user.id)
    await update.message.reply_text(f"Статус создателя передан пользователю {target_user.first_name}")

async def remove_will(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)

    if creator != user_id:
        await update.message.reply_text("Только создатель может отменить завещание")
        return

    db.set_chat_creator(chat_id, None)
    await update.message.reply_text("Завещание отменено. Статус создателя будет автоматически установлен для следующего пользователя из списка создателей.")

async def show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    welcome_text = db.get_welcome_message(chat_id)
    chat_title = update.message.chat.title or "Чат"
    welcome_text = welcome_text.replace("[***]", chat_title).replace("ANT-X", chat_title)
    await update.message.reply_text(welcome_text)

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: +приветствие [текст]")
        return

    welcome_text = parts[1]
    db.set_welcome_message(chat_id, welcome_text)
    await update.message.reply_text("Приветственное сообщение обновлено")

async def show_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    admins = db.get_all_admins(chat_id)

    if not admins:
        await update.message.reply_text("✅ В чате нет администраторов")
        return

    rank_names = {
        0: "Участник",
        1: "Модератор чата", 
        2: "Наборщик",
        3: "Заместитель главы клана",
        4: "Глава клана",
        5: "Глава альянса"
    }

    admins_text = "👑 Администраторы чата:\n\n"
    for user_id, rank in admins.items():
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            full_name = user.user.first_name
            if user.user.last_name:
                full_name += f" {user.user.last_name}"
            user_link = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
            rank_name = rank_names.get(rank, "Неизвестный ранг")
            admins_text += f"{user_link} — {rank_name}\n"
        except:
            continue

    await update.message.reply_text(admins_text.strip(), parse_mode='HTML')

async def show_creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    creator_id = db.get_chat_creator(chat_id)

    if not creator_id:
        await update.message.reply_text("❌ Создатель этого чата не определён")
        return

    try:
        user = await context.bot.get_chat_member(chat_id, creator_id)
        full_name = user.user.first_name
        if user.user.last_name:
            full_name += f" {user.user.last_name}"
        user_link = f"<a href='tg://user?id={creator_id}'>{full_name}</a>"
        await update.message.reply_text(f"👑 <b>Создатель чата:</b> {user_link}", parse_mode='HTML')
    except:
        await update.message.reply_text(f"❌ Не удалось получить информацию о создателе (ID: {creator_id})")

async def gather_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.3"):
        await update.message.reply_text("Недостаточно прав")
        return

    try:
        chat_members = await context.bot.get_chat_member_count(chat_id)
        await update.message.reply_text(
            f"📢 Сбор клана!\n\nВсего участников: {chat_members}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

async def set_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.4"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение и напишите 'назначить [ранг]'")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: назначить [число от 0 до 5]")
        return

    try:
        rank = int(parts[1])
        if rank < 0 or rank > 5:
            await update.message.reply_text("Ранг должен быть от 0 до 5")
            return
    except ValueError:
        await update.message.reply_text("Ранг должен быть числом")
        return

    target_user = update.message.reply_to_message.from_user
    db.set_user_rank(chat_id, target_user.id, rank)
    await update.message.reply_text(f"Ранг пользователя {target_user.first_name} установлен на {rank}")

async def set_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: +ник [ник]")
        return

    nick = parts[1]
    if len(nick) > 50:
        await update.message.reply_text("Ник не может быть длиннее 50 символов")
        return

    db.set_nick(chat_id, user_id, nick)
    await update.message.reply_text(f"✅ Ваш ник установлен: {nick}")

async def remove_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    nick = db.get_nick(chat_id, user_id)
    
    if not nick:
        await update.message.reply_text("❌ У вас нет установленного ника")
        return

    db.remove_nick(chat_id, user_id)
    await update.message.reply_text("✅ Ваш ник удален")

async def set_nick_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_rank = db.get_user_rank(chat_id, user_id)

    if not has_access(chat_id, user_id, "2.1"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите '+ник другому [ник]'")
        return

    target_user = update.message.reply_to_message.from_user
    target_rank = db.get_user_rank(chat_id, target_user.id)

    if user_rank <= target_rank:
        await update.message.reply_text("❌ Вы можете установить ник только пользователю с более низким рангом")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: +ник другому [ник]")
        return

    nick = parts[1]
    db.set_nick(chat_id, target_user.id, nick)
    await update.message.reply_text(f"✅ Ник '{nick}' установлен пользователю {target_user.first_name}")

async def remove_nick_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_rank = db.get_user_rank(chat_id, user_id)

    if not has_access(chat_id, user_id, "2.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите '-ник другому'")
        return

    target_user = update.message.reply_to_message.from_user
    target_rank = db.get_user_rank(chat_id, target_user.id)

    if user_rank <= target_rank:
        await update.message.reply_text("❌ Вы можете удалить ник только пользователю с более низким рангом")
        return

    nick = db.get_nick(chat_id, target_user.id)
    
    if nick:
        db.remove_nick(chat_id, target_user.id)
        await update.message.reply_text(f"Ник пользователя {target_user.first_name} удален")
    else:
        await update.message.reply_text(f"У пользователя {target_user.first_name} нет установленного ника")

async def show_nicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    nicks = db.get_all_nicks(chat_id)

    if not nicks:
        await update.message.reply_text("✅ В чате нет установленных ников")
        return

    nicks_text = "📋 Список ников чата:\n\n"
    for i, (user_id, nick) in enumerate(nicks.items(), 1):
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            full_name = user.user.first_name
            if user.user.last_name:
                full_name += f" {user.user.last_name}"
            user_link = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
            nicks_text += f"{i}. {nick} — {user_link}\n"
        except:
            continue

    nicks_text += f"\n📊 Всего ников: {len(nicks)}"
    await update.message.reply_text(nicks_text.strip(), parse_mode='HTML')

async def get_nick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    target_user_id = None
    
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    else:
        text = update.message.text.strip()
        parts = text.split()
        
        if len(parts) > 1:
            username_arg = parts[1]
            if username_arg.startswith('@'):
                username_arg = username_arg[1:]
            
            try:
                member = await context.bot.get_chat_member(chat_id, f"@{username_arg}")
                target_user_id = member.user.id
            except:
                await update.message.reply_text(f"❌ Пользователь @{username_arg} не найден")
                return
        else:
            target_user_id = user_id
    
    nick = db.get_nick(chat_id, target_user_id)
    
    if not nick:
        if target_user_id == user_id:
            await update.message.reply_text("❌ У вас нет установленного ника")
        else:
            try:
                user = await context.bot.get_chat_member(chat_id, target_user_id)
                user_link = f"<a href='tg://user?id={target_user_id}'>{user.user.first_name}</a>"
                await update.message.reply_text(f"❌ У {user_link} нет установленного ника", parse_mode='HTML')
            except:
                await update.message.reply_text("❌ Ник не установлен")
    else:
        if target_user_id == user_id:
            await update.message.reply_text(f"🏷️ <b>Ваш ник:</b> {nick}", parse_mode='HTML')
        else:
            try:
                user = await context.bot.get_chat_member(chat_id, target_user_id)
                user_link = f"<a href='tg://user?id={target_user_id}'>{user.user.first_name}</a>"
                await update.message.reply_text(f"🏷️ <b>Ник {user_link}:</b> {nick}", parse_mode='HTML')
            except:
                await update.message.reply_text(f"🏷️ <b>Ник:</b> {nick}", parse_mode='HTML')

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    rules = db.get_rules(chat_id)
    await update.message.reply_text(rules)

async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.1"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: +правила [текст правил]")
        return

    rules_text = parts[1]
    db.set_rules(chat_id, rules_text)
    await update.message.reply_text("Правила чата обновлены")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.4"):
        await update.message.reply_text("Недостаточно прав")
        return

    target_user = None
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Причина не указана"

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user

    if not target_user:
        await update.message.reply_text("Использование: ответом на сообщение 'варн [причина]'")
        return

    if target_user.id == user_id:
        await update.message.reply_text("❌ Вы не можете давать предупреждения себе", parse_mode='HTML')
        return

    if target_user.id == context.bot.id:
        await update.message.reply_text("❌ Вы не можете наказать бота", parse_mode='HTML')
        return

    db.add_warn(chat_id, target_user.id, user_id, reason)
    warn_count = db.get_warn_count(chat_id, target_user.id)
    user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"

    if warn_count >= 3:
        db.add_ban(chat_id, target_user.id)
        await update.message.reply_text(
            f"{user_link} получил 3 предупреждения и был забанен",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"{user_link} получил предупреждение ({warn_count}/3)\nПричина: {reason}",
            parse_mode='HTML'
        )

async def show_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    target_user = update.message.from_user
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user

    warns = db.get_warns(chat_id, target_user.id)
    
    if not warns:
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"✅ У {user_link} нет предупреждений", parse_mode='HTML')
        return

    user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    total_warns = len(warns)
    
    warns_text = f"""
⠀╔════════════════════════════════════╗
║ㅤㅤㅤㅤㅤ 📋 ИСТОРИЯ ПРЕДУПРЕЖДЕНИЙㅤㅤ⠀⠀⠀⠀⠀║
⠀╚════════════════════════════════════╝

"""

    for i, warn in enumerate(warns, 1):
        try:
            admin = await context.bot.get_chat_member(chat_id, warn['from_user_id'])
            admin_link = f"<a href='tg://user?id={warn['from_user_id']}'>{admin.user.first_name}</a>"
        except:
            admin_link = "Неизвестно"

        warn_date = warn['warn_date']
        if isinstance(warn_date, str):
            from datetime import datetime
            warn_date = datetime.fromisoformat(warn_date.replace('Z', '+00:00'))
        
        msk_offset = timedelta(hours=3)
        warn_date_msk = warn_date + msk_offset
        expires_date_msk = warn_date_msk + timedelta(days=7)
        
        date_str = warn_date_msk.strftime("%d.%m.%Y %H:%M")
        expires_date = expires_date_msk.strftime("%d.%m.%Y %H:%M")
        
        warns_text += f"""⚠️ <b>{user_link} предупреждения ({i}/{3})</b>
📅 Выдано: {date_str}
⏰ Истекает: {expires_date}
📝 Причина: {warn['reason']}
🛡️ Модератор: {admin_link}

"""

    warns_text += "\n🕐 <i>Время указано по МСК (UTC+3)</i>"
    await update.message.reply_text(warns_text.strip(), parse_mode='HTML')

async def remove_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_rank = db.get_user_rank(chat_id, user_id)
    creator = db.get_chat_creator(chat_id)
    is_creator = creator == user_id

    if not is_creator and not has_access(chat_id, user_id, "1.5"):
        await update.message.reply_text("❌ Недостаточно прав для снятия предупреждений")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'снять пред'")
        return

    target_user = update.message.reply_to_message.from_user

    if target_user.id == context.bot.id:
        await update.message.reply_text("❌ Вы не можете наказать бота", parse_mode='HTML')
        return

    target_rank = db.get_user_rank(chat_id, target_user.id)

    if not is_creator and user_rank < target_rank:
        await update.message.reply_text("❌ Вы не можете снять предупреждение у пользователя с более высоким рангом")
        return

    warns = db.get_warns(chat_id, target_user.id)

    if not warns:
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"У {user_link} нет предупреждений", parse_mode='HTML')
        return

    last_warn = db.get_last_warn_details(chat_id, target_user.id)
    if last_warn and not is_creator:
        giver_rank = db.get_user_rank(chat_id, last_warn['from_user_id'])
        if user_rank <= giver_rank:
            await update.message.reply_text("❌ Вы не можете снять предупреждение, выданное модератором равного или выше ранга")
            return

    db.remove_last_warn(chat_id, target_user.id)
    warn_count = db.get_warn_count(chat_id, target_user.id)
    max_warns = db.get_max_warns(chat_id)
    
    if db.is_banned(chat_id, target_user.id) and warn_count < max_warns:
        db.remove_ban(chat_id, target_user.id)

    user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    await update.message.reply_text(
        f"Предупреждение снято с {user_link}\nОсталось предупреждений: {warn_count}/{max_warns}",
        parse_mode='HTML'
    )

async def remove_all_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Снять все предупреждения пользователю"""
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_rank = db.get_user_rank(chat_id, user_id)
    creator = db.get_chat_creator(chat_id)
    is_creator = creator == user_id

    if not is_creator and not has_access(chat_id, user_id, "1.5"):
        await update.message.reply_text("❌ Недостаточно прав для снятия предупреждений")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'снять все преды'")
        return

    target_user = update.message.reply_to_message.from_user
    target_rank = db.get_user_rank(chat_id, target_user.id)

    if not is_creator and user_rank < target_rank:
        await update.message.reply_text("❌ Вы не можете снять предупреждения у пользователя с более высоким рангом")
        return

    warns = db.get_warns(chat_id, target_user.id)

    if not warns:
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"У {user_link} нет предупреждений", parse_mode='HTML')
        return

    if not is_creator:
        highest_warn_giver_rank = db.get_highest_warn_giver_rank(chat_id, target_user.id)
        if user_rank <= highest_warn_giver_rank:
            await update.message.reply_text("❌ Вы не можете снять предупреждения, выданные модератором равного или выше ранга")
            return

    db.remove_all_warns(chat_id, target_user.id)
    
    if db.is_banned(chat_id, target_user.id):
        db.remove_ban(chat_id, target_user.id)

    user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    await update.message.reply_text(
        f"✅ Все предупреждения сняты с {user_link}",
        parse_mode='HTML'
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.3"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'бан [причина]'")
        return

    target_user = update.message.reply_to_message.from_user

    if target_user.id == user_id:
        await update.message.reply_text("❌ Вы не можете банить себя", parse_mode='HTML')
        return

    if target_user.id == context.bot.id:
        await update.message.reply_text("❌ Вы не можете наказать бота", parse_mode='HTML')
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Причина не указана"

    db.ban_user(chat_id, target_user.id, reason)

    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(
            f"{user_link} забанен\nПричина: {reason}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при бане: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)
    is_creator = creator == user_id

    if not is_creator and not has_access(chat_id, user_id, "1.3"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'разбан'")
        return

    target_user = update.message.reply_to_message.from_user

    db.remove_ban(chat_id, target_user.id)

    try:
        await context.bot.unban_chat_member(chat_id, target_user.id)
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"{user_link} разбанен", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"Ошибка при разбане: {str(e)}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.3"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'кик'")
        return

    target_user = update.message.reply_to_message.from_user

    if target_user.id == user_id:
        await update.message.reply_text("❌ Вы не можете кикать себя", parse_mode='HTML')
        return

    if target_user.id == context.bot.id:
        await update.message.reply_text("❌ Вы не можете наказать бота", parse_mode='HTML')
        return

    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        await context.bot.unban_chat_member(chat_id, target_user.id)
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"{user_link} исключен из чата", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"Ошибка при кике: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.1"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    target_user = None
    duration = 60
    unit = "минут"
    reason = "Временное ограничение сообщений"
    
    # Вариант 1: Ответ на сообщение - мут 5 с причина
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        if len(parts) > 1:
            try:
                duration = int(parts[1])
                if len(parts) > 2:
                    unit_str = parts[2].lower()
                    if unit_str in ['с', 'сек', 'секунд']:
                        unit = "секунд"
                    elif unit_str in ['м', 'мин', 'минут']:
                        unit = "минут"
                    if len(parts) > 3:
                        reason = " ".join(parts[3:])
            except ValueError:
                pass
    
    # Вариант 2: По user_id - мут 123456789 5 с причина
    elif len(parts) >= 4:
        user_id_input = parts[1]
        
        # Парсим параметры
        try:
            duration = int(parts[2])
            unit_str = parts[3].lower()
            if unit_str in ['с', 'сек', 'секунд']:
                unit = "секунд"
            elif unit_str in ['м', 'мин', 'минут']:
                unit = "минут"
            
            if len(parts) > 4:
                reason = " ".join(parts[4:])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Ошибка: неверный формат")
            return
        
        # Проверяем, не пытается ли пользователь использовать @username
        if user_id_input.startswith('@'):
            await update.message.reply_text(f"❌ @username не поддерживается (ограничение Telegram API)\n\n💡 Вместо этого:\n1️⃣ Ответьте на сообщение: мут 5 м причина\n2️⃣ Используйте числовой ID: мут 123456789 5 с причина\n\n📱 Как узнать ID: пересчитайте на сообщение пользователя и используйте его ID")
            return
        
        # Ищем пользователя по числовому ID
        try:
            lookup_id = int(user_id_input)
        except ValueError:
            await update.message.reply_text(f"❌ ID должно быть числом (например: 123456789)")
            return
        
        # Получаем информацию о пользователе
        try:
            member = await context.bot.get_chat_member(chat_id, lookup_id)
            target_user = member.user
        except Exception as e:
            await update.message.reply_text(f"❌ Пользователь с ID {user_id_input} не найден в чате")
            return
    else:
        await update.message.reply_text("Использование:\n1️⃣ Ответьте на сообщение: мут 5 м причина\n2️⃣ По ID: мут 123456789 5 с причина")
        return

    if not target_user:
        await update.message.reply_text("❌ Не удалось получить информацию о пользователе")
        return

    if target_user.id == user_id:
        await update.message.reply_text("❌ Вы не можете мутить себя", parse_mode='HTML')
        return

    if target_user.id == context.bot.id:
        await update.message.reply_text("❌ Вы не можете наказать бота", parse_mode='HTML')
        return

    if not reason or reason == "Временное ограничение сообщений":
        reason = "Шоб не втыкал"

    db.mute_user(chat_id, target_user.id, reason)

    try:
        await context.bot.restrict_chat_member(
            chat_id, 
            target_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(
            f"{user_link} замучен на {duration} {unit}\nПричина: {reason}",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при муте: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)
    is_creator = creator == user_id

    if not is_creator and not has_access(chat_id, user_id, "1.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'размут'")
        return

    target_user = update.message.reply_to_message.from_user

    db.unmute_user(chat_id, target_user.id)

    try:
        await context.bot.restrict_chat_member(
            chat_id,
            target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"{user_link} размучен", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"Ошибка при размуте: {str(e)}")

async def access_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.7"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=2)
    
    if len(parts) < 2:
        access_control = db.get_access_control(chat_id)
        
        info = """<b>⚙️ УПРАВЛЕНИЕ ПРАВАМИ ДОСТУПА</b>

Текущие требуемые ранги для команд:
"""
        for section, rank in sorted(access_control.items()):
            rank_names = {0: "Участник", 1: "Модератор", 2: "Наборщик", 3: "Замести", 4: "Глава", 5: "Альянс"}
            info += f"\n{section}: {rank_names.get(rank, rank)}"
        
        info += "\n\nИспользование: <code>дк [раздел] [ранг]</code>"
        
        await update.message.reply_text(info, parse_mode='HTML')
        return
    
    section = parts[1]
    try:
        rank = int(parts[2])
    except (ValueError, IndexError):
        await update.message.reply_text("Ранг должен быть числом от 0 до 5")
        return
    
    if rank < 0 or rank > 5:
        await update.message.reply_text("Ранг должен быть от 0 до 5")
        return
    
    db.set_access_control_section(chat_id, section, rank)
    await update.message.reply_text(f"✅ Раздел {section} теперь требует ранг {rank}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_text = """📚 СПРАВКА ПО КОМАНДАМ:

<b>👤 Ники:</b>
<code>+ник [ник]</code> - установить свой ник
<code>-ник</code> - удалить свой ник
<code>ники</code> - список всех ников

<b>👑 Администрирование:</b>
<code>назначить [ранг]</code> - назначить ранг (ответом)
<code>дк [раздел] [ранг]</code> - управление доступом

<b>⚠️ Наказания:</b>
<code>варн [причина]</code> - дать предупреждение (ответом)
<code>преды</code> - показать свои предупреждения
<code>снять пред</code> - снять последнее предупреждение (ответом)
<code>мут [время] [с/м]</code> - замутить (ответом)
<code>размут</code> - размутить (ответом)
<code>бан [причина]</code> - забанить (ответом)
<code>разбан</code> - разбанить (ответом)
<code>кик</code> - кикнуть (ответом)

<b>📋 Правила:</b>
<code>+правила [текст]</code> - установить правила
<code>правила</code> - показать правила
<code>+приветствие [текст]</code> - установить приветствие
<code>приветствие</code> - показать приветствие

<b>ℹ️ Информация:</b>
<code>админы</code> - список администраторов
<code>сбор</code> - упоминание всех участников
<code>помощь</code> - эта справка"""

    await update.message.reply_text(commands_text, parse_mode='HTML')

async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_command(update, context)

async def who_is_this(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответьте на сообщение пользователя")
        return
    
    target_user = update.message.reply_to_message.from_user
    user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    await update.message.reply_text(f"Это {user_link}", parse_mode='HTML')

async def who_am_i(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_link = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    await update.message.reply_text(f"Это ты: {user_link}", parse_mode='HTML')

async def bot_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Шо")

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    await check_and_set_creator_rank(update, context)

    creator = db.get_chat_creator(chat_id)
    bot_was_added = any(user.is_bot for user in update.message.new_chat_members)
    
    if not creator:
        if bot_was_added:
            db.set_chat_creator(chat_id, update.message.from_user.id)
            db.set_user_rank(chat_id, update.message.from_user.id, 5)
        elif is_creator_username(update.message.from_user.username):
            db.set_chat_creator(chat_id, update.message.from_user.id)
            db.set_user_rank(chat_id, update.message.from_user.id, 5)
        else:
            db.set_chat_creator(chat_id, update.message.from_user.id)
            db.set_user_rank(chat_id, update.message.from_user.id, 5)

    for user in update.message.new_chat_members:
        if user.is_bot:
            continue

        if is_creator_username(user.username):
            db.set_user_rank(chat_id, user.id, 5)

        welcome_text = db.get_welcome_message(chat_id)
        chat_title = update.message.chat.title or "Чат"
        welcome_text = welcome_text.replace("[***]", chat_title).replace("ANT-X", chat_title)
        
        nick = db.get_nick(chat_id, user.id)
        if nick:
            welcome_text += f"\nТвой ник: {nick}"

        await update.message.reply_text(welcome_text)
    
    if bot_was_added:
        capabilities_text = """✅ <b>БОТ ДОБАВЛЕН В ГРУППУ!</b>

⚠️ <b>ВАЖНО:</b> Выдайте боту <b>ВСЕ ПРАВА АДМИНИСТРАТОРА</b> для полной работы!

🚀 <b>ФУНКЦИИ:</b>
• Система наказаний (мут, бан, кик, преды)
• Управление никнеймами
• Система рангов (0-5 уровней)
• Фильтр мата и доступ к командам
• Правила и приветствия чата
• Система вознаграждений

Для изучения действующих команд нажмите кнопку ниже:"""
        
        keyboard = [[InlineKeyboardButton("📚 Помощь", callback_data="help_command")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(capabilities_text, parse_mode='HTML', reply_markup=reply_markup)

async def check_profanity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    profanity_enabled = db.is_profanity_filter_enabled(chat_id)
    
    if not profanity_enabled:
        return
    
    text = update.message.text.lower()
    
    if contains_profanity(text):
        user = update.message.from_user
        user_id = user.id
        
        await update.message.delete()
        
        db.add_warn(chat_id, user_id, chat_id, "Использование нецензурной лексики")
        
        warns = db.get_warns(chat_id, user_id)
        warn_count = len(warns) if warns else 0
        max_warns = db.get_max_warns(chat_id)
        
        if warn_count >= max_warns:
            db.add_ban(chat_id, user_id)
            await context.bot.send_message(
                chat_id,
                f"❌ Пользователь {user.first_name} забанен за использование мата ({warn_count}+ предупреждения)"
            )
        else:
            user_link = f"<a href='tg://user?id={user_id}'>{user.first_name}</a>"
            await context.bot.send_message(
                chat_id,
                f"⚠️ {user_link} предупреждение за мат ({warn_count}/{max_warns})",
                parse_mode='HTML'
            )

async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    user_rank = db.get_user_rank(chat_id, user_id)
    
    link_posting_rank = db.get_link_posting_rank(chat_id)
    
    if user_rank < link_posting_rank:
        text = update.message.text
        link_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'(?:www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r't\.me/\S+',
            r'@\w+'
        ]
        
        for pattern in link_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                await update.message.delete()
                return

async def enable_profanity_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.8"):
        await update.message.reply_text("Недостаточно прав")
        return

    db.enable_profanity_filter(chat_id)
    await update.message.reply_text("✅ Фильтр мата включен")

async def disable_profanity_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.8"):
        await update.message.reply_text("Недостаточно прав")
        return

    db.disable_profanity_filter(chat_id)
    await update.message.reply_text("✅ Фильтр мата отключен")

async def reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "4"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение и напишите '!наградить [награда]'")
        return

    target_user = update.message.reply_to_message.from_user
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    reward = parts[1] if len(parts) > 1 else "Спасибо"

    db.add_award(chat_id, target_user.id, reward)
    await update.message.reply_text(f"✅ {target_user.first_name} награжден: {reward}")

async def remove_awards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "4"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение и напишите '!снять награды'")
        return

    target_user = update.message.reply_to_message.from_user
    db.remove_awards(chat_id, target_user.id)
    await update.message.reply_text(f"✅ Награды {target_user.first_name} удалены")

async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    awards = db.get_all_awards(chat_id)

    if not awards:
        await update.message.reply_text("📊 Нет выданных наград")
        return

    awards_text = "🏆 Награждённые участники:\n\n"
    for user_id, reward in awards.items():
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            full_name = user.user.first_name
            if user.user.last_name:
                full_name += f" {user.user.last_name}"
            user_link = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
            awards_text += f"⭐ {user_link} — {reward}\n"
        except:
            continue

    await update.message.reply_text(awards_text.strip(), parse_mode='HTML')

async def set_max_warns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "3.7"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        max_warns = db.get_max_warns(chat_id)
        await update.message.reply_text(f"Текущий лимит предупреждений: {max_warns}\nИспользование: !преды [число]")
        return

    try:
        max_warns = int(parts[1])
        if max_warns < 1:
            await update.message.reply_text("Лимит должен быть не менее 1")
            return
    except ValueError:
        await update.message.reply_text("Лимит должен быть числом")
        return

    db.set_max_warns(chat_id, max_warns)
    await update.message.reply_text(f"✅ Лимит предупреждений установлен: {max_warns}")

async def moderation_log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    if not has_access(chat_id, user_id, "1.1"):
        await update.message.reply_text("Недостаточно прав")
        return
    
    log_data = db.get_moderation_log(chat_id)
    
    if not log_data:
        await update.message.reply_text("📋 История наказаний пуста")
        return
    
    log_text = "📋 <b>ЖУРНАЛ МОДЕРАЦИИ</b>\n\n"
    
    for record in log_data[:50]:
        user_id_punished = record['user_id']
        punishment_type = record['punishment_type']
        reason = record['punishment_reason'] or "Не указана"
        date = record['punishment_date']
        
        if date:
            formatted_date = date.strftime("%d.%m.%Y %H:%M")
        else:
            formatted_date = "Неизвестно"
        
        type_emoji = {
            'предупреждение': '⚠️',
            'мут': '🤐',
            'бан': '🚫'
        }.get(punishment_type, '📌')
        
        log_text += f"{type_emoji} <b>{punishment_type.capitalize()}</b>\n"
        log_text += f"👤 ID: {user_id_punished}\n"
        log_text += f"📝 Причина: {reason}\n"
        log_text += f"🕐 Дата: {formatted_date}\n\n"
    
    if len(log_data) > 50:
        log_text += f"... и ещё {len(log_data) - 50} записей"
    
    await update.message.reply_text(log_text, parse_mode='HTML')

def setup_handlers(application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(help_command|nicks_help|warns_help|rules_help)"))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кто ты'), who_is_this))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кто я$'), who_am_i))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^бот$'), bot_response))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^помощь$'), help_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^команды$'), commands_list))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!код чата$'), chat_code_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!импорт'), import_settings))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!завещание'), set_will), group=1)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-завещание'), remove_will), group=1)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^приветствие$'), show_welcome))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+приветствие'), set_welcome))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^админы$'), show_admins))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кто создатель$'), show_creator))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^сбор$'), gather_members))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^назначить\s+'), set_rank))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+ник другому\s+'), set_nick_other))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-ник другому$'), remove_nick_other))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^ник(?:\s|$)'), get_nick_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+ник\s+'), set_nick))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-ник$'), remove_nick))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^ники$'), show_nicks))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^правила$'), show_rules))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+правила'), set_rules))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(?:снять все преды|снять все варны)'), remove_all_warns))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(?:снять пред|снять варн)'), remove_warn))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(?:варн|пред)(?:\s|$)'), warn_user))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^разбан'), unban_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кик'), kick_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^бан'), ban_user))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(размут|говори)'), unmute_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^мут'), mute_user))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^дк'), access_control_command))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!наградить'), reward_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!снять награды'), remove_awards_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^Наградной список$'), show_participants))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^история наказаний$'), moderation_log_command))

    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+маты$'), enable_profanity_filter))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-маты$'), disable_profanity_filter))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!преды'), set_max_warns_command))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
    
    # Check profanity first
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_profanity), group=1)
    
    # Check links last (after all command handlers) to avoid blocking commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_links), group=100)

def main():
    print("Инициализация базы данных...")
    db.init_database()
    
    print("Инициализация бота...")
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
    
    print("✅ Бот инициализирован!")
    print("Добавьте бота в группу и дайте ему права администратора!")
    
    # Start Flask health check server in background thread
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Flask health check server started on port 5000")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        time.sleep(5)

if __name__ == '__main__':
    main()
