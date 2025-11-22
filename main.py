import os
import logging
import random
import string
import re
from datetime import datetime, timedelta
from typing import Optional
import threading
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from flask import Flask

import db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logging.getLogger('httpx').setLevel(logging.WARNING)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("Ошибка: BOT_TOKEN не найден!")
    print("Добавьте BOT_TOKEN в Secrets (Environment Variables)")
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
    
    creator = db.get_chat_creator(chat_id)
    if creator == user_id:
        return True
    
    return user_rank >= required_rank

async def check_expired_mutes(context: ContextTypes.DEFAULT_TYPE):
    expired_mutes = db.get_expired_mutes()
    
    for chat_id, user_id in expired_mutes:
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            user_link = f"<a href='tg://user?id={user_id}'>{user.user.first_name}</a>"
            await context.bot.send_message(
                chat_id,
                f" Срок наказания {user_link} истек. Пользователь размучен.",
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об истечении мута: {str(e)}")
        finally:
            db.remove_mute(chat_id, user_id)

async def check_and_set_creator_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    
    user = update.message.from_user
    chat_id = update.message.chat_id
    
    if is_creator_username(user.username):
        current_rank = db.get_user_rank(chat_id, user.id)
        if current_rank < 5:
            db.set_user_rank(chat_id, user.id, 5)
            creator = db.get_chat_creator(chat_id)
            if not creator:
                db.set_chat_creator(chat_id, user.id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👤 Ники", callback_data="nicks_help"), InlineKeyboardButton("⚠️ Преды", callback_data="warns_help")],
        [InlineKeyboardButton("📋 Правила", callback_data="rules_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = """
╔═══════════════════════════════════════╗
║  📖 СПРАВКА ПО КОМАНДАМ БОТА  📖  ║
╚═══════════════════════════════════════╝

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

    await update.message.reply_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "nicks_help":
        text = """<b>👤 УПРАВЛЕНИЕ НИКАМАМИ</b>

<code>+ник [ник]</code> - установить себе ник
Пример: <code>+ник Assassin</code>

<code>-ник</code> - удалить свой ник

<code>ники</code> - показать список всех ников в чате
         с указанием кто их установил"""
    elif data == "admins_help":
        text = """<b>👑 АДМИНИСТРАТОРЫ</b>

<code>админы</code> - показать список администраторов чата

<code>дк</code> - открыть панель управления доступом
Позволяет настроить минимальный ранг для:
  • Изменения прав доступа
  • Установки никнеймов
  • Управления наградами
  • И других функций"""
    elif data == "warns_help":
        text = """<b>⚠️ СИСТЕМА ПРЕДУПРЕЖДЕНИЙ</b>

<code>преды</code> - посмотреть свои предупреждения

<code>преды</code> (ответом на сообщение) - показать преды пользователю

<b>❌ 3 предупреждения = БАН</b>

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

    await query.edit_message_text(text, parse_mode='HTML')

async def chat_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "4"):
        await update.message.reply_text("Недостаточно прав")
        return

    chat_code = db.get_chat_code(chat_id)
    if not chat_code:
        chat_code = generate_chat_code()
        db.set_chat_code(chat_id, chat_code)

    await update.message.reply_text(f"Код чата: {chat_code}")

async def import_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "4"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: !импорт [код]")
        return

    source_code = parts[1].upper()
    source_chat_id = db.find_chat_by_code(source_code)

    if not source_chat_id:
        await update.message.reply_text("Чат с таким кодом не найден")
        return

    db.import_chat_settings(chat_id, source_chat_id)
    await update.message.reply_text("Настройки успешно импортированы")

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

    rank_emoji = {
        0: "👤",
        1: "🛡️",
        2: "📌",
        3: "⚜️",
        4: "👑",
        5: "🏆"
    }

    admins_text = "👨‍💼 <b>АДМИНИСТРАТОРЫ ЧАТА</b>\n\n"
    for user_id, rank in sorted(admins.items(), key=lambda x: x[1], reverse=True):
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            rank_name = rank_names.get(rank, "Неизвестно")
            emoji = rank_emoji.get(rank, "•")
            user_link = f"<a href='tg://user?id={user_id}'>{user.user.first_name}</a>"
            admins_text += f"{emoji} <b>{rank_name}</b>\n→ {user_link}\n\n"
        except:
            continue

    admins_text += f"📊 <i>Всего администраторов: {len(admins)}</i>"
    await update.message.reply_text(admins_text.strip(), parse_mode='HTML')

async def gather_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    if not has_access(chat_id, user_id, "7"):
        await update.message.reply_text("Недостаточно прав")
        return
    
    members = db.get_all_members(chat_id)
    
    if not members:
        await update.message.reply_text("В чате нет участников")
        return
    
    mentions = "🔔 <b>СБОР КЛАНА!</b>\n\n"
    count = 0
    try:
        for member_id in members:
            try:
                user = await context.bot.get_chat_member(chat_id, member_id)
                mention = f"<a href='tg://user?id={member_id}'>{user.user.first_name}</a>"
                mentions += mention + " "
                count += 1
            except:
                continue
    except:
        pass
    
    mentions += f"\n\n📢 Собрание объявлено! ({count} участников)"
    await update.message.reply_text(mentions, parse_mode='HTML')

async def set_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)

    if creator != user_id:
        await update.message.reply_text("Только создатель может назначать ранги")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'назначить [ранг]'")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        await update.message.reply_text(
            "Использование: назначить [ранг]\n\n"
            "Ранги:\n"
            "0 - Участник\n"
            "1 - Модератор чата\n"
            "2 - Наборщик\n"
            "3 - Заместитель главы клана\n"
            "4 - Глава клана\n"
            "5 - Глава альянса"
        )
        return

    try:
        rank = int(parts[1])
        if rank < 0 or rank > 5:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Ранг должен быть числом от 0 до 5")
        return

    target_user = update.message.reply_to_message.from_user
    
    rank_names = {
        0: "Участник",
        1: "Модератор чата",
        2: "Наборщик",
        3: "Заместитель главы клана",
        4: "Глава клана",
        5: "Глава альянса"
    }

    db.set_user_rank(chat_id, target_user.id, rank)
    
    if rank == 0:
        await update.message.reply_text(f"Пользователь {target_user.first_name} теперь обычный участник")
    else:
        await update.message.reply_text(
            f"Пользователю {target_user.first_name} назначен ранг: {rank_names[rank]}"
        )

async def set_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "2.1"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text("Использование: +ник [никнейм]")
        return

    nick = parts[1]
    db.set_nick(chat_id, user_id, nick)
    await update.message.reply_text(f"Ваш ник установлен: {nick}")

async def remove_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "2.1"):
        await update.message.reply_text("Недостаточно прав")
        return

    nick = db.get_nick(chat_id, user_id)
    if nick:
        db.remove_nick(chat_id, user_id)
        await update.message.reply_text("Ваш ник удален")
    else:
        await update.message.reply_text("У вас нет установленного ника")

async def set_nick_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "2.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите '+ник другому [никнейм]'")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=2)
    
    if len(parts) < 3:
        await update.message.reply_text("Использование: +ник другому [никнейм]")
        return

    target_user = update.message.reply_to_message.from_user
    nick = parts[2]
    db.set_nick(chat_id, target_user.id, nick)
    await update.message.reply_text(f"Ник для пользователя {target_user.first_name} установлен: {nick}")

async def remove_nick_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "2.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите '-ник другому'")
        return

    target_user = update.message.reply_to_message.from_user
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
            nicks_text += f"{i}️⃣ {nick} — {user_link}\n"
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
    creator = db.get_chat_creator(chat_id)
    is_creator = creator == user_id

    if not is_creator and not has_access(chat_id, user_id, "1.5"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'снять пред'")
        return

    target_user = update.message.reply_to_message.from_user

    warns = db.get_warns(chat_id, target_user.id)

    if not warns:
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(f"У {user_link} нет предупреждений", parse_mode='HTML')
        return

    db.remove_last_warn(chat_id, target_user.id)
    warn_count = db.get_warn_count(chat_id, target_user.id)
    
    if db.is_banned(chat_id, target_user.id) and warn_count < 3:
        db.remove_ban(chat_id, target_user.id)

    user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
    await update.message.reply_text(
        f"Предупреждение снято с {user_link}\nОсталось предупреждений: {warn_count}/3",
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

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Причина не указана"

    db.add_ban(chat_id, target_user.id)

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

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'мут [время] [с/м]'\nПример: мут 10 с (10 секунд) или мут 5 м (5 минут)")
        return

    target_user = update.message.reply_to_message.from_user

    if target_user.id == user_id:
        await update.message.reply_text("❌ Вы не можете мутить себя", parse_mode='HTML')
        return

    text = update.message.text.strip()
    parts = text.split()
    
    duration = 60
    unit = "минут"
    
    if len(parts) > 1:
        try:
            duration = int(parts[1])
            if len(parts) > 2:
                suffix = parts[2].lower()
                if suffix in ['с', 'сек', 'секунд']:
                    duration = duration
                    unit = "секунд"
                elif suffix in ['м', 'мин', 'минут']:
                    duration = duration
                    unit = "минут"
            else:
                unit = "минут"
        except ValueError:
            duration = 60
            unit = "минут"

    if unit == "секунд":
        unmute_time = datetime.now() + timedelta(seconds=duration)
    else:
        unmute_time = datetime.now() + timedelta(minutes=duration)
    
    db.set_mute(chat_id, target_user.id, unmute_time)

    try:
        await context.bot.restrict_chat_member(
            chat_id, 
            target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=unmute_time
        )
        user_link = f"<a href='tg://user?id={target_user.id}'>{target_user.first_name}</a>"
        await update.message.reply_text(
            f"{user_link} замучен на {duration} {unit}",
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

    db.remove_mute(chat_id, target_user.id)

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

async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    link_pattern = r'https?://|www\.'
    if re.search(link_pattern, update.message.text):
        required_rank = db.get_link_posting_rank(chat_id)
        user_rank = get_user_rank(chat_id, user_id)
        
        if user_rank < required_rank:
            db.add_ban(chat_id, user_id)
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                user_link = f"<a href='tg://user?id={user_id}'>{update.message.from_user.first_name}</a>"
                await update.message.reply_text(f"{user_link} забанен за постинг ссылки", parse_mode='HTML')
            except Exception as e:
                logging.error(f"Ошибка при бане за ссылку: {str(e)}")

async def reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    required_rank = db.get_award_giving_rank(chat_id)
    user_rank = get_user_rank(chat_id, user_id)
    
    if user_rank < required_rank:
        await update.message.reply_text("Недостаточно прав для выдачи наград")
        return
    
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text(
            "Использование:\n"
            "1. Ответьте на сообщение и напишите: !наградить {название награды}\n"
            "2. Или: !наградить @username {название награды}"
        )
        return
    
    award_name = parts[1]
    target_user_id = None
    
    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    else:
        if award_name.startswith('@'):
            parts_award = award_name.split(maxsplit=1)
            username = parts_award[0][1:]
            award_name = parts_award[1] if len(parts_award) > 1 else "Награда"
            
            try:
                member = await context.bot.get_chat_member(chat_id, f"@{username}")
                target_user_id = member.user.id
            except Exception as e:
                await update.message.reply_text(f"Не найден пользователь @{username}")
                return
    
    if not target_user_id:
        await update.message.reply_text("Укажите пользователя или ответьте на сообщение")
        return
    
    db.add_award(chat_id, target_user_id, award_name)
    
    try:
        target_user = await context.bot.get_chat_member(chat_id, target_user_id)
        user_link = f"<a href='tg://user?id={target_user_id}'>{target_user.user.first_name}</a>"
        await update.message.reply_text(f"✨ {user_link} получил награду: {award_name}", parse_mode='HTML')
    except:
        user_link = f"<a href='tg://user?id={target_user_id}'>Пользователь</a>"
        await update.message.reply_text(f"✨ {user_link} получил награду: {award_name}", parse_mode='HTML')

async def remove_awards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответьте на сообщение пользователя, чтобы снять награды")
        return
    
    target_user_id = update.message.reply_to_message.from_user.id
    
    if target_user_id != user_id:
        if not has_access(chat_id, user_id, "3"):
            await update.message.reply_text("Недостаточно прав для снятия наград других пользователей")
            return
    
    db.remove_all_awards(chat_id, target_user_id)
    
    try:
        target_user = await context.bot.get_chat_member(chat_id, target_user_id)
        user_link = f"<a href='tg://user?id={target_user_id}'>{target_user.user.first_name}</a>"
        await update.message.reply_text(f"❌ Все награды сняты с {user_link}", parse_mode='HTML')
    except:
        await update.message.reply_text("❌ Все награды сняты")

async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    users = db.get_all_users_in_chat(chat_id)
    
    if not users:
        await update.message.reply_text("Нет участников")
        return
    
    rank_names = {
        0: "Участник",
        1: "Модератор чата",
        2: "Наборщик",
        3: "Заместитель главы клана",
        4: "Глава клана",
        5: "Глава альянса"
    }
    
    current_rank = None
    message = ""
    
    for user in users:
        if user['rank'] != current_rank:
            if message:
                message += "\n"
            current_rank = user['rank']
            message += f"\n📊 {rank_names.get(current_rank, 'Неизвестный ранг')}:\n"
        
        try:
            member = await context.bot.get_chat_member(chat_id, user['user_id'])
            user_name = member.user.first_name
            username = member.user.username
            user_display = f"<a href='tg://user?id={user['user_id']}'>{user_name}</a>"
        except Exception as e:
            logging.error(f"Ошибка при получении информации о пользователе: {e}")
            user_display = f"@{user['user_id']}"
        
        message += f"  • {user_display}"
        
        if user['awards']:
            awards_str = ", ".join(user['awards'])
            message += f" | {awards_str}"
        else:
            message += f" | нет наград"
        
        message += "\n"
    
    if message:
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("Нет участников")

def get_section_from_command(command: str) -> str:
    command_lower = command.lower().strip()
    
    if command_lower == "мут":
        return "1.1"
    elif command_lower in ["размут", "говори"]:
        return "1.2"
    elif command_lower in ["бан", "разбан", "кик"]:
        return "1.3"
    elif command_lower in ["варн", "пред"]:
        return "1.4"
    elif command_lower in ["снять пред", "снять варн"]:
        return "1.5"
    elif command_lower in ["+ник", "-ник"]:
        return "2.1"
    elif command_lower in ["+ник другому", "-ник другому"]:
        return "2.2"
    elif command_lower in ["правила", "+правила"]:
        return "3.1"
    elif command_lower == "+приветствие":
        return "3.2"
    elif command_lower == "админы":
        return "3.1"
    elif command_lower == "ссылки":
        return "5"
    elif command_lower == "награды":
        return "6"
    elif command_lower == "сбор":
        return "7"
    else:
        return None

async def access_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "4"):
        await update.message.reply_text("Недостаточно прав")
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        access_control = db.get_access_control(chat_id)
        link_posting_rank = db.get_link_posting_rank(chat_id)
        award_giving_rank = db.get_award_giving_rank(chat_id)
        
        rank_emoji = {0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣"}
        
        r_1_1 = access_control.get('1.1', 1)
        r_1_2 = access_control.get('1.2', 1)
        r_1_3 = access_control.get('1.3', 3)
        r_1_4 = access_control.get('1.4', 1)
        r_1_5 = access_control.get('1.5', 1)
        r_2_1 = access_control.get('2.1', 0)
        r_2_2 = access_control.get('2.2', 2)
        r_3_1 = access_control.get('3.1', 3)
        r_3_2 = access_control.get('3.2', 3)
        r_4 = access_control.get('4', 4)
        
        help_text = (
            "⚙️ Изменить доступ к команде: <b>дк {команда} {требуемый ранг}</b>\n\n"
            "🔴 <b>РАЗДЕЛ 1: Система наказаний</b>\n"
            f"1.1. 🔇 Мут: <i>мут</i> {rank_emoji[r_1_1]}\n"
            f"1.2. 🔊 Размут: <i>размут, говори</i> {rank_emoji[r_1_2]}\n"
            f"1.3. 🔨 Бан и кик: <i>бан, разбан, кик</i> {rank_emoji[r_1_3]}\n"
            f"1.4. ⚠️ Выдать предупреждение: <i>пред, варн</i> {rank_emoji[r_1_4]}\n"
            f"1.5. 🔓 Снять предупреждение: <i>снять пред, снять варн</i> {rank_emoji[r_1_5]}\n\n"
            "🟡 <b>РАЗДЕЛ 2: Система ников</b>\n"
            f"2.1. ✏️ Установить себе ник: <i>+ник</i> {rank_emoji[r_2_1]}\n"
            f"2.2. 🗑️ Удалить себе ник: <i>-ник</i> {rank_emoji[r_2_1]}\n"
            f"2.3. 📝 Установить ник участнику: <i>+ник другому</i> {rank_emoji[r_2_2]}\n"
            f"2.4. ❌ Удалить ник участнику: <i>-ник другому</i> {rank_emoji[r_2_2]}\n\n"
            "🟢 <b>РАЗДЕЛ 3: Информирование</b>\n"
            f"3.1. 📋 Узнать правила: <i>правила</i> {rank_emoji[r_3_1]}\n"
            f"3.2. ✍️ Изменить правила: <i>+правила</i> {rank_emoji[r_3_1]}\n"
            f"3.3. 👋 Сообщение приветствия: <i>приветствие</i> {rank_emoji[r_3_2]}\n"
            f"3.4. 📢 Изменить приветствие: <i>+приветствие</i> {rank_emoji[r_3_2]}\n"
            f"3.5. 👨‍💼 Список администраторов: <i>админы</i> {rank_emoji[r_3_1]}\n\n"
            "🔵 <b>РАЗДЕЛ 4: Администраторские</b>\n"
            f"4.1. 🛡️ Доступ к командам: <i>дк</i> {rank_emoji[r_4]}\n"
            f"4.2. 🔗 Разрешить ссылки: <i>дк ссылки [ранг]</i> {rank_emoji[link_posting_rank]}\n"
            f"4.3. 🔔 Сбор клана: <i>сбор</i> {rank_emoji[access_control.get('7', 1)]}\n\n"
            "🟣 <b>РАЗДЕЛ 5: Система вознаграждения</b>\n"
            f"5.1. 🏆 Выдача наград: <i>!наградить {{награда}}</i> {rank_emoji[award_giving_rank]}\n"
            f"5.2. ✂️ Снятие наград: <i>!снять награды</i> {rank_emoji[award_giving_rank]}\n"
            "5.3. 🎖️ Посмотреть награды: <i>Наградной список</i> 0️⃣\n"
            f"5.4. 🎯 Изменить ранг награждения: <i>дк награды [ранг]</i> {rank_emoji[r_4]}"
        )
        
        await update.message.reply_text(help_text, parse_mode='HTML')
        return

    command_part = parts[1]
    cmd_parts = command_part.rsplit(maxsplit=1)
    
    if len(cmd_parts) < 2:
        await update.message.reply_text("Использование: дк {команда} {требуемый ранг}")
        return
    
    command_name = cmd_parts[0]
    try:
        rank = int(cmd_parts[1])
        if rank < 0 or rank > 5:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Ранг должен быть числом от 0 до 5")
        return

    section = get_section_from_command(command_name)
    if section is None:
        await update.message.reply_text(f"Неизвестная команда: {command_name}")
        return

    if section == "5":
        db.set_link_posting_rank(chat_id, rank)
    elif section == "6":
        db.set_award_giving_rank(chat_id, rank)
    else:
        access_control = db.get_access_control(chat_id)
        access_control[section] = rank
        db.set_access_control(chat_id, access_control)

    section_names = {
        "1.1": "Мут и снятие мута",
        "1.2": "Бан и снятие бана", 
        "1.3": "Предупреждения",
        "2.1": "Ники себе",
        "2.2": "Ники другим",
        "3.1": "Правила",
        "3.2": "Приветствие",
        "4": "Доступ к команде ДК",
        "5": "Постинг ссылок",
        "6": "Выдача наград"
    }

    rank_names = {
        0: "Участник",
        1: "Модератор чата",
        2: "Наборщик", 
        3: "Заместитель главы клана",
        4: "Глава клана",
        5: "Глава альянса"
    }

    await update.message.reply_text(
        f"Для команды '{command_name}' теперь требуется ранг: {rank_names[rank]}"
    )

def display_user_profile(chat_id: int, user_id: int, user_name: str, user_lastname: Optional[str] = None) -> str:
    """Получить текст профиля пользователя"""
    try:
        rank = db.get_user_rank(chat_id, user_id)
        nick = db.get_nick(chat_id, user_id)
        warnings = db.get_warns(chat_id, user_id) or []
        awards = db.get_user_awards(chat_id, user_id) or []
        is_banned = db.is_banned(chat_id, user_id)
        mute_info = db.get_mute_time(chat_id, user_id)
        is_muted = mute_info is not None
        
        rank_names = {
            0: "👤 Участник",
            1: "🛡️ Модератор чата",
            2: "📋 Наборщик", 
            3: "⚔️ Заместитель главы клана",
            4: "👑 Глава клана",
            5: "🔱 Глава альянса"
        }
        
        # Формируем полное имя
        full_name = user_name
        if user_lastname:
            full_name = f"{user_name} {user_lastname}"
        
        # Формируем текст профиля
        user_link = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
        profile_text = f"<b>👤 Профиль пользователя</b>\n\n"
        profile_text += f"<b>Имя:</b> {user_link}\n"
        
        if nick:
            profile_text += f"<b>Ник:</b> {nick}\n"
        
        profile_text += f"<b>Ранг:</b> {rank_names.get(rank, 'Неизвестный')} [{rank}]\n"
        
        if warnings:
            profile_text += f"<b>Предупреждения:</b> {len(warnings)}/3\n"
        else:
            profile_text += f"<b>Предупреждения:</b> 0/3\n"
        
        if is_banned:
            profile_text += "🚫 <b>Статус:</b> <u>Забанен</u>\n"
        elif is_muted:
            profile_text += "🔇 <b>Статус:</b> <u>Заммучен</u>\n"
        else:
            profile_text += "✅ <b>Статус:</b> <u>Активен</u>\n"
        
        if awards and len(awards) > 0:
            profile_text += f"\n<b>🏆 Награды ({len(awards)}):</b>\n"
            for award in awards:
                profile_text += f"  • {award}\n"
        
        return profile_text
    except Exception as e:
        logging.error(f"Error building profile: {str(e)}")
        return f"❌ Ошибка при загрузке профиля: {str(e)}"

async def who_am_i(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль текущего пользователя"""
    try:
        user = update.message.from_user
        chat_id = update.message.chat_id
        
        profile_text = display_user_profile(chat_id, user.id, user.first_name, user.last_name)
        await update.message.reply_text(profile_text, parse_mode='HTML')
    except Exception as e:
        logging.error(f"who_am_i error: {str(e)}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def who_is_this(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль другого пользователя (по reply или mention)"""
    try:
        chat_id = update.message.chat_id
        target_user = None
        target_user_id = None
        
        # 1. Проверяем reply
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
        # 2. Проверяем text_mention entities
        elif update.message.entities:
            for entity in update.message.entities:
                if entity.type == 'text_mention':
                    target_user = entity.user
                    target_user_id = target_user.id
                    break
        
        if not target_user_id:
            await update.message.reply_text("❌ Ответьте на сообщение пользователя или упомяните его, чтобы посмотреть профиль.")
            return
        
        profile_text = display_user_profile(chat_id, target_user_id, target_user.first_name, target_user.last_name)
        await update.message.reply_text(profile_text, parse_mode='HTML')
    except Exception as e:
        logging.error(f"who_is_this error: {str(e)}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def bot_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Шо")

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    await check_and_set_creator_rank(update, context)

    creator = db.get_chat_creator(chat_id)
    if not creator:
        if is_creator_username(update.message.from_user.username):
            db.set_chat_creator(chat_id, update.message.from_user.id)
            db.set_user_rank(chat_id, update.message.from_user.id, 5)
        else:
            db.set_chat_creator(chat_id, update.message.from_user.id)

    for user in update.message.new_chat_members:
        if user.is_bot:
            continue

        if is_creator_username(user.username):
            db.set_user_rank(chat_id, user.id, 5)

        welcome_text = db.get_welcome_message(chat_id)
        nick = db.get_nick(chat_id, user.id)
        if nick:
            welcome_text += f"\nТвой ник: {nick}"

        await update.message.reply_text(welcome_text)

def setup_handlers(application):
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кто ты'), who_is_this))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кто я$'), who_am_i))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^бот$'), bot_response))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^помощь$'), help_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!код чата$'), chat_code_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!импорт'), import_settings))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!завещание'), set_will), group=1)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-завещание'), remove_will), group=1)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^приветствие$'), show_welcome))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+приветствие'), set_welcome))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^админы$'), show_admins))
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
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^преды$'), show_warns))
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

    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(nicks_help|warns_help|rules_help)"))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
    
    # Check links last (after all command handlers) to avoid blocking commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_links), group=100)

# Keep-alive сервер на порту 5000 (Replit держит его живым)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running on Replit!"

@app.route('/health')
def health():
    return {"status": "ok"}, 200

def run_flask():
    print("🌐 Keep-alive сервер запущен на http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

def keep_alive():
    t = threading.Thread(target=run_flask, daemon=False)
    t.start()

def main():
    print("Инициализация базы данных...")
    db.init_database()
    
    print("Запуск keep-alive сервера на порту 5000...")
    keep_alive()
    time.sleep(2)
    
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    print("✅ Бот полностью инициализирован!")
    print("✅ Keep-alive сервер работает - проект останется активным!")
    print("Добавьте бота в группу и дайте ему права администратора!")
    application.run_polling()

if __name__ == '__main__':
    main()
