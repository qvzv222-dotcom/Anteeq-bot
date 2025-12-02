
import os
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_db_connection():
    """Получить подключение к PostgreSQL из DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL не установлен в переменных окружения")
    
    # Render использует postgres://, но psycopg2 требует postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
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

# Остальные функции БД аналогичны test_db.py, но используют PostgreSQL
# (Полный код будет слишком длинным, основные изменения - замена ? на %s для параметров)
