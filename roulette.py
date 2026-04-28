import random

# Цвета чисел рулетки
RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
# 0 — зеро (зелёное)

ROULETTE_EMOJI = {
    "red": "🔴",
    "black": "⚫",
    "zero": "🟢"
}

def get_color(number):
    if number == 0:
        return "zero"
    elif number in RED_NUMBERS:
        return "red"
    else:
        return "black"

def spin():
    return random.randint(0, 36)

def parse_bet(text: str):
    """
    Парсит строку ставки вида '100 к', '500 ч', '200 з', '1000 15', '300 д1'
    Возвращает (amount, bet_type, bet_value) или None при ошибке
    
    Типы ставок:
      к  — красное (win x2)
      ч  — чёрное (win x2)
      з  — зеро (win x36)
      чт — чёт (win x2)
      нч — нечет (win x2)
      1-36 — конкретное число (win x36)
      д1 — дюжина 1-12 (win x3)
      д2 — дюжина 13-24 (win x3)
      д3 — дюжина 25-36 (win x3)
      м  — меньше 1-18 (win x2)
      б  — больше 19-36 (win x2)
    """
    parts = text.strip().lower().split()
    if len(parts) != 2:
        return None
    
    try:
        amount = float(parts[0])
    except ValueError:
        try:
            amount = float(parts[1])
            parts = [parts[1], parts[0]]
        except ValueError:
            return None
    
    if amount <= 0:
        return None
    
    bet_str = parts[1]
    
    # Конкретное число
    try:
        num = int(bet_str)
        if 0 <= num <= 36:
            return amount, "number", str(num)
    except ValueError:
        pass
    
    # Словарь ставок
    mapping = {
        "к": ("color", "red"),
        "красное": ("color", "red"),
        "ч": ("color", "black"),
        "черное": ("color", "black"),
        "чёрное": ("color", "black"),
        "з": ("zero", "0"),
        "зеро": ("zero", "0"),
        "чт": ("parity", "even"),
        "чет": ("parity", "even"),
        "нч": ("parity", "odd"),
        "нечет": ("parity", "odd"),
        "д1": ("dozen", "1"),
        "д2": ("dozen", "2"),
        "д3": ("dozen", "3"),
        "м": ("half", "low"),
        "мало": ("half", "low"),
        "б": ("half", "high"),
        "много": ("half", "high"),
    }
    
    if bet_str in mapping:
        return amount, mapping[bet_str][0], mapping[bet_str][1]
    
    return None

def calculate_win(bet_type, bet_value, result_number, amount):
    """
    Возвращает сумму выигрыша (включая возврат ставки) или 0 при проигрыше
    """
    color = get_color(result_number)
    
    if bet_type == "color":
        if result_number == 0:
            return 0
        if (bet_value == "red" and color == "red") or (bet_value == "black" and color == "black"):
            return amount * 2
        return 0
    
    elif bet_type == "zero":
        if result_number == 0:
            return amount * 36
        return 0
    
    elif bet_type == "number":
        if result_number == int(bet_value):
            return amount * 36
        return 0
    
    elif bet_type == "parity":
        if result_number == 0:
            return 0
        if bet_value == "even" and result_number % 2 == 0:
            return amount * 2
        if bet_value == "odd" and result_number % 2 == 1:
            return amount * 2
        return 0
    
    elif bet_type == "dozen":
        if result_number == 0:
            return 0
        d = int(bet_value)
        ranges = {1: (1,12), 2: (13,24), 3: (25,36)}
        lo, hi = ranges[d]
        if lo <= result_number <= hi:
            return amount * 3
        return 0
    
    elif bet_type == "half":
        if result_number == 0:
            return 0
        if bet_value == "low" and 1 <= result_number <= 18:
            return amount * 2
        if bet_value == "high" and 19 <= result_number <= 36:
            return amount * 2
        return 0
    
    return 0

def bet_type_label(bet_type, bet_value):
    labels = {
        ("color", "red"): "🔴 Красное",
        ("color", "black"): "⚫ Чёрное",
        ("zero", "0"): "🟢 Зеро",
        ("parity", "even"): "🔢 Чёт",
        ("parity", "odd"): "🔢 Нечет",
        ("dozen", "1"): "📊 Дюжина 1-12",
        ("dozen", "2"): "📊 Дюжина 13-24",
        ("dozen", "3"): "📊 Дюжина 25-36",
        ("half", "low"): "⬇️ Меньше (1-18)",
        ("half", "high"): "⬆️ Больше (19-36)",
    }
    if bet_type == "number":
        return f"🎯 Число {bet_value}"
    return labels.get((bet_type, bet_value), f"{bet_type}:{bet_value}")
