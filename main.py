import os
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

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
        [InlineKeyboardButton("Ники", callback_data="nicks_help")],
        [InlineKeyboardButton("Админы", callback_data="admins_help")],
        [InlineKeyboardButton("Преды", callback_data="warns_help")],
        [InlineKeyboardButton("Правила", callback_data="rules_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Доступные команды:\n\n"
        "• Помощь - показать это сообщение\n"
        "• Кто админ - список администраторов\n"
        "• +ник [ник] - установить свой ник\n"
        "• -ник - удалить свой ник\n"
        "• Ники - список всех ников\n"
        "• Преды - посмотреть свои предупреждения\n"
        "• Правила - показать правила чата",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "nicks_help":
        text = "Команды ников:\n• +ник [ник] - установить ник\n• -ник - удалить ник\n• Ники - список ников"
    elif data == "admins_help":
        text = "Команда: 'кто админ' - покажет список администраторов чата"
    elif data == "warns_help":
        text = "Команда: 'преды' - покажет ваши предупреждения\nДля других участников - ответьте на сообщение с этой командой"
    elif data == "rules_help":
        text = "Команда: 'правила' - покажет правила чата"
    else:
        return

    await query.edit_message_text(text)

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
        await update.message.reply_text("В чате нет администраторов")
        return

    rank_names = {
        0: "Участник",
        1: "Модератор чата", 
        2: "Наборщик",
        3: "Заместитель главы клана",
        4: "Глава клана",
        5: "Глава альянса"
    }

    admins_text = "Администраторы чата:\n"
    for user_id, rank in sorted(admins.items(), key=lambda x: x[1], reverse=True):
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            rank_name = rank_names.get(rank, "Неизвестно")
            admins_text += f"• {user.user.first_name} - {rank_name}\n"
        except:
            continue

    await update.message.reply_text(admins_text)

async def set_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    creator = db.get_chat_creator(chat_id)

    if creator != user_id:
        await update.message.reply_text("Только создатель может назначать ранги")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите '+ранг [ранг]'")
        return

    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        await update.message.reply_text(
            "Использование: +ранг [ранг]\n\n"
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
        await update.message.reply_text("В чате нет установленных ников")
        return

    nicks_text = "Ники участников:\n"
    for i, (user_id, nick) in enumerate(nicks.items(), 1):
        try:
            user = await context.bot.get_chat_member(chat_id, user_id)
            username = f"@{user.user.username}" if user.user.username else "без юзернейма"
            nicks_text += f"{i}. {nick} - {username}\n"
        except:
            continue

    await update.message.reply_text(nicks_text)

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

    if not has_access(chat_id, user_id, "1.3"):
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

    db.add_warn(chat_id, target_user.id, user_id, reason)
    warn_count = db.get_warn_count(chat_id, target_user.id)

    if warn_count >= 3:
        db.add_ban(chat_id, target_user.id)
        await update.message.reply_text(
            f"Пользователь {target_user.first_name} получил 3 предупреждения и был забанен"
        )
    else:
        await update.message.reply_text(
            f"Пользователь {target_user.first_name} получил предупреждение ({warn_count}/3)\nПричина: {reason}"
        )

async def show_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    target_user = update.message.from_user
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user

    warns = db.get_warns(chat_id, target_user.id)
    
    if not warns:
        await update.message.reply_text(f"У пользователя {target_user.first_name} нет предупреждений")
        return

    warns_text = f"Предупреждения пользователя {target_user.first_name} ({len(warns)}/3):\n"

    for i, warn in enumerate(warns, 1):
        try:
            admin = await context.bot.get_chat_member(chat_id, warn['from_user_id'])
            admin_name = admin.user.first_name
        except:
            admin_name = "Неизвестно"

        date_str = warn['warn_date'].strftime("%d.%m.%Y %H:%M")
        warns_text += f"{i}. {date_str} - {admin_name}: {warn['reason']}\n"

    await update.message.reply_text(warns_text)

async def remove_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.3"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите '-варн' или '-пред'")
        return

    target_user = update.message.reply_to_message.from_user
    warns = db.get_warns(chat_id, target_user.id)

    if not warns:
        await update.message.reply_text(f"У пользователя {target_user.first_name} нет предупреждений")
        return

    db.remove_last_warn(chat_id, target_user.id)
    warn_count = db.get_warn_count(chat_id, target_user.id)
    
    if db.is_banned(chat_id, target_user.id) and warn_count < 3:
        db.remove_ban(chat_id, target_user.id)

    await update.message.reply_text(
        f"Предупреждение снято с пользователя {target_user.first_name}\n"
        f"Осталось предупреждений: {warn_count}/3"
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'бан [причина]'")
        return

    target_user = update.message.reply_to_message.from_user
    text = update.message.text.strip()
    parts = text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Причина не указана"

    db.add_ban(chat_id, target_user.id)

    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        await update.message.reply_text(
            f"Пользователь {target_user.first_name} забанен\nПричина: {reason}"
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при бане: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'разбан'")
        return

    target_user = update.message.reply_to_message.from_user
    db.remove_ban(chat_id, target_user.id)

    try:
        await context.bot.unban_chat_member(chat_id, target_user.id)
        await update.message.reply_text(f"Пользователь {target_user.first_name} разбанен")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при разбане: {str(e)}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.2"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'кик'")
        return

    target_user = update.message.reply_to_message.from_user

    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        await context.bot.unban_chat_member(chat_id, target_user.id)
        await update.message.reply_text(f"Пользователь {target_user.first_name} исключен из чата")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при кике: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.1"):
        await update.message.reply_text("Недостаточно прав")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Использование: ответьте на сообщение пользователя и напишите 'мут [время в минутах]'")
        return

    target_user = update.message.reply_to_message.from_user
    text = update.message.text.strip()
    parts = text.split()
    
    duration = 60
    if len(parts) > 1:
        try:
            duration = int(parts[1])
        except ValueError:
            duration = 60

    unmute_time = datetime.now() + timedelta(minutes=duration)
    db.set_mute(chat_id, target_user.id, unmute_time)

    try:
        await context.bot.restrict_chat_member(
            chat_id, 
            target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=unmute_time
        )
        await update.message.reply_text(
            f"Пользователь {target_user.first_name} замучен на {duration} минут"
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при муте: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not has_access(chat_id, user_id, "1.1"):
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
        await update.message.reply_text(f"Пользователь {target_user.first_name} размучен")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при размуте: {str(e)}")

def get_section_from_command(command: str) -> str:
    command_lower = command.lower().strip()
    
    if command_lower in ["мут", "размут"]:
        return "1.1"
    elif command_lower in ["бан", "разбан"]:
        return "1.2"
    elif command_lower in ["варн", "пред"]:
        return "1.3"
    elif command_lower in ["+ник", "-ник"]:
        return "2.1"
    elif command_lower in ["+ник другому", "-ник другому"]:
        return "2.2"
    elif command_lower in ["правила", "+правила"]:
        return "3.1"
    elif command_lower == "+приветствие":
        return "3.2"
    elif command_lower == "кто админ":
        return "3.1"
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
        await update.message.reply_text(
            "Использование: дк {команда} {требуемый ранг}\n\n"
            "Разделы и команды:\n"
            "1 - Мут, Бан, Предупреждения\n"
            "   мут, размут, бан, разбан, варн, пред\n\n"
            "2 - Ники\n"
            "   +ник, -ник, +ник другому, -ник другому\n\n"
            "3 - Правила, Приветствие\n"
            "   правила, +правила, +приветствие, кто админ\n\n"
            "4 - Доступ к команде ДК\n\n"
            "Ранги: 0-5\n"
            "0 - Участник\n"
            "1 - Модератор чата\n"
            "2 - Наборщик\n"
            "3 - Заместитель главы клана\n"
            "4 - Глава клана\n"
            "5 - Глава альянса"
        )
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
        "4": "Доступ к команде ДК"
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_and_set_creator_rank), group=-1)
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^бот$'), bot_response))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^помощь$'), help_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!код чата$'), chat_code_command))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!импорт'), import_settings))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^!завещание'), set_will))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-завещание'), remove_will))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+приветствие'), set_welcome))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кто админ'), show_admins))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+ранг'), set_rank))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+ник другому\s+'), set_nick_other))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-ник другому$'), remove_nick_other))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+ник\s+'), set_nick))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-ник$'), remove_nick))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^ники$'), show_nicks))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^правила$'), show_rules))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^\+правила'), set_rules))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^-(варн|пред)'), remove_warn))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(варн|пред)'), warn_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^преды$'), show_warns))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^разбан'), unban_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^кик'), kick_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^бан'), ban_user))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^(размут|говори)'), unmute_user))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^мут'), mute_user))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(?i)^дк'), access_control_command))

    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(nicks_help|admins_help|warns_help|rules_help)"))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))

def main():
    print("Инициализация базы данных...")
    db.init_database()
    
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)

    print("Бот запущен...")
    print("Добавьте бота в группу и дайте ему права администратора!")
    application.run_polling()

if __name__ == '__main__':
    main()
