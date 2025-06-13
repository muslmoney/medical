import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = 572979988
TOKEN = "7366253745:AAEGD7nh93tBAg-g70ZDXlpyRnEaT_xXLkk"
DATA_FILE = "questions.json"

admin_keyboard = [
    ["📋 Список вопросов", "➕ Добавить вопрос"],
    ["✏️ Редактировать вопрос", "❌ Удалить вопрос"],
    ["📊 Ответы пользователей"]
]

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Только администратор может использовать эту команду.")
        return
    reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
    await update.message.reply_text("🔐 Админ-панель:", reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = 0
    context.user_data["answers"] = {}
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    step = context.user_data.get("step", 0)
    if step >= len(data["questions"]):
        data["answers"][str(update.effective_user.id)] = context.user_data["answers"]
        save_data(data)
        await update.message.reply_text("Спасибо за участие!")
        return

    q = data["questions"][step]
    keyboard = [[opt] for opt in q["options"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(q["text"], reply_markup=markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    data = load_data()

    if user_id == ADMIN_ID:
        if context.user_data.get("admin_action") == "add_question":
            context.user_data["new_q_text"] = text
            context.user_data["admin_action"] = "add_options"
            await update.message.reply_text("🔢 Введите варианты ответа через запятую:")
            return
        elif context.user_data.get("admin_action") == "add_options":
            options = [opt.strip() for opt in text.split(",")]
            new_question = {
                "id": len(data["questions"]) + 1,
                "text": context.user_data["new_q_text"],
                "options": options
            }
            data["questions"].append(new_question)
            save_data(data)
            context.user_data["admin_action"] = None
            await update.message.reply_text("✅ Вопрос добавлен.")
            return
        elif context.user_data.get("admin_action") == "delete_question":
            try:
                q_id = int(text)
                data["questions"] = [q for q in data["questions"] if q["id"] != q_id]
                for i, q in enumerate(data["questions"], start=1):
                    q["id"] = i
                save_data(data)
                await update.message.reply_text("❌ Вопрос удалён.")
            except:
                await update.message.reply_text("⚠️ Введите корректный номер.")
            context.user_data["admin_action"] = None
            return
        elif context.user_data.get("admin_action") == "edit_question":
            try:
                q_id = int(text)
                context.user_data["edit_id"] = q_id
                context.user_data["admin_action"] = "edit_text"
                await update.message.reply_text("✏️ Введите новый текст вопроса:")
            except:
                await update.message.reply_text("⚠️ Введите корректный номер.")
            return
        elif context.user_data.get("admin_action") == "edit_text":
            for q in data["questions"]:
                if q["id"] == context.user_data["edit_id"]:
                    q["text"] = text
                    break
            save_data(data)
            context.user_data["admin_action"] = None
            await update.message.reply_text("✅ Вопрос обновлён.")
            return
        elif text in [btn for row in admin_keyboard for btn in row]:
            if text == "📋 Список вопросов":
                msg = "📋 Вопросы:\n\n"
                for q in data["questions"]:
                    msg += f"{q['id']}. {q['text']}\n"
                await update.message.reply_text(msg or "Нет вопросов.")
            elif text == "➕ Добавить вопрос":
                context.user_data["admin_action"] = "add_question"
                await update.message.reply_text("📝 Введите текст нового вопроса:")
            elif text == "❌ Удалить вопрос":
                context.user_data["admin_action"] = "delete_question"
                await update.message.reply_text("🗑 Введите номер вопроса для удаления:")
            elif text == "✏️ Редактировать вопрос":
                context.user_data["admin_action"] = "edit_question"
                await update.message.reply_text("✏️ Введите номер вопроса для редактирования:")
            elif text == "📊 Ответы пользователей":
                msg = "📊 Ответы:\n\n"
                for uid, ans in data["answers"].items():
                    msg += f"👤 Пользователь {uid}:\n"
                    for q_id, a in ans.items():
                        msg += f"  Вопрос {q_id}: {a}\n"
                    msg += "\n"
                await update.message.reply_text(msg or "Нет ответов.")
            return

    # пользователь — не админ, обычный опрос
    if "answers" not in context.user_data:
        context.user_data["answers"] = {}

    step = context.user_data.get("step", 0)
    if step < len(data["questions"]):
        q = data["questions"][step]
        context.user_data["answers"][str(q["id"])] = text
        context.user_data["step"] += 1
        await send_question(update, context)

# Точка входа
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.run_polling()
