import os
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import Optional, Dict, List, Any
from datetime import datetime
import json
import time

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection(retry_count=3):
    for attempt in range(retry_count):
        try:
            return psycopg2.connect(DATABASE_URL)
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            if attempt == retry_count - 1:
                raise
            time.sleep(0.5)

def safe_execute(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            import logging
            logging.error(f"Database error in {func.__name__}: {str(e)}")
            return None
    return wrapper

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
            access_control JSONB DEFAULT '{"1.1": 1, "1.2": 1, "1.3": 3, "1.4": 1, "1.5": 1, "2.1": 0, "2.2": 2, "3.1": 3, "3.2": 3, "4": 4, "7": 1}'::jsonb,
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
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_chat_creator(chat_id: int) -> Optional[int]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT creator_id FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result and result[0] else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

def set_chat_creator(chat_id: int, creator_id: Optional[int]):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET creator_id = %s WHERE chat_id = %s', (creator_id, chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_chat_code(chat_id: int) -> Optional[str]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT chat_code FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

def set_chat_code(chat_id: int, chat_code: str):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET chat_code = %s WHERE chat_id = %s', (chat_code, chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_welcome_message(chat_id: int) -> str:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT welcome_message FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else "ANTEEQ"
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return "ANTEEQ"

def set_welcome_message(chat_id: int, message: str):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET welcome_message = %s WHERE chat_id = %s', (message, chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_rules(chat_id: int) -> str:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT rules FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else "Правила чата не установлены"
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return "Правила чата не установлены"

def set_rules(chat_id: int, rules: str):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET rules = %s WHERE chat_id = %s', (rules, chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_access_control(chat_id: int) -> Dict[str, int]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT access_control FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result and result[0]:
            return result[0]
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass
    return {"1.1": 1, "1.2": 3, "1.3": 1, "2.1": 0, "2.2": 2, "3.1": 3, "3.2": 3, "4": 4}

def set_access_control(chat_id: int, access_control: Dict[str, int]):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET access_control = %s WHERE chat_id = %s', (Json(access_control), chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_user_rank(chat_id: int, user_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT rank FROM admins WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 0
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 0

def set_user_rank(chat_id: int, user_id: int, rank: int):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_all_admins(chat_id: int) -> Dict[int, int]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id, rank FROM admins WHERE chat_id = %s', (chat_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return {user_id: rank for user_id, rank in results}
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return {}

def get_nick(chat_id: int, user_id: int) -> Optional[str]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT nick FROM nicks WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

def set_nick(chat_id: int, user_id: int, nick: str):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def remove_nick(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM nicks WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_all_nicks(chat_id: int) -> Dict[int, str]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id, nick FROM nicks WHERE chat_id = %s', (chat_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return {user_id: nick for user_id, nick in results}
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return {}

def add_warn(chat_id: int, user_id: int, from_user_id: int, reason: str):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_warns(chat_id: int, user_id: int) -> List[Dict[str, Any]]:
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def remove_last_warn(chat_id: int, user_id: int):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_warn_count(chat_id: int, user_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM warns WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 0
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 0

def add_ban(chat_id: int, user_id: int):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def remove_ban(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM bans WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def is_banned(chat_id: int, user_id: int) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM bans WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return False

def set_mute(chat_id: int, user_id: int, unmute_time: datetime):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def remove_mute(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM mutes WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_mute_time(chat_id: int, user_id: int) -> Optional[datetime]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT unmute_time FROM mutes WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

def get_expired_mutes() -> List[tuple]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT chat_id, user_id FROM mutes
            WHERE unmute_time <= NOW()
        ''')
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def find_chat_by_code(chat_code: str) -> Optional[int]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT chat_id FROM chats WHERE chat_code = %s', (chat_code,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

def get_link_posting_rank(chat_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT link_posting_rank FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 1
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 1

def set_link_posting_rank(chat_id: int, rank: int):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET link_posting_rank = %s WHERE chat_id = %s', (rank, chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_award_giving_rank(chat_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT award_giving_rank FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 3
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 3

def set_award_giving_rank(chat_id: int, rank: int):
    try:
        ensure_chat_exists(chat_id)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET award_giving_rank = %s WHERE chat_id = %s', (rank, chat_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def add_award(chat_id: int, user_id: int, award_name: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO awards (chat_id, user_id, award_name)
            VALUES (%s, %s, %s)
        ''', (chat_id, user_id, award_name))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_user_awards(chat_id: int, user_id: int) -> List[str]:
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def remove_all_awards(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            DELETE FROM awards
            WHERE chat_id = %s AND user_id = %s
        ''', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_all_users_in_chat(chat_id: int) -> List[Dict[str, Any]]:
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def import_chat_settings(target_chat_id: int, source_chat_id: int):
    try:
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
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass
