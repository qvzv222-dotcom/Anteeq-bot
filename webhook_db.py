
import os
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import Json, RealDictCursor

logger = logging.getLogger(__name__)

def get_db_connection():
    """Получить подключение к PostgreSQL из DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL не установлен в переменных окружения")
    
    # Replit использует postgresql://, это правильный формат
    return psycopg2.connect(database_url)

def init_db():
    """Инициализация базы данных PostgreSQL"""
    print("Инициализация базы данных PostgreSQL...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,
            creator_id BIGINT,
            chat_code VARCHAR(10),
            welcome_message TEXT DEFAULT 'ANTEEQ',
            rules TEXT DEFAULT 'Правила чата не установлены',
            access_control JSONB,
            link_posting_rank INTEGER DEFAULT 0,
            award_giving_rank INTEGER DEFAULT 4
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            chat_id BIGINT,
            user_id BIGINT,
            rank INTEGER,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nicks (
            chat_id BIGINT,
            user_id BIGINT,
            nick TEXT,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warns (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            user_id BIGINT,
            from_user_id BIGINT,
            reason TEXT,
            warn_date TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mutes (
            chat_id BIGINT,
            user_id BIGINT,
            unmute_time TIMESTAMP,
            mute_reason TEXT,
            mute_date TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            chat_id BIGINT,
            user_id BIGINT,
            ban_reason TEXT,
            ban_date TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS awards (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            user_id BIGINT,
            award_name TEXT,
            award_date TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            user_id BIGINT PRIMARY KEY,
            user_name TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id BIGINT PRIMARY KEY,
            profanity_filter_enabled BOOLEAN DEFAULT TRUE,
            max_warns INTEGER DEFAULT 3,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ БД инициализирована (PostgreSQL)")

# Функции для работы с БД (используют %s вместо ?)

def save_admin_rank(chat_id: int, user_id: int, rank: int):
    """Сохранить ранг администратора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO admins (chat_id, user_id, rank) 
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET rank = %s
    ''', (chat_id, user_id, rank, rank))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_admins():
    """Получить всех администраторов"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
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
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET nick = %s
    ''', (chat_id, user_id, nick, nick))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_nicks():
    """Получить все ники"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT chat_id, user_id, nick FROM nicks')
    nicks = cursor.fetchall()
    cursor.close()
    conn.close()
    return nicks

def save_chat(chat_id: int, creator_id: int = None):
    """Сохранить чат"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chats (chat_id, creator_id) 
        VALUES (%s, %s)
        ON CONFLICT (chat_id) DO NOTHING
    ''', (chat_id, creator_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_chat(chat_id: int):
    """Получить данные чата"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM chats WHERE chat_id = %s', (chat_id,))
    chat = cursor.fetchone()
    cursor.close()
    conn.close()
    return chat

def update_chat_welcome(chat_id: int, welcome_message: str):
    """Обновить приветствие чата"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE chats SET welcome_message = %s WHERE chat_id = %s
    ''', (welcome_message, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_chat_rules(chat_id: int, rules: str):
    """Обновить правила чата"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE chats SET rules = %s WHERE chat_id = %s
    ''', (rules, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_access_control(chat_id: int, access_control: dict):
    """Обновить доступы к командам"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE chats SET access_control = %s WHERE chat_id = %s
    ''', (Json(access_control), chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def add_warn(chat_id: int, user_id: int, from_user_id: int, reason: str):
    """Добавить предупреждение"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO warns (chat_id, user_id, from_user_id, reason, warn_date)
        VALUES (%s, %s, %s, %s, %s)
    ''', (chat_id, user_id, from_user_id, reason, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()

def get_warns(chat_id: int, user_id: int):
    """Получить предупреждения пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT * FROM warns 
        WHERE chat_id = %s AND user_id = %s
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
            WHERE chat_id = %s AND user_id = %s
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
    cursor.execute('''
        INSERT INTO mutes (chat_id, user_id, unmute_time, mute_reason, mute_date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (chat_id, user_id) 
        DO UPDATE SET unmute_time = %s, mute_reason = %s, mute_date = %s
    ''', (chat_id, user_id, unmute_time, mute_reason, datetime.now(), 
          unmute_time, mute_reason, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()

def remove_mute(chat_id: int, user_id: int):
    """Удалить мут"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM mutes WHERE chat_id = %s AND user_id = %s
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
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO NOTHING
    ''', (chat_id, user_id, ban_reason, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()

def remove_ban(chat_id: int, user_id: int):
    """Удалить бан"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM bans WHERE chat_id = %s AND user_id = %s
    ''', (chat_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
