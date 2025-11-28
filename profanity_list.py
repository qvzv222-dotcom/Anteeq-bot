# Profanity filter list for Russian language
PROFANITY_WORDS = {
    'мат', 'блят', 'блядь', 'ебать', 'ёбать', 'пидор', 'пизда', 'сука', 'хуй', 'хуе',
    'ахуел', 'хуёво', 'бля', 'блин', 'ебланы', 'ебал', 'нахуй', 'похуй', 'охуел',
    'хулиган', 'сучка', 'сучье', 'пидорас', 'уебан', 'доебал', 'проебал', 'ебёнок',
    'сукин', 'мудак', 'мудаки', 'бляди', 'долбоёб', 'гандон', 'уёбыш', 'пиздец',
    'засранец', 'дерьмо', 'говнюк', 'хер', 'хером', 'хреновый', 'курва', 'фак',
    'факе', 'шлюха', 'байстрюк', 'гниль', 'ублюдок', 'мразь', 'паскуда', 'сволочь'
}

def contains_profanity(text):
    """Проверить наличие мата в тексте"""
    if not text:
        return False
    
    text_lower = text.lower()
    words = text_lower.split()
    
    for word in words:
        # Удаляем пунктуацию для проверки
        clean_word = ''.join(c for c in word if c.isalpha())
        if clean_word in PROFANITY_WORDS:
            return True
    
    return False
