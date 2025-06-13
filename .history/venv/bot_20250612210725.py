import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "YOUR_BOT_TOKEN"  # ЗАМЕНИ НА СВОЙ
DATA_FILE = "questions.json"

LANGS = {
    "Русский": "ru",
    "O'zbek": "uz",
    "English": "en"
}

admin_keyboard = [
    ["📋 Список вопросов", "➕ Добавить вопрос"],
    ["✏️ Редактировать вопрос", "📤 Переместить вопрос"],
    ["❌ Удалить вопрос", "📊 Ответы пользователей"]
]

cancel_keyboard = [["🔙 Отмена"]]


def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    lang_keyboard = [[key] for key in LANGS]
    await update.message.reply_text("🌐 Выберите язык:", reply_markup=ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True))


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lang = context.user_data["lang"]
    step = context.user_data.get("step", 0)

    if step >= len(data["questions"]):
        data.setdefault("answers", {})[str(update.effective_user.id)] = context.user_data["answers"]
        save_data(data)
        await update.message.reply_text("✅ Спасибо за участие!", reply_markup=ReplyKeyboardRemove())
        return

    q = data["questions"][step]
    context.user_data["current_question"] = q

    text = q["text"][lang]
    if q["type"] == "choice":
        opts = q["options"][lang]
        keyboard = [[o] for o in opts] + [["Другое"], ["🔙 Отмена"]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    else:
        markup = ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True)

    await update.message.reply_text(text, reply_markup=markup)


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    data = load_data()

    if text in LANGS:
        context.user_data["lang"] = LANGS[text]
        context.user_data["step"] = 0
        context.user_data["answers"] = {}
        await send_question(update, context)
        return

    if text.lower() in ["отмена", "🔙 отмена", "🔙"]:
        context.user_data.clear()
        await update.message.reply_text("❌ Отменено.", reply_markup=ReplyKeyboardRemove())
        return

    if user_id in ADMIN_ID:
        act = context.user_data.get("admin_action")
        if act == "move_question":
            try:
                parts = list(map(int, text.split()))
                if len(parts) == 2:
                    src, dest = parts
                    questions = data["questions"]
                    if 1 <= src <= len(questions) and 1 <= dest <= len(questions):
                        item = questions.pop(src - 1)
                        questions.insert(dest - 1, item)
                        for i, q in enumerate(questions, 1):
                            q["id"] = i
                        save_data(data)
                        await update.message.reply_text("📤 Перемещено.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
                    else:
                        await update.message.reply_text("⚠️ Неверные номера.")
                else:
                    await update.message.reply_text("⚠️ Введите два номера.")
            except:
                await update.message.reply_text("⚠️ Ошибка.")
            context.user_data.clear()
            return
        elif text in [btn for row in admin_keyboard for btn in row]:
            if text == "📋 Список вопросов":
                msg = "📋 Вопросы:\n\n"
                for q in data["questions"]:
                    msg += f"{q['id']}. {q['text']['ru']} ({q['type']})\n"
                await update.message.reply_text(msg or "Нет вопросов.")
            elif text == "📤 Переместить вопрос":
                context.user_data["admin_action"] = "move_question"
                await update.message.reply_text("↕️ Введите два номера (откуда и куда):", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            elif text == "📊 Ответы пользователей":
                msg = "📊 Ответы:\n"
                for uid, ans in data.get("answers", {}).items():
                    msg += f"\n👤 {uid}:\n"
                    for qid, val in ans.items():
                        msg += f"  {qid}: {val}\n"
                await update.message.reply_text(msg or "Нет ответов.")
            return

    # обычный пользователь
    q = context.user_data.get("current_question")
    if not q:
        await update.message.reply_text("⚠️ Напишите /start.")
        return

    lang = context.user_data["lang"]
    step = context.user_data.get("step", 0)

    if q["type"] == "choice" and text == "Другое":
        context.user_data["awaiting_other"] = True
        await update.message.reply_text("✏️ Напишите свой вариант:")
        return

    if context.user_data.get("awaiting_other"):
        context.user_data["awaiting_other"] = False
        answer = text
    elif q["type"] == "choice" and text not in q["options"][lang] and text != "Другое":
        await update.message.reply_text("⚠️ Выберите из списка или 'Другое'.")
        return
    else:
        answer = text

    context.user_data["answers"][str(q["id"])] = answer
    context.user_data["step"] = step + 1
    await send_question(update, context)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("⛔ Только для админа.")
        return
    await update.message.reply_text("🔐 Админ-панель:", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))


# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.run_polling()
