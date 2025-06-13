import json, csv, os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "7366253745:AAEGD7nh93tBAg-g70ZDXlpyRnEaT_xXLkk"
DATA_FILE = "questions.json"
EXPORT_FILE = "answers.csv"

LANGUAGES = {"Русский": "ru", "O'zbek": "uz", "English": "en"}
admin_keyboard = [["📋 Список вопросов", "➕ Добавить вопрос"],
                  ["✏️ Редактировать вопрос", "📤 Переместить вопрос"],
                  ["❌ Удалить вопрос", "📊 Ответы пользователей"],
                  ["📥 Экспорт в CSV"]]
cancel_keyboard = [["🔙 Отмена"]]


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"questions": [], "answers": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[k] for k in LANGUAGES.keys()]
    await update.message.reply_text("🌐 Выберите язык:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = LANGUAGES.get(update.message.text)
    if not lang:
        await update.message.reply_text("⚠️ Пожалуйста, выберите язык из предложенных.")
        return
    context.user_data["lang"] = lang
    context.user_data["step"] = 0
    context.user_data["answers"] = {}
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    step = context.user_data.get("step", 0)
    questions = data["questions"]
    if step >= len(questions):
        data.setdefault("answers", {})[str(update.effective_user.id)] = context.user_data["answers"]
        save_data(data)
        await update.message.reply_text("✅ Спасибо за участие!", reply_markup=ReplyKeyboardRemove())
        return

    q = questions[step]
    context.user_data["current_question"] = q
    text = q.get(f"text_{context.user_data['lang']}", q["text"])

    if q["type"] == "choice":
        keyboard = [[opt] for opt in q["options"]] + [["Другое"], ["🔙 Отмена"]]
    else:
        keyboard = [["🔙 Отмена"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)

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
        act = context.user_data.get("admin_action")
        if act == "add_question_text":
            context.user_data["new_q_text"] = text
            context.user_data["admin_action"] = "add_question_type"
            await update.message.reply_text("📌 Тип: choice или text:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            return
        elif act == "add_question_type":
            if text not in ["choice", "text"]:
                await update.message.reply_text("⚠️ Введите choice или text")
                return
            context.user_data["new_q_type"] = text
            if text == "choice":
                context.user_data["admin_action"] = "add_question_options"
                await update.message.reply_text("🔢 Введите варианты через запятую:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
            else:
                q = {"id": len(data["questions"]) + 1, "text": context.user_data["new_q_text"], "type": "text", "options": []}
                data["questions"].append(q)
                save_data(data)
                context.user_data.clear()
                await update.message.reply_text("✅ Вопрос добавлен.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return
        elif act == "add_question_options":
            options = list(set(o.strip() for o in text.split(",") if o.strip()))
            q = {"id": len(data["questions"]) + 1, "text": context.user_data["new_q_text"], "type": "choice", "options": options}
            data["questions"].append(q)
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Вопрос добавлен.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return
        elif act == "move_question":
            try:
                src, dest = map(int, text.split())
                if 1 <= src <= len(data["questions"]) and 1 <= dest <= len(data["questions"]):
                    item = data["questions"].pop(src - 1)
                    data["questions"].insert(dest - 1, item)
                    for i, q in enumerate(data["questions"], 1):
                        q["id"] = i
                    save_data(data)
                    await update.message.reply_text("📤 Перемещено.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ Неверные номера.")
            except:
                await update.message.reply_text("⚠️ Ошибка ввода")
            context.user_data.clear()
            return
        elif act == "delete_question":
            try:
                idx = int(text)
                if 1 <= idx <= len(data["questions"]):
                    data["questions"].pop(idx - 1)
                    for i, q in enumerate(data["questions"], 1):
                        q["id"] = i
                    save_data(data)
                    await update.message.reply_text("❌ Удалено.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ Неверный номер.")
            except:
                await update.message.reply_text("⚠️ Введите число")
            context.user_data.clear()
            return
        elif act == "edit_question":
            try:
                idx = int(text)
                if 1 <= idx <= len(data["questions"]):
                    context.user_data["edit_index"] = idx - 1
                    context.user_data["admin_action"] = "edit_question_text"
                    await update.message.reply_text("✏️ Новый текст:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ Неверный номер.")
            except:
                await update.message.reply_text("⚠️ Введите номер")
            return
        elif act == "edit_question_text":
            idx = context.user_data["edit_index"]
            data["questions"][idx]["text"] = text
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Обновлено.", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return

        # Обработка кнопок
        if text == "📋 Список вопросов":
            msg = "\n".join([f"{q['id']}. {q['text']} ({q['type']})" for q in data["questions"]]) or "Нет вопросов."
            await update.message.reply_text(msg)
        elif text == "➕ Добавить вопрос":
            context.user_data["admin_action"] = "add_question_text"
            await update.message.reply_text("📝 Введите текст вопроса:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
        elif text == "📤 Переместить вопрос":
            context.user_data["admin_action"] = "move_question"
            await update.message.reply_text("↕️ Введите два номера через пробел:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
        elif text == "❌ Удалить вопрос":
            context.user_data["admin_action"] = "delete_question"
            await update.message.reply_text("❌ Введите номер вопроса:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
        elif text == "✏️ Редактировать вопрос":
            context.user_data["admin_action"] = "edit_question"
            await update.message.reply_text("✏️ Введите номер вопроса:", reply_markup=ReplyKeyboardMarkup(cancel_keyboard, resize_keyboard=True))
        elif text == "📊 Ответы пользователей":
            msg = ""
            for uid, ans in data.get("answers", {}).items():
                msg += f"👤 {uid}:\n" + "\n".join([f"  {k}: {v}" for k, v in ans.items()]) + "\n\n"
            await update.message.reply_text(msg or "Нет ответов.")
        elif text == "📥 Экспорт в CSV":
            with open(EXPORT_FILE, "w", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["user_id"] + [q["text"] for q in data["questions"]])
                for uid, ans in data.get("answers", {}).items():
                    row = [uid] + [ans.get(str(q["id"]), "") for q in data["questions"]]
                    writer.writerow(row)
            await update.message.reply_text("✅ Ответы экспортированы в answers.csv")
        return

    # Пользователь
    q = context.user_data.get("current_question")
    if not q:
        await update.message.reply_text("⚠️ Нажмите /start для начала.")
        return

    step = context.user_data.get("step", 0)

    if q["type"] == "choice" and text == "Другое":
        context.user_data["awaiting_other"] = True
        await update.message.reply_text("✏️ Введите свой вариант:")
        return

    if context.user_data.get("awaiting_other"):
        context.user_data["awaiting_other"] = False
        answer = text
    elif q["type"] == "choice" and text not in q["options"] and text != "Другое":
        await update.message.reply_text("⚠️ Выберите из списка или нажмите 'Другое'")
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

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.run_polling()
