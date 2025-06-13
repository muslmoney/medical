import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "7366253745:AAEGD7nh93tBAg-g70ZDXlpyRnEaT_xXLkk"
DATA_FILE = "questions.json"

LANGUAGES = {
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
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    language_keyboard = [[k] for k in LANGUAGES]
    await update.message.reply_text("🌐 Выберите язык / Tilni tanlang / Choose language:",
                                    reply_markup=ReplyKeyboardMarkup(language_keyboard, resize_keyboard=True))

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in LANGUAGES:
        context.user_data["lang"] = LANGUAGES[text]
        context.user_data["step"] = 0
        context.user_data["answers"] = {}
        await send_question(update, context)
        return
    await handle_answer(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    step = context.user_data.get("step", 0)
    lang = context.user_data.get("lang", "ru")

    if step >= len(data["questions"]):
        data.setdefault("answers", {})[str(update.effective_user.id)] = {
            "lang": lang,
            "answers": context.user_data["answers"]
        }
        save_data(data)
        await update.message.reply_text("✅ Спасибо за участие!", reply_markup=ReplyKeyboardRemove())
        return

    q = data["questions"][step]
    context.user_data["current_question"] = q

    q_text = q["text"].get(lang, q["text"].get("ru", ""))
    if q["type"] == "choice":
        options = q["options"].get(lang, q["options"].get("ru", []))
        keyboard = [[opt] for opt in options] + [["Другое"], ["🔙 Отмена"]]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    else:
        markup = ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True)

    await update.message.reply_text(q_text, reply_markup=markup)

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Опрос отменён.", reply_markup=ReplyKeyboardRemove())

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    data = load_data()

    if text.lower() in ["отмена", "🔙 отмена", "🔙"]:
        context.user_data.clear()
        await update.message.reply_text("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
        return

    if user_id in ADMIN_ID:
        if context.user_data.get("admin_action") == "add_question_text":
            context.user_data["new_q_text"] = {"ru": text}
            context.user_data["admin_action"] = "add_question_text_uz"
            await update.message.reply_text("📝 Введите текст вопроса на узбекском:")
            return
        elif context.user_data.get("admin_action") == "add_question_text_uz":
            context.user_data["new_q_text"]["uz"] = text
            context.user_data["admin_action"] = "add_question_text_en"
            await update.message.reply_text("📝 Введите текст вопроса на английском:")
            return
        elif context.user_data.get("admin_action") == "add_question_text_en":
            context.user_data["new_q_text"]["en"] = text
            context.user_data["admin_action"] = "add_question_type"
            await update.message.reply_text("📌 Укажите тип вопроса: choice (варианты) или text (свободный ввод):",
                                            reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            return
        elif context.user_data.get("admin_action") == "add_question_type":
            if text not in ["choice", "text"]:
                await update.message.reply_text("⚠️ Введите либо choice, либо text.")
                return
            context.user_data["new_q_type"] = text
            if text == "choice":
                context.user_data["admin_action"] = "add_question_options"
                await update.message.reply_text("🔢 Введите варианты через запятую на русском:")
            else:
                q = {
                    "id": len(data["questions"]) + 1,
                    "text": context.user_data["new_q_text"],
                    "type": "text",
                    "options": {}
                }
                data["questions"].append(q)
                save_data(data)
                context.user_data.clear()
                await update.message.reply_text("✅ Вопрос добавлен.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return
        elif context.user_data.get("admin_action") == "add_question_options":
            context.user_data["new_q_options"] = {"ru": [o.strip() for o in text.split(",")]}
            context.user_data["admin_action"] = "add_question_options_uz"
            await update.message.reply_text("🔢 Введите варианты на узбекском:")
            return
        elif context.user_data.get("admin_action") == "add_question_options_uz":
            context.user_data["new_q_options"]["uz"] = [o.strip() for o in text.split(",")]
            context.user_data["admin_action"] = "add_question_options_en"
            await update.message.reply_text("🔢 Введите варианты на английском:")
            return
        elif context.user_data.get("admin_action") == "add_question_options_en":
            context.user_data["new_q_options"]["en"] = [o.strip() for o in text.split(",")]
            q = {
                "id": len(data["questions"]) + 1,
                "text": context.user_data["new_q_text"],
                "type": "choice",
                "options": context.user_data["new_q_options"]
            }
            data["questions"].append(q)
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Вопрос добавлен.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return
        elif context.user_data.get("admin_action") == "move_question":
            try:
                parts = list(map(int, text.split()))
                if len(parts) == 2:
                    src, dest = parts
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
                else:
                    await update.message.reply_text("⚠️ Введите два номера через пробел.")
            except:
                await update.message.reply_text("⚠️ Ошибка ввода.")
            context.user_data.clear()
            return
        elif text in [btn for row in admin_keyboard for btn in row]:
            if text == "📋 Список вопросов":
                msg = "📋 Вопросы:\n\n"
                for q in data["questions"]:
                    msg += f"{q['id']}. {q['text'].get('ru', '')} ({q['type']})\n"
                await update.message.reply_text(msg or "Нет вопросов.")
            elif text == "➕ Добавить вопрос":
                context.user_data["admin_action"] = "add_question_text"
                await update.message.reply_text("📝 Введите текст вопроса на русском:",
                                                reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            elif text == "📤 Переместить вопрос":
                context.user_data["admin_action"] = "move_question"
                await update.message.reply_text("↕️ Введите два номера (откуда и куда), через пробел:",
                                                reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            elif text == "📊 Ответы пользователей":
                msg = "📊 Ответы:\n\n"
                for uid, d in data.get("answers", {}).items():
                    msg += f"👤 {uid} ({d.get('lang', 'ru')}):\n"
                    for qid, val in d["answers"].items():
                        msg += f"  {qid}: {val}\n"
                    msg += "\n"
                await update.message.reply_text(msg or "Ответов нет.")
            return

    if "lang" not in context.user_data:
        await handle_language_selection(update, context)
        return

    q = context.user_data.get("current_question")
    if not q:
        await update.message.reply_text("⚠️ Нажмите /start, чтобы начать опрос.")
        return

    step = context.user_data.get("step", 0)

    if q["type"] == "choice" and text == "Другое":
        context.user_data["awaiting_other"] = True
        await update.message.reply_text("✏️ Введите свой вариант:")
        return

    if context.user_data.get("awaiting_other"):
        context.user_data["awaiting_other"] = False
        answer = text
    elif q["type"] == "choice":
        options = q["options"].get(context.user_data["lang"], q["options"].get("ru", []))
        if text not in options and text != "Другое":
            await update.message.reply_text("⚠️ Пожалуйста, выберите доступный вариант или нажмите 'Другое'.")
            return
        answer = text
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

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection))
    app.run_polling()
