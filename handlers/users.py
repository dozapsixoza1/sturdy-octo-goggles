from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from database import (
    get_or_create_user, get_user, save_bet, get_user_bets,
    update_balance, use_promo, get_setting
)
from roulette import parse_bet, spin, calculate_win, get_color, ROULETTE_EMOJI, bet_type_label

user_router = Router()

def fmt_balance(bal):
    return f"{bal:,.0f}".replace(",", " ")

@user_router.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_or_create_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    await msg.answer(
        f"🎰 <b>Добро пожаловать в казино GRAM!</b>\n\n"
        f"💰 Твой баланс: <b>{fmt_balance(user['balance'])} GRAM</b>\n\n"
        f"<b>Как делать ставки:</b>\n"
        f"Напиши <code>сумма тип</code>, например:\n"
        f"  <code>100 к</code> — на красное\n"
        f"  <code>500 ч</code> — на чёрное\n"
        f"  <code>200 з</code> — на зеро (x36)\n"
        f"  <code>300 17</code> — на число 17 (x36)\n"
        f"  <code>100 чт</code> — на чёт\n"
        f"  <code>100 нч</code> — на нечет\n"
        f"  <code>200 д1</code> — дюжина 1-12 (x3)\n"
        f"  <code>200 д2</code> — дюжина 13-24 (x3)\n"
        f"  <code>200 д3</code> — дюжина 25-36 (x3)\n"
        f"  <code>100 м</code> — меньше 1-18 (x2)\n"
        f"  <code>100 б</code> — больше 19-36 (x2)\n\n"
        f"/balance — баланс\n"
        f"/history — история ставок\n"
        f"/promo КОД — активировать промокод\n"
        f"/help — помощь",
        parse_mode="HTML"
    )

@user_router.message(Command("balance"))
async def cmd_balance(msg: Message):
    user = await get_or_create_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    await msg.answer(
        f"💰 <b>Твой баланс:</b> {fmt_balance(user['balance'])} GRAM\n\n"
        f"📊 Всего ставок: {user['total_bets']}\n"
        f"✅ Выигрышей: {user['total_wins']}\n"
        f"❌ Проигрышей: {user['total_losses']}\n"
        f"📈 Поставлено: {fmt_balance(user['total_wagered'])} GRAM\n"
        f"🏆 Выиграно: {fmt_balance(user['total_won'])} GRAM",
        parse_mode="HTML"
    )

@user_router.message(Command("history"))
async def cmd_history(msg: Message):
    await get_or_create_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    bets = await get_user_bets(msg.from_user.id, 15)
    if not bets:
        await msg.answer("📭 У тебя пока нет ставок")
        return
    lines = ["📋 <b>Последние 15 ставок:</b>\n"]
    for b in bets:
        color = get_color(b["result_number"])
        emoji = ROULETTE_EMOJI[color]
        result = "✅" if b["win"] > 0 else "❌"
        label = bet_type_label(b["bet_type"], b["bet_value"])
        lines.append(
            f"{result} {label} | {fmt_balance(b['amount'])} GRAM "
            f"→ {emoji}{b['result_number']} | "
            f"{'+ ' + fmt_balance(b['win']) if b['win'] > 0 else '- ' + fmt_balance(b['amount'])}"
        )
    await msg.answer("\n".join(lines), parse_mode="HTML")

@user_router.message(Command("promo"))
async def cmd_promo(msg: Message):
    await get_or_create_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.answer("❓ Напиши: /promo КОД")
        return
    code = args[1].strip()
    amount, status = await use_promo(msg.from_user.id, code)
    if amount:
        user = await get_user(msg.from_user.id)
        await msg.answer(
            f"🎁 {status}\n"
            f"Начислено: <b>+{fmt_balance(amount)} GRAM</b>\n"
            f"💰 Баланс: <b>{fmt_balance(user['balance'])} GRAM</b>",
            parse_mode="HTML"
        )
    else:
        await msg.answer(status)

@user_router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "🎰 <b>GRAM Рулетка — Помощь</b>\n\n"
        "<b>Ставки (сумма тип):</b>\n"
        "  к / красное — Красное x2\n"
        "  ч / чёрное — Чёрное x2\n"
        "  з / зеро — Зеро x36\n"
        "  0-36 — Число x36\n"
        "  чт / нч — Чёт/Нечет x2\n"
        "  д1 / д2 / д3 — Дюжины x3\n"
        "  м / б — Меньше/Больше x2\n\n"
        "<b>Команды:</b>\n"
        "/balance — Баланс и статистика\n"
        "/history — История ставок\n"
        "/promo КОД — Использовать промокод",
        parse_mode="HTML"
    )

@user_router.message()
async def handle_bet(msg: Message):
    user = await get_or_create_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    
    if user["is_blocked"]:
        await msg.answer("🚫 Ты заблокирован. Обратись к администратору.")
        return
    
    parsed = parse_bet(msg.text)
    if not parsed:
        return  # Игнорируем нераспознанные сообщения
    
    amount, bet_type, bet_value = parsed
    amount = round(amount)
    
    # Проверка лимитов
    min_bet = float(await get_setting("min_bet") or 10)
    max_bet = float(await get_setting("max_bet") or 10000)
    
    if amount < min_bet:
        await msg.answer(f"⚠️ Минимальная ставка: <b>{fmt_balance(min_bet)} GRAM</b>", parse_mode="HTML")
        return
    if amount > max_bet:
        await msg.answer(f"⚠️ Максимальная ставка: <b>{fmt_balance(max_bet)} GRAM</b>", parse_mode="HTML")
        return
    if user["balance"] < amount:
        await msg.answer(
            f"💸 Недостаточно GRAM на балансе\n"
            f"💰 Твой баланс: <b>{fmt_balance(user['balance'])} GRAM</b>",
            parse_mode="HTML"
        )
        return
    
    # Крутим рулетку
    result = spin()
    win = calculate_win(bet_type, bet_value, result, amount)
    profit = win - amount  # может быть отрицательным
    
    await update_balance(msg.from_user.id, profit)
    await save_bet(msg.from_user.id, bet_type, bet_value, amount, result, win)
    
    user_after = await get_user(msg.from_user.id)
    color = get_color(result)
    color_emoji = ROULETTE_EMOJI[color]
    label = bet_type_label(bet_type, bet_value)
    
    if win > 0:
        result_text = (
            f"🎰 <b>Рулетка крутится...</b>\n\n"
            f"🎯 Ставка: {label}\n"
            f"💵 Сумма: {fmt_balance(amount)} GRAM\n\n"
            f"🎡 Выпало: {color_emoji} <b>{result}</b>\n\n"
            f"✅ <b>ВЫИГРЫШ! +{fmt_balance(win)} GRAM</b>\n"
            f"💰 Баланс: {fmt_balance(user_after['balance'])} GRAM"
        )
    else:
        result_text = (
            f"🎰 <b>Рулетка крутится...</b>\n\n"
            f"🎯 Ставка: {label}\n"
            f"💵 Сумма: {fmt_balance(amount)} GRAM\n\n"
            f"🎡 Выпало: {color_emoji} <b>{result}</b>\n\n"
            f"❌ <b>Проигрыш. -{fmt_balance(amount)} GRAM</b>\n"
            f"💰 Баланс: {fmt_balance(user_after['balance'])} GRAM"
        )
    
    await msg.answer(result_text, parse_mode="HTML")
