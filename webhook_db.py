import os
import json
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"

def dict_factory(cursor, row):
    """Преобразует строки SQLite в словари"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    """Получить подключение к SQLite"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = dict_factory
    return conn

def init_db():
    """Инициализация базы данных SQLite"""
    print("Инициализация базы данных SQLite...")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            creator_id INTEGER,
            chat_code TEXT,
            welcome_message TEXT DEFAULT 'ANTEEQ',
            rules TEXT DEFAULT 'Правила чата не установлены',
            access_control TEXT,
            link_posting_rank INTEGER DEFAULT 0,
            award_giving_rank INTEGER DEFAULT 4
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            chat_id INTEGER,
            user_id INTEGER,
            rank INTEGER,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nicks (
            chat_id INTEGER,
            user_id INTEGER,
            nick TEXT,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            from_user_id INTEGER,
            reason TEXT,
            warn_date TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mutes (
            chat_id INTEGER,
            user_id INTEGER,
            unmute_time TEXT,
            mute_reason TEXT,
            mute_date TEXT,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            chat_id INTEGER,
            user_id INTEGER,
            ban_reason TEXT,
            ban_date TEXT,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS awards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            award_name TEXT,
            award_date TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            profanity_filter_enabled INTEGER DEFAULT 1,
            max_warns INTEGER DEFAULT 3,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ БД инициализирована (SQLite)")

def save_admin_rank(chat_id: int, user_id: int, rank: int):
    """Сохранить ранг администратора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO admins (chat_id, user_id, rank) 
        VALUES (?, ?, ?)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET rank = ?
    ''', (chat_id, user_id, rank, rank))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_admins():
    """Получить всех администраторов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, user_id, rank FROM admins')
    admins = cursor.fetchall()
    cursor.close()
    conn.close()
    return admins

def save_nick(chat_id: int, user_id: int, nick: str):
    """Сохранить ник пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO nicks (chat_id, user_id, nick) 
        VALUES (?, ?, ?)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET nick = ?
    ''', (chat_id, user_id, nick, nick))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_nicks():
    """Получить все ники"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, user_id, nick FROM nicks')
    nicks = cursor.fetchall()
    cursor.close()
    conn.close()
    return nicks

def save_chat(chat_id: int, creator_id: int | None = None):
    """Сохранить чат"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chats (chat_id, creator_id) 
        VALUES (?, ?)
        ON CONFLICT (chat_id) DO NOTHING
    ''', (chat_id, creator_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_chat(chat_id: int):
    """Получить данные чата"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
    chat = cursor.fetchone()
    cursor.close()
    conn.close()
    if chat and chat.get('access_control'):
        chat['access_control'] = json.loads(chat['access_control'])
    return chat

def update_chat_welcome(chat_id: int, welcome_message: str):
    """Обновить приветствие чата"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE chats SET welcome_message = ? WHERE chat_id = ?
    ''', (welcome_message, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_chat_rules(chat_id: int, rules: str):
    """Обновить правила чата"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE chats SET rules = ? WHERE chat_id = ?
    ''', (rules, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_access_control(chat_id: int, access_control: dict):
    """Обновить доступы к командам"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE chats SET access_control = ? WHERE chat_id = ?
    ''', (json.dumps(access_control), chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def add_warn(chat_id: int, user_id: int, from_user_id: int, reason: str):
    """Добавить предупреждение"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO warns (chat_id, user_id, from_user_id, reason, warn_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, user_id, from_user_id, reason, datetime.now().isoformat()))
    conn.commit()
    cursor.close()
    conn.close()

def get_warns(chat_id: int, user_id: int):
    """Получить предупреждения пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM warns 
        WHERE chat_id = ? AND user_id = ?
        ORDER BY warn_date DESC
    ''', (chat_id, user_id))
    warns = cursor.fetchall()
    cursor.close()
    conn.close()
    return warns

def remove_warn(chat_id: int, user_id: int):
    """Удалить последнее предупреждение"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM warns 
        WHERE id = (
            SELECT id FROM warns 
            WHERE chat_id = ? AND user_id = ?
            ORDER BY warn_date DESC LIMIT 1
        )
    ''', (chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def add_mute(chat_id: int, user_id: int, unmute_time, mute_reason: str):
    """Добавить мут"""
    conn = get_db_connection()
    cursor = conn.cursor()
    unmute_str = unmute_time.isoformat() if hasattr(unmute_time, 'isoformat') else str(unmute_time)
    now_str = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO mutes (chat_id, user_id, unmute_time, mute_reason, mute_date)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (chat_id, user_id) 
        DO UPDATE SET unmute_time = ?, mute_reason = ?, mute_date = ?
    ''', (chat_id, user_id, unmute_str, mute_reason, now_str, 
          unmute_str, mute_reason, now_str))
    conn.commit()
    cursor.close()
    conn.close()

def remove_mute(chat_id: int, user_id: int):
    """Удалить мут"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM mutes WHERE chat_id = ? AND user_id = ?
    ''', (chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def add_ban(chat_id: int, user_id: int, ban_reason: str):
    """Добавить бан"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bans (chat_id, user_id, ban_reason, ban_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (chat_id, user_id) DO NOTHING
    ''', (chat_id, user_id, ban_reason, datetime.now().isoformat()))
    conn.commit()
    cursor.close()
    conn.close()

def remove_ban(chat_id: int, user_id: int):
    """Удалить бан"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM bans WHERE chat_id = ? AND user_id = ?
    ''', (chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
