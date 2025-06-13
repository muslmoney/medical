import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "YOUR_BOT_TOKEN_HERE"
DATA_FILE = "questions.json"

LANGUAGES = {
    "Русский": "ru",
    "O'zbekcha": "uz",
    "English": "en"
}

admin_keyboard = [
    ["📋 Список вопросов", "➕ Добавить вопрос"],
    ["✏️ Редактировать вопрос", "📤 Переместить вопрос"],
    ["❌ Удалить вопрос", "📊 Ответы пользователей"]
]

cancel_keyboard = [["🔙 Отмена"]]

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    buttons = [[lang] for lang in LANGUAGES.keys()]
    await update.message.reply_text("⚠️ Пожалуйста, выберите язык:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    context.user_data["step"] = -1

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in LANGUAGES:
        await update.message.reply_text("⚠️ Пожалуйста, выберите язык с кнопки.")
        return

    context.user_data["lang"] = LANGUAGES[text]
    context.user_data["step"] = 0
    context.user_data["answers"] = {}
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    step = context.user_data.get("step", 0)
    lang = context.user_data.get("lang", "ru")

    if step >= len(data["questions"]):
        data.setdefault("answers", {})[str(update.effective_user.id)] = context.user_data["answers"]
        save_data(data)
        await update.message.reply_text("✅ Спасибо за участие!", reply_markup=ReplyKeyboardRemove())
        return

    q = data["questions"][step]
    context.user_data["current_question"] = q

    text = q["text"].get(lang, q["text"].get("ru", ""))
    if q["type"] == "choice":
        options = q.get("options", {}).get(lang, [])
        keyboard = [[opt] for opt in options] + [["Другое"], ["🔙 Отмена"]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    else:
        markup = ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True)

    await update.message.reply_text(text, reply_markup=markup)

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Опрос отменён.", reply_markup=ReplyKeyboardRemove())

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text.lower() in ["отмена", "🔙 отмена", "🔙"]:
        context.user_data.clear()
        await update.message.reply_text("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
        return

    if context.user_data.get("step") == -1:
        await handle_language_selection(update, context)
        return

    data = load_data()
    lang = context.user_data.get("lang", "ru")

    if user_id in ADMIN_ID:
        admin_action = context.user_data.get("admin_action")

        if admin_action == "add_question_text":
            context.user_data.setdefault("new_q_text", {})[lang] = text
            if len(context.user_data["new_q_text"]) < len(LANGUAGES):
                await ask_next_lang(update, context, "text")
            else:
                await ask_question_type(update, context)
            return

        elif admin_action == "add_question_type_choice":
            context.user_data.setdefault("new_q_options", {})[lang] = [o.strip() for o in text.split(",") if o.strip()]
            if len(context.user_data["new_q_options"]) < len(LANGUAGES):
                await ask_next_lang(update, context, "options")
            else:
                q = {
                    "id": len(data["questions"]) + 1,
                    "type": "choice",
                    "text": context.user_data["new_q_text"],
                    "options": context.user_data["new_q_options"]
                }
                data["questions"].append(q)
                save_data(data)
                context.user_data.clear()
                await update.message.reply_text("✅ Вопрос добавлен.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return

        elif admin_action == "add_question_type_text":
            q = {
                "id": len(data["questions"]) + 1,
                "type": "text",
                "text": context.user_data["new_q_text"],
                "options": {}
            }
            data["questions"].append(q)
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Вопрос добавлен.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return

        elif admin_action == "move_question":
            try:
                src, dest = map(int, text.split())
                questions = data["questions"]
                if 1 <= src <= len(questions) and 1 <= dest <= len(questions):
                    item = questions.pop(src - 1)
                    questions.insert(dest - 1, item)
                    for i, q in enumerate(questions, start=1):
                        q["id"] = i
                    save_data(data)
                    await update.message.reply_text("📤 Вопрос перемещён.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ Неверные номера.")
            except:
                await update.message.reply_text("⚠️ Ошибка ввода.")
            context.user_data.clear()
            return

        elif text in [btn for row in admin_keyboard for btn in row]:
            if text == "📋 Список вопросов":
                msg = "📋 Вопросы:\n\n"
                for q in data["questions"]:
                    qtext = q["text"].get("ru", "❓")
                    msg += f"{q['id']}. {qtext} ({q['type']})\n"
                await update.message.reply_text(msg or "Нет вопросов.")
            elif text == "➕ Добавить вопрос":
                context.user_data["admin_action"] = "add_question_text"
                context.user_data["lang_order"] = list(LANGUAGES.values())
                context.user_data["lang_step"] = 0
                lang_code = context.user_data["lang_order"][0]
                await update.message.reply_text(f"📝 Введите текст вопроса на {lang_code}:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            elif text == "📤 Переместить вопрос":
                context.user_data["admin_action"] = "move_question"
                await update.message.reply_text("↕️ Введите два номера (откуда и куда), через пробел:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            elif text == "📊 Ответы пользователей":
                msg = "📊 Ответы:\n\n"
                for uid, ans in data.get("answers", {}).items():
                    msg += f"👤 {uid}:\n"
                    for qid, val in ans.items():
                        msg += f"  {qid}: {val}\n"
                    msg += "\n"
                await update.message.reply_text(msg or "Ответов нет.")
            return

    q = context.user_data.get("current_question")
    if not q:
        await update.message.reply_text("⚠️ Нажмите /start, чтобы начать опрос.")
        return

    step = context.user_data.get("step", 0)
    lang = context.user_data.get("lang", "ru")

    if q["type"] == "choice" and text == "Другое":
        context.user_data["awaiting_other"] = True
        await update.message.reply_text("✏️ Введите свой вариант:")
        return

    if context.user_data.get("awaiting_other"):
        context.user_data["awaiting_other"] = False
        answer = text
    elif q["type"] == "choice" and text not in q.get("options", {}).get(lang, []) and text != "Другое":
        await update.message.reply_text("⚠️ Пожалуйста, выберите доступный вариант или нажмите 'Другое'.")
        return
    else:
        answer = text

    context.user_data["answers"][str(q["id"])] = answer
    context.user_data["step"] = step + 1
    await send_question(update, context)

async def ask_next_lang(update: Update, context: ContextTypes.DEFAULT_TYPE, part: str):
    context.user_data["lang_step"] += 1
    if context.user_data["lang_step"] < len(context.user_data["lang_order"]):
        lang_code = context.user_data["lang_order"][context.user_data["lang_step"]]
        if part == "text":
            await update.message.reply_text(f"📝 Введите текст вопроса на {lang_code}:")
        else:
            context.user_data["admin_action"] = "add_question_type_choice"
            await update.message.reply_text(f"🔢 Введите варианты ответа на {lang_code} через запятую:")

async def ask_question_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_action"] = "await_question_type"
    keyboard = [["📋 choice (варианты)", "📝 text (ввод)"]]
    await update.message.reply_text("📌 Выберите тип вопроса:", reply_markup=ReplyKeyboardMarkup(keyboard + cancel_keyboard, resize_keyboard=True))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("⛔ Только для админа.")
        return
    await update.message.reply_text("🔐 Админ-панель:", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))

# 📍 Универсальный обработчик
async def unified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if context.user_data.get("admin_action") == "await_question_type":
        if "choice" in text:
            context.user_data["admin_action"] = "add_question_type_choice"
            context.user_data["lang_step"] = 0
            lang_code = context.user_data["lang_order"][0]
            await update.message.reply_text(f"🔢 Введите варианты ответа на {lang_code} через запятую:")
        elif "text" in text:
            context.user_data["admin_action"] = "add_question_type_text"
            await handle_answer(update, context)
        else:
            await update.message.reply_text("⚠️ Выберите тип из предложенных.")
        return

    await handle_answer(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_handler))
    app.run_polling()
