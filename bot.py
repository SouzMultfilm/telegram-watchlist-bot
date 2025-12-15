# -*- coding: utf-8 -*-

import json
import os
from statistics import mean
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8251244160:AAGZpoqfEMGN85Oc8xuh5feXmXDXu_XQJwM"
DATA_FILE = "watchlist.json"

CATEGORIES = {
    "movie": "🎬 Фильмы",
    "series": "📺 Сериалы",
    "anime": "🍥 Аниме",
    "music": "🎵 Музыка",
}

# ---------- DATA ----------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # защита от старого формата
    if isinstance(data, list):
        return {}

    return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_list(user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = []

    # автоматическая защита старых записей
    for item in data[uid]:
        if "done" not in item:
            item["done"] = False
        if "rating" not in item:
            item["rating"] = None

    return data[uid]

data = load_data()

# ---------- MENUS ----------

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить", callback_data="add")],
        [InlineKeyboardButton("📋 Список", callback_data="list")],
        [InlineKeyboardButton("✅ Просмотрено", callback_data="done")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])

def rating_keyboard(index):
    keyboard, row = [], []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(str(i), callback_data=f"rate_{index}_{i}"))
        if i % 5 == 0:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

# ---------- START ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🎥 *Личный медиалист*\n\n"
        "Фильмы · Сериалы · Аниме · Музыка\n"
        "У каждого пользователя свой список.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ---------- CALLBACK ----------

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_list = get_user_list(query.from_user.id)
    btn = query.data

    if btn == "back":
        context.user_data.clear()
        await query.message.reply_text("🏠 Главное меню:", reply_markup=main_menu())

    elif btn == "add":
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"add_{key}")]
            for key, name in CATEGORIES.items()
        ]
        keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
        await query.message.reply_text(
            "➕ *Добавление*\n\nВыбери категорию:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif btn.startswith("add_"):
        category = btn.replace("add_", "")
        context.user_data["adding"] = category
        await query.message.reply_text(
            f"✍️ Введи название\n\n*{CATEGORIES[category]}*",
            reply_markup=back_menu(),
            parse_mode="Markdown"
        )

    elif btn == "list":
        await show_list(query.message, user_list, False)

    elif btn == "done":
        await show_list(query.message, user_list, True)

    elif btn == "stats":
        await show_stats(query.message, user_list)

    elif btn.startswith("mark_"):
        i = int(btn.replace("mark_", ""))
        user_list[i]["done"] = True
        save_data(data)
        await query.message.reply_text(
            "⭐ Оцени просмотр (1–10):",
            reply_markup=rating_keyboard(i)
        )

    elif btn.startswith("rate_"):
        _, index, value = btn.split("_")
        user_list[int(index)]["rating"] = int(value)
        save_data(data)
        await query.message.reply_text("✅ Оценка сохранена", reply_markup=main_menu())

    elif btn.startswith("delete_"):
        removed = user_list.pop(int(btn.replace("delete_", "")))
        save_data(data)
        await query.message.reply_text(
            f"🗑 Удалено:\n*{removed['category']}* — {removed['title']}",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )

# ---------- TEXT ----------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "adding" not in context.user_data:
        return

    user_list = get_user_list(update.effective_user.id)
    category = context.user_data.pop("adding")

    user_list.append({
        "title": update.message.text,
        "category": CATEGORIES[category],
        "done": False,
        "rating": None
    })

    save_data(data)

    await update.message.reply_text(
        f"➕ Добавлено:\n*{CATEGORIES[category]}* — {update.message.text}",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ---------- LIST ----------

async def show_list(message, user_list, only_done):
    items = [(i, x) for i, x in enumerate(user_list)
             if x["done"] == only_done or not only_done]

    if not items:
        await message.reply_text("📭 Список пуст", reply_markup=main_menu())
        return

    text = "📋 *Твой список:*\n\n"
    keyboard = []

    for i, item in items:
        status = "✅" if item["done"] else "⏳"
        rating = f" ⭐{item['rating']}" if item["rating"] else ""
        text += f"{i+1}. {status}{rating} {item['category']} — {item['title']}\n"

        row = []
        if not item["done"]:
            row.append(InlineKeyboardButton("✅", callback_data=f"mark_{i}"))
        row.append(InlineKeyboardButton("🗑", callback_data=f"delete_{i}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------- STATS ----------

async def show_stats(message, user_list):
    total = len(user_list)
    done = sum(1 for x in user_list if x["done"])
    ratings = [x.get("rating") for x in user_list if x.get("rating")]

    avg = round(mean(ratings), 2) if ratings else "—"

    by_cat = {}
    for x in user_list:
        by_cat[x["category"]] = by_cat.get(x["category"], 0) + 1

    text = (
        "📊 *Статистика*\n\n"
        f"🎯 Всего: *{total}*\n"
        f"✅ Просмотрено: *{done}*\n"
        f"⏳ Осталось: *{total - done}*\n"
        f"⭐ Средняя оценка: *{avg}*\n\n"
        "📂 По категориям:\n"
    )

    for cat, count in by_cat.items():
        text += f"• {cat}: {count}\n"

    await message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

# ---------- RUN ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
