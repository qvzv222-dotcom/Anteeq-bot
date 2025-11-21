import os
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import Optional, Dict, List, Any
from datetime import datetime
import json

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_database():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,
            creator_id BIGINT,
            chat_code VARCHAR(10),
            welcome_message TEXT DEFAULT 'ANTEEQ',
            rules TEXT DEFAULT 'Правила чата не установлены',
            access_control JSONB DEFAULT '{"1.1": 1, "1.2": 3, "1.3": 1, "2.1": 0, "2.2": 2, "3.1": 3, "3.2": 3, "4": 4}'::jsonb,
            link_posting_rank INT DEFAULT 1,
            award_giving_rank INT DEFAULT 3
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            chat_id BIGINT,
            user_id BIGINT,
            rank INT,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nicks (
            chat_id BIGINT,
            user_id BIGINT,
            nick VARCHAR(255),
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS warns (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            user_id BIGINT,
            from_user_id BIGINT,
            reason TEXT,
            warn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS mutes (
            chat_id BIGINT,
            user_id BIGINT,
            unmute_time TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            chat_id BIGINT,
            user_id BIGINT,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS awards (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            user_id BIGINT,
            award_name VARCHAR(255),
            award_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('ALTER TABLE chats ADD COLUMN IF NOT EXISTS link_posting_rank INT DEFAULT 1')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        pass
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('ALTER TABLE chats ADD COLUMN IF NOT EXISTS award_giving_rank INT DEFAULT 3')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        pass
    
    print("База данных инициализирована")

def ensure_chat_exists(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO chats (chat_id)
        VALUES (%s)
        ON CONFLICT (chat_id) DO NOTHING
    ''', (chat_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_chat_creator(chat_id: int) -> Optional[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT creator_id FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result and result[0] else None

def set_chat_creator(chat_id: int, creator_id: Optional[int]):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET creator_id = %s WHERE chat_id = %s', (creator_id, chat_id))
    conn.commit()
    cur.close()
    conn.close()

def get_chat_code(chat_id: int) -> Optional[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT chat_code FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def set_chat_code(chat_id: int, chat_code: str):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET chat_code = %s WHERE chat_id = %s', (chat_code, chat_id))
    conn.commit()
    cur.close()
    conn.close()

def get_welcome_message(chat_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT welcome_message FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else "ANTEEQ"

def set_welcome_message(chat_id: int, message: str):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET welcome_message = %s WHERE chat_id = %s', (message, chat_id))
    conn.commit()
    cur.close()
    conn.close()

def get_rules(chat_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT rules FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else "Правила чата не установлены"

def set_rules(chat_id: int, rules: str):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET rules = %s WHERE chat_id = %s', (rules, chat_id))
    conn.commit()
    cur.close()
    conn.close()

def get_access_control(chat_id: int) -> Dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT access_control FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result and result[0]:
        return result[0]
    return {"1.1": 1, "1.2": 3, "1.3": 1, "2.1": 0, "2.2": 2, "3.1": 3, "3.2": 3, "4": 4}

def set_access_control(chat_id: int, access_control: Dict[str, int]):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET access_control = %s WHERE chat_id = %s', (Json(access_control), chat_id))
    conn.commit()
    cur.close()
    conn.close()

def get_user_rank(chat_id: int, user_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT rank FROM admins WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 0

def set_user_rank(chat_id: int, user_id: int, rank: int):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    if rank == 0:
        cur.execute('DELETE FROM admins WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    else:
        cur.execute('''
            INSERT INTO admins (chat_id, user_id, rank)
            VALUES (%s, %s, %s)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET rank = %s
        ''', (chat_id, user_id, rank, rank))
    conn.commit()
    cur.close()
    conn.close()

def get_all_admins(chat_id: int) -> Dict[int, int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id, rank FROM admins WHERE chat_id = %s', (chat_id,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return {user_id: rank for user_id, rank in results}

def get_nick(chat_id: int, user_id: int) -> Optional[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT nick FROM nicks WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def set_nick(chat_id: int, user_id: int, nick: str):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO nicks (chat_id, user_id, nick)
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET nick = %s
    ''', (chat_id, user_id, nick, nick))
    conn.commit()
    cur.close()
    conn.close()

def remove_nick(chat_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM nicks WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_all_nicks(chat_id: int) -> Dict[int, str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id, nick FROM nicks WHERE chat_id = %s', (chat_id,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return {user_id: nick for user_id, nick in results}

def add_warn(chat_id: int, user_id: int, from_user_id: int, reason: str):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO warns (chat_id, user_id, from_user_id, reason)
        VALUES (%s, %s, %s, %s)
    ''', (chat_id, user_id, from_user_id, reason))
    conn.commit()
    cur.close()
    conn.close()

def get_warns(chat_id: int, user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        SELECT from_user_id, reason, warn_date
        FROM warns
        WHERE chat_id = %s AND user_id = %s
        ORDER BY warn_date
    ''', (chat_id, user_id))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in results]

def remove_last_warn(chat_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM warns
        WHERE id = (
            SELECT id FROM warns
            WHERE chat_id = %s AND user_id = %s
            ORDER BY warn_date DESC
            LIMIT 1
        )
    ''', (chat_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_warn_count(chat_id: int, user_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM warns WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 0

def add_ban(chat_id: int, user_id: int):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO bans (chat_id, user_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    ''', (chat_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def remove_ban(chat_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM bans WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def is_banned(chat_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM bans WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

def set_mute(chat_id: int, user_id: int, unmute_time: datetime):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO mutes (chat_id, user_id, unmute_time)
        VALUES (%s, %s, %s)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET unmute_time = %s
    ''', (chat_id, user_id, unmute_time, unmute_time))
    conn.commit()
    cur.close()
    conn.close()

def remove_mute(chat_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM mutes WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_mute_time(chat_id: int, user_id: int) -> Optional[datetime]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT unmute_time FROM mutes WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def find_chat_by_code(chat_code: str) -> Optional[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT chat_id FROM chats WHERE chat_code = %s', (chat_code,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def get_link_posting_rank(chat_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT link_posting_rank FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 1

def set_link_posting_rank(chat_id: int, rank: int):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET link_posting_rank = %s WHERE chat_id = %s', (rank, chat_id))
    conn.commit()
    cur.close()
    conn.close()

def get_award_giving_rank(chat_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT award_giving_rank FROM chats WHERE chat_id = %s', (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 3

def set_award_giving_rank(chat_id: int, rank: int):
    ensure_chat_exists(chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE chats SET award_giving_rank = %s WHERE chat_id = %s', (rank, chat_id))
    conn.commit()
    cur.close()
    conn.close()

def add_award(chat_id: int, user_id: int, award_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO awards (chat_id, user_id, award_name)
        VALUES (%s, %s, %s)
    ''', (chat_id, user_id, award_name))
    conn.commit()
    cur.close()
    conn.close()

def get_user_awards(chat_id: int, user_id: int) -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT award_name FROM awards
        WHERE chat_id = %s AND user_id = %s
        ORDER BY award_date DESC
    ''', (chat_id, user_id))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in results]

def remove_all_awards(chat_id: int, user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM awards
        WHERE chat_id = %s AND user_id = %s
    ''', (chat_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def get_all_users_in_chat(chat_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.user_id, a.rank FROM admins a
        WHERE a.chat_id = %s
        ORDER BY a.rank DESC, a.user_id
    ''', (chat_id,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    users = []
    for user_id, rank in results:
        nick = get_nick(chat_id, user_id)
        awards = get_user_awards(chat_id, user_id)
        users.append({
            'user_id': user_id,
            'rank': rank,
            'nick': nick,
            'awards': awards
        })
    
    return users

def import_chat_settings(target_chat_id: int, source_chat_id: int):
    ensure_chat_exists(target_chat_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE chats
        SET welcome_message = src.welcome_message,
            rules = src.rules,
            access_control = src.access_control
        FROM (SELECT welcome_message, rules, access_control FROM chats WHERE chat_id = %s) AS src
        WHERE chat_id = %s
    ''', (source_chat_id, target_chat_id))
    conn.commit()
    cur.close()
    conn.close()
