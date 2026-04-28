from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS
from database import (
    get_all_users, get_user, set_balance, update_balance,
    block_user, get_all_bets, get_global_stats,
    get_setting, set_setting, create_promo, get_all_promos, deactivate_promo
)

admin_router = Router()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def fmt(n):
    if n is None:
        return "0"
    return f"{float(n):,.0f}".replace(",", " ")

# ─── MIDDLEWARE: только для админов ─────────────────────

@admin_router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    await msg.answer(
        "👑 <b>Панель администратора</b>\n\n"
        "<b>👥 Игроки:</b>\n"
        "/users — список всех игроков\n"
        "/addbalance [id] [сумма] — добавить баланс\n"
        "/setbalance [id] [сумма] — установить баланс\n"
        "/block [id] — заблокировать игрока\n"
        "/unblock [id] — разблокировать игрока\n"
        "/userinfo [id] — инфо об игроке\n\n"
        "<b>📊 Статистика:</b>\n"
        "/stats — общая статистика казино\n"
        "/allbets — последние 50 ставок\n\n"
        "<b>⚙️ Настройки:</b>\n"
        "/setminbet [сумма] — мин. ставка\n"
        "/setmaxbet [сумма] — макс. ставка\n\n"
        "<b>🎁 Промокоды:</b>\n"
        "/createpromo [код] [сумма] [кол-во использований]\n"
        "/promos — список промокодов\n"
        "/delpromo [код] — деактивировать промокод",
        parse_mode="HTML"
    )

@admin_router.message(Command("users"))
async def cmd_users(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    users = await get_all_users()
    if not users:
        await msg.answer("Нет игроков")
        return
    lines = [f"👥 <b>Игроки ({len(users)}):</b>\n"]
    for u in users[:30]:
        name = u["username"] or u["full_name"] or "—"
        blocked = " 🚫" if u["is_blocked"] else ""
        lines.append(f"{'@'+u['username'] if u['username'] else u['full_name']} | ID: {u['user_id']} | 💰 {fmt(u['balance'])}{blocked}")
    if len(users) > 30:
        lines.append(f"\n...и ещё {len(users)-30} игроков")
    await msg.answer("\n".join(lines), parse_mode="HTML")

@admin_router.message(Command("userinfo"))
async def cmd_userinfo(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ /userinfo [user_id]")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await msg.answer("❌ Неверный ID")
        return
    u = await get_user(uid)
    if not u:
        await msg.answer("❌ Игрок не найден")
        return
    await msg.answer(
        f"👤 <b>Игрок:</b> {u['full_name']}\n"
        f"🆔 ID: {u['user_id']}\n"
        f"📱 Username: @{u['username'] or '—'}\n"
        f"💰 Баланс: {fmt(u['balance'])} GRAM\n"
        f"🚫 Заблокирован: {'Да' if u['is_blocked'] else 'Нет'}\n"
        f"🎯 Ставок: {u['total_bets']}\n"
        f"✅ Выигрышей: {u['total_wins']}\n"
        f"❌ Проигрышей: {u['total_losses']}\n"
        f"📈 Поставлено: {fmt(u['total_wagered'])} GRAM\n"
        f"🏆 Выиграно: {fmt(u['total_won'])} GRAM\n"
        f"📅 Регистрация: {u['created_at']}",
        parse_mode="HTML"
    )

@admin_router.message(Command("addbalance"))
async def cmd_addbalance(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer("❓ /addbalance [user_id] [сумма]")
        return
    try:
        uid = int(args[1])
        amount = float(args[2])
    except ValueError:
        await msg.answer("❌ Неверные аргументы")
        return
    u = await get_user(uid)
    if not u:
        await msg.answer("❌ Игрок не найден")
        return
    await update_balance(uid, amount)
    u2 = await get_user(uid)
    await msg.answer(
        f"✅ Баланс пополнен\n"
        f"👤 {u['full_name']} | ID: {uid}\n"
        f"➕ +{fmt(amount)} GRAM\n"
        f"💰 Новый баланс: {fmt(u2['balance'])} GRAM",
        parse_mode="HTML"
    )

@admin_router.message(Command("setbalance"))
async def cmd_setbalance(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer("❓ /setbalance [user_id] [сумма]")
        return
    try:
        uid = int(args[1])
        amount = float(args[2])
    except ValueError:
        await msg.answer("❌ Неверные аргументы")
        return
    u = await get_user(uid)
    if not u:
        await msg.answer("❌ Игрок не найден")
        return
    await set_balance(uid, amount)
    await msg.answer(
        f"✅ Баланс установлен\n"
        f"👤 {u['full_name']} | ID: {uid}\n"
        f"💰 Баланс: {fmt(amount)} GRAM",
        parse_mode="HTML"
    )

@admin_router.message(Command("block"))
async def cmd_block(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ /block [user_id]")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await msg.answer("❌ Неверный ID")
        return
    u = await get_user(uid)
    if not u:
        await msg.answer("❌ Игрок не найден")
        return
    await block_user(uid, True)
    await msg.answer(f"🚫 Игрок {u['full_name']} (ID: {uid}) заблокирован")

@admin_router.message(Command("unblock"))
async def cmd_unblock(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ /unblock [user_id]")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await msg.answer("❌ Неверный ID")
        return
    u = await get_user(uid)
    if not u:
        await msg.answer("❌ Игрок не найден")
        return
    await block_user(uid, False)
    await msg.answer(f"✅ Игрок {u['full_name']} (ID: {uid}) разблокирован")

@admin_router.message(Command("stats"))
async def cmd_stats(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    s = await get_global_stats()
    users = await get_all_users()
    min_bet = await get_setting("min_bet")
    max_bet = await get_setting("max_bet")
    await msg.answer(
        f"📊 <b>Статистика казино</b>\n\n"
        f"👥 Всего игроков: {len(users)}\n"
        f"🎲 Всего ставок: {s['total_bets'] or 0}\n"
        f"💵 Поставлено: {fmt(s['total_wagered'])} GRAM\n"
        f"💸 Выплачено: {fmt(s['total_paid'])} GRAM\n"
        f"🏦 Прибыль казино: {fmt(s['profit'])} GRAM\n\n"
        f"⚙️ Лимиты: {fmt(min_bet)} — {fmt(max_bet)} GRAM",
        parse_mode="HTML"
    )

@admin_router.message(Command("allbets"))
async def cmd_allbets(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    bets = await get_all_bets(30)
    if not bets:
        await msg.answer("Нет ставок")
        return
    from roulette import get_color, ROULETTE_EMOJI, bet_type_label
    lines = ["📋 <b>Последние 30 ставок:</b>\n"]
    for b in bets:
        color = get_color(b["result_number"])
        emoji = ROULETTE_EMOJI[color]
        result = "✅" if b["win"] > 0 else "❌"
        user = f"@{b['username']}" if b["username"] else str(b["user_id"])
        label = bet_type_label(b["bet_type"], b["bet_value"])
        lines.append(f"{result} {user} | {label} | {fmt(b['amount'])} → {emoji}{b['result_number']}")
    await msg.answer("\n".join(lines), parse_mode="HTML")

@admin_router.message(Command("setminbet"))
async def cmd_setminbet(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ /setminbet [сумма]")
        return
    try:
        val = float(args[1])
    except ValueError:
        await msg.answer("❌ Неверное значение")
        return
    await set_setting("min_bet", val)
    await msg.answer(f"✅ Минимальная ставка: <b>{fmt(val)} GRAM</b>", parse_mode="HTML")

@admin_router.message(Command("setmaxbet"))
async def cmd_setmaxbet(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ /setmaxbet [сумма]")
        return
    try:
        val = float(args[1])
    except ValueError:
        await msg.answer("❌ Неверное значение")
        return
    await set_setting("max_bet", val)
    await msg.answer(f"✅ Максимальная ставка: <b>{fmt(val)} GRAM</b>", parse_mode="HTML")

@admin_router.message(Command("createpromo"))
async def cmd_createpromo(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 4:
        await msg.answer("❓ /createpromo [КОД] [сумма] [кол-во использований]")
        return
    try:
        code = args[1].upper()
        amount = float(args[2])
        uses = int(args[3])
    except ValueError:
        await msg.answer("❌ Неверные аргументы")
        return
    await create_promo(code, amount, uses)
    await msg.answer(
        f"✅ Промокод создан!\n"
        f"🎁 Код: <code>{code}</code>\n"
        f"💰 Сумма: {fmt(amount)} GRAM\n"
        f"🔢 Использований: {uses}",
        parse_mode="HTML"
    )

@admin_router.message(Command("promos"))
async def cmd_promos(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    promos = await get_all_promos()
    if not promos:
        await msg.answer("Нет промокодов")
        return
    lines = ["🎁 <b>Промокоды:</b>\n"]
    for p in promos:
        status = "✅" if p["is_active"] else "❌"
        lines.append(
            f"{status} <code>{p['code']}</code> | {fmt(p['amount'])} GRAM "
            f"| {p['used_count']}/{p['max_uses']} исп."
        )
    await msg.answer("\n".join(lines), parse_mode="HTML")

@admin_router.message(Command("delpromo"))
async def cmd_delpromo(msg: Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❓ /delpromo [КОД]")
        return
    code = args[1].upper()
    await deactivate_promo(code)
    await msg.answer(f"✅ Промокод <code>{code}</code> деактивирован", parse_mode="HTML")
