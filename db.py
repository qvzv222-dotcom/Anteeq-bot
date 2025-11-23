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
            return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            if attempt == retry_count - 1:
                raise
            time.sleep(1 + attempt)

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
            mute_reason TEXT DEFAULT '',
            mute_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            chat_id BIGINT,
            user_id BIGINT,
            ban_reason TEXT DEFAULT '',
            ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id BIGINT PRIMARY KEY,
            profanity_filter_enabled BOOLEAN DEFAULT TRUE,
            max_warns INT DEFAULT 3,
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
        cur.execute('ALTER TABLE chats ADD COLUMN IF NOT EXISTS award_giving_rank INT DEFAULT 3')
        cur.execute('ALTER TABLE mutes ADD COLUMN IF NOT EXISTS mute_reason TEXT DEFAULT \'\'')
        cur.execute('ALTER TABLE mutes ADD COLUMN IF NOT EXISTS mute_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        cur.execute('ALTER TABLE bans ADD COLUMN IF NOT EXISTS ban_reason TEXT DEFAULT \'\'')
        cur.execute('ALTER TABLE bans ADD COLUMN IF NOT EXISTS ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        conn.commit()
        cur.close()
        conn.close()
    except:
        pass

def set_user_rank(chat_id: int, user_id: int, rank: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO admins (chat_id, user_id, rank)
            VALUES (%s, %s, %s)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET rank = EXCLUDED.rank
        ''', (chat_id, user_id, rank))
        
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

def set_nick(chat_id: int, user_id: int, nick: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO nicks (chat_id, user_id, nick)
            VALUES (%s, %s, %s)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET nick = EXCLUDED.nick
        ''', (chat_id, user_id, nick))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

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
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT user_id, nick FROM nicks WHERE chat_id = %s', (chat_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return {row['user_id']: row['nick'] for row in results}
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return {}

def warn_user(chat_id: int, user_id: int, from_user_id: int, reason: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO warns (chat_id, user_id, from_user_id, reason, warn_date)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
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

def remove_warn(chat_id: int, user_id: int):
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

def remove_all_warns(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM warns WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def mute_user(chat_id: int, user_id: int, until: datetime, reason: str = ''):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO mutes (chat_id, user_id, unmute_time, mute_reason, mute_date)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET unmute_time = EXCLUDED.unmute_time, mute_reason = EXCLUDED.mute_reason
        ''', (chat_id, user_id, until, reason))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def unmute_user(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            UPDATE mutes 
            SET unmute_time = '2999-12-31'::TIMESTAMP
            WHERE chat_id = %s AND user_id = %s
        ''', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def ban_user(chat_id: int, user_id: int, reason: str = ''):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO bans (chat_id, user_id, ban_reason, ban_date)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (chat_id, user_id)
            DO UPDATE SET ban_reason = EXCLUDED.ban_reason
        ''', (chat_id, user_id, reason))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def unban_user(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM bans WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
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
        cur.execute('SELECT chat_id, user_id FROM mutes WHERE unmute_time < CURRENT_TIMESTAMP')
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def is_banned(chat_id: int, user_id: int) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM bans WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return bool(result)
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return False

def get_all_bans(chat_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT user_id, ban_reason, ban_date FROM bans WHERE chat_id = %s', (chat_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in results]
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def set_chat_creator(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('UPDATE chats SET creator_id = %s WHERE chat_id = %s', (user_id, chat_id))
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
        return result[0] if result else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

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

def set_welcome_message(chat_id: int, message: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chats (chat_id, welcome_message)
            VALUES (%s, %s)
            ON CONFLICT (chat_id)
            DO UPDATE SET welcome_message = EXCLUDED.welcome_message
        ''', (chat_id, message))
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
        return result[0] if result else 'Добро пожаловать!'
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 'Добро пожаловать!'

def set_rules(chat_id: int, rules: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chats (chat_id, rules)
            VALUES (%s, %s)
            ON CONFLICT (chat_id)
            DO UPDATE SET rules = EXCLUDED.rules
        ''', (chat_id, rules))
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
        return result[0] if result else 'Правила не установлены'
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 'Правила не установлены'

def set_access_control(chat_id: int, access_control: Dict):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chats (chat_id, access_control)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (chat_id)
            DO UPDATE SET access_control = EXCLUDED.access_control
        ''', (chat_id, json.dumps(access_control)))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_access_control(chat_id: int) -> Dict:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT access_control FROM chats WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result and result[0]:
            return json.loads(result[0]) if isinstance(result[0], str) else result[0]
        return {"1.1": 1, "1.2": 1, "1.3": 3, "1.4": 1, "1.5": 1, "2.1": 0, "2.2": 2, "3.1": 3, "3.2": 3, "4": 4, "7": 1}
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return {"1.1": 1, "1.2": 1, "1.3": 3, "1.4": 1, "1.5": 1, "2.1": 0, "2.2": 2, "3.1": 3, "3.2": 3, "4": 4, "7": 1}


def set_award(chat_id: int, user_id: int, award_name: str):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO awards (chat_id, user_id, award_name, award_date)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ''', (chat_id, user_id, award_name))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

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
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chats (chat_id, link_posting_rank)
            VALUES (%s, %s)
            ON CONFLICT (chat_id)
            DO UPDATE SET link_posting_rank = EXCLUDED.link_posting_rank
        ''', (chat_id, rank))
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
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chats (chat_id, award_giving_rank)
            VALUES (%s, %s)
            ON CONFLICT (chat_id)
            DO UPDATE SET award_giving_rank = EXCLUDED.award_giving_rank
        ''', (chat_id, rank))
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
        ''', (chat_id, user_id))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [result[0] for result in results]
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def remove_awards(chat_id: int, user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM awards WHERE chat_id = %s AND user_id = %s', (chat_id, user_id))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_all_users_in_chat(chat_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT DISTINCT
                COALESCE(admins.user_id, nicks.user_id) as user_id,
                admins.rank,
                nicks.nick
            FROM admins
            FULL OUTER JOIN nicks ON admins.user_id = nicks.user_id AND admins.chat_id = nicks.chat_id
            WHERE admins.chat_id = %s OR nicks.chat_id = %s
        ''', (chat_id, chat_id))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in results]
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return []

def get_all_awards(chat_id: int) -> Dict[int, str]:
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT user_id, STRING_AGG(award_name, ', ') as awards
            FROM awards
            WHERE chat_id = %s
            GROUP BY user_id
        ''', (chat_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return {row['user_id']: row['awards'] for row in results}
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return {}

def get_profanity_filter_status(chat_id: int) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT profanity_filter_enabled FROM chat_settings WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else True
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return True

def set_profanity_filter(chat_id: int, enabled: bool):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chat_settings (chat_id, profanity_filter_enabled)
            VALUES (%s, %s)
            ON CONFLICT (chat_id)
            DO UPDATE SET profanity_filter_enabled = EXCLUDED.profanity_filter_enabled
        ''', (chat_id, enabled))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_max_warns(chat_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT max_warns FROM chat_settings WHERE chat_id = %s', (chat_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 3
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 3

def set_max_warns(chat_id: int, max_warns: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO chat_settings (chat_id, max_warns)
            VALUES (%s, %s)
            ON CONFLICT (chat_id)
            DO UPDATE SET max_warns = EXCLUDED.max_warns
        ''', (chat_id, max_warns))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass

def get_last_warn_details(chat_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT from_user_id, reason, warn_date
            FROM warns
            WHERE chat_id = %s AND user_id = %s
            ORDER BY warn_date DESC
            LIMIT 1
        ''', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return dict(result) if result else None
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return None

def get_highest_warn_giver_rank(chat_id: int, user_id: int) -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT from_user_id FROM warns
            WHERE chat_id = %s AND user_id = %s
        ''', (chat_id, user_id))
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        max_rank = 0
        for row in results:
            from_user_id = row[0]
            rank = get_user_rank(chat_id, from_user_id)
            max_rank = max(max_rank, rank)
        return max_rank
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return 0

def get_moderation_log(chat_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute('''
            SELECT 
                user_id, 
                'предупреждение' as punishment_type, 
                reason as punishment_reason, 
                warn_date as punishment_date
            FROM warns
            WHERE chat_id = %s
            UNION ALL
            SELECT 
                user_id,
                'мут' as punishment_type,
                mute_reason as punishment_reason,
                mute_date as punishment_date
            FROM mutes
            WHERE chat_id = %s
            UNION ALL
            SELECT 
                user_id,
                'бан' as punishment_type,
                ban_reason as punishment_reason,
                ban_date as punishment_date
            FROM bans
            WHERE chat_id = %s
            ORDER BY punishment_date DESC
        ''', (chat_id, chat_id, chat_id))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in results]
    except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
        import logging
        logging.error(f"ERROR in get_moderation_log for chat {chat_id}: {str(e)}")
        return []

def is_user_currently_muted(chat_id: int, user_id: int) -> bool:
    """Проверяет активный ли мут (не истекший)"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT 1 FROM mutes 
            WHERE chat_id = %s AND user_id = %s 
            AND unmute_time > CURRENT_TIMESTAMP
        ''', (chat_id, user_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return bool(result)
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        return False

def clear_punishment_history(chat_id: int):
    """Очищает историю наказаний чата (муты, варны, баны)"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM mutes WHERE chat_id = %s', (chat_id,))
        cur.execute('DELETE FROM warns WHERE chat_id = %s', (chat_id,))
        cur.execute('DELETE FROM bans WHERE chat_id = %s', (chat_id,))
        conn.commit()
        cur.close()
        conn.close()
    except (psycopg2.OperationalError, psycopg2.DatabaseError):
        pass
