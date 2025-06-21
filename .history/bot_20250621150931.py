
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "7539569165:AAF6TUZAS0vZAHe7wGS4iKwesfDsnXPbTVA"
DATA_FILE = "questions.json"
ANSWERS_FILE = "answers.json"
CHANNEL_ID = -1002283959136  # ID канала для отправки ответов

LANGUAGES = {
    "Русский": "ru",
    "O'zbekcha": "uz",
    "English": "en"
}

TEXTS = {
    "thank_you": {
        "ru": "✅ Спасибо за участие!\n\n🔄 Хотите пройти опрос заново?",
        "uz": "✅ Ishtirokingiz uchun rahmat!\n\n🔄 So‘rovnomani qayta boshlaysizmi?",
        "en": "✅ Thank you for your participation!\n\n🔄 Want to start again?"
    },
    "choose_lang": {
        "ru": "🌐 Выберите язык:",
        "uz": "🌐 Tilni tanlang:",
        "en": "🌐 Choose your language:"
    },
    "cancelled": {
        "ru": "❌ Действие отменено.",
        "uz": "❌ Amaliyot bekor qilindi.",
        "en": "❌ Action cancelled."
    },
    "select_from_buttons": {
        "ru": "⚠️ Выберите вариант с кнопки.",
        "uz": "⚠️ Tugmalardan birini tanlang.",
        "en": "⚠️ Please choose from the buttons."
    },
    "enter_custom": {
        "ru": "✍️ Введите свой вариант:",
        "uz": "✍️ O'z variantingizni kiriting:",
        "en": "✍️ Enter your own option:"
    },
    "use_start": {
        "ru": "⚠️ Используйте /start для начала.",
        "uz": "⚠️ Boshlash uchun /start ni bosing.",
        "en": "⚠️ Use /start to begin."
    },
    "invalid_lang": {
        "ru": "⚠️ Пожалуйста, выберите язык через кнопку.",
        "uz": "⚠️ Iltimos, tilni tugma orqali tanlang.",
        "en": "⚠️ Please select a language using the button."
    }
}

BUTTONS = {
    "cancel": {
        "ru": "🔙 Отмена",
        "uz": "🔙 Bekor qilish",
        "en": "🔙 Cancel"
    },
    "other": {
        "ru": "Другое",
        "uz": "Boshqa",
        "en": "Other"
    },
    "restart": {
        "ru": "🔄 Начать заново",
        "uz": "🔄 Qaytadan boshlash",
        "en": "🔄 Restart"
    }
}

admin_keyboard = [
    ["📋 Список вопросов", "➕ Добавить вопрос"],
    ["✏️ Редактировать вопрос", "📤 Переместить вопрос"],
    ["❌ Удалить вопрос", "📊 Ответы пользователей"]
]

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def save_user_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
            all_answers = json.load(f)
    except FileNotFoundError:
        all_answers = {}

    all_answers[user_id] = {
        "timestamp": datetime.now().isoformat(),
        "responses": context.user_data["answers"]
    }

    with open(ANSWERS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_answers, f, ensure_ascii=False, indent=2)

    lang = context.user_data.get("lang", "ru")
    text_lines = [f"📥 Новый ответ от пользователя {user_id} ({datetime.now().isoformat()}):"]
    for qid, ans in context.user_data["answers"].items():
        text_lines.append(f"🔹 {qid}: {ans}")
    await context.bot.send_message(chat_id=CHANNEL_ID, text="\n".join(text_lines))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    buttons = [[lang] for lang in LANGUAGES]
    await update.message.reply_text(TEXTS["choose_lang"]["ru"], reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    context.user_data["step"] = -1

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = LANGUAGES.get(update.message.text.strip())
    if not lang:
        await update.message.reply_text(TEXTS["invalid_lang"]["ru"])
        return
    context.user_data["lang"] = lang
    context.user_data["step"] = 0
    context.user_data["answers"] = {}
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    step = context.user_data.get("step", 0)
    lang = context.user_data.get("lang", "ru")

    if step >= len(data["questions"]):
        await save_user_answers(update, context)
        restart_button = [[BUTTONS["restart"][lang]]]
        await update.message.reply_text(
            TEXTS["thank_you"][lang],
            reply_markup=ReplyKeyboardMarkup(restart_button, resize_keyboard=True)
        )
        context.user_data.clear()
        return

    q = data["questions"][step]
    context.user_data["current_question"] = q
    text = q["text"].get(lang, q["text"].get("ru", "❓"))
    cancel_btn = BUTTONS["cancel"].get(lang, "🔙 Отмена")
    other_btn = BUTTONS["other"].get(lang, "Другое")

    if q["type"] == "choice":
        options = q.get("options", {}).get(lang, [])
        keyboard = [[opt] for opt in options] + [[other_btn], [cancel_btn]]
    else:
        keyboard = [[cancel_btn]]

    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)
async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    context.user_data.clear()
    await update.message.reply_text(TEXTS["cancelled"][lang], reply_markup=ReplyKeyboardRemove())

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("⛔ Только для админа.")
        return
    await update.message.reply_text("🔧 Админ-панель:", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    data = load_data()
    lang = context.user_data.get("lang", "ru")

    # 🔄 Начать заново
    if any(text == BUTTONS["restart"][code] for code in LANGUAGES.values()):
        await start(update, context)
        return

    if text.lower() in ["🔙", "отмена", "🔙 отмена", BUTTONS["cancel"][lang].lower()]:
        await cancel_action(update, context)
        return

    if context.user_data.get("step") == -1:
        await handle_language_selection(update, context)
        return

    if user_id in map(str, ADMIN_ID):
        action = context.user_data.get("admin_action")
        if text in [btn for row in admin_keyboard for btn in row]:
            if text == "📋 Список вопросов":
                msg = "📋 Вопросы:\n\n"
                for q in data["questions"]:
                    msg += f"{q['id']}. {q['text'].get('ru', '❓')} ({q['type']})\n"
                await update.message.reply_text(msg)
            elif text == "➕ Добавить вопрос":
                context.user_data.update({
                    "admin_action": "add_question_text",
                    "lang_order": list(LANGUAGES.values()),
                    "lang_step": 0,
                    "new_q_text": {},
                })
                await update.message.reply_text("📝 Введите текст вопроса на ru:")
            elif text == "📤 Переместить вопрос":
                context.user_data["admin_action"] = "move_question"
                await update.message.reply_text("Введите номера: откуда и куда, через пробел:")
            elif text == "❌ Удалить вопрос":
                context.user_data["admin_action"] = "delete_question"
                await update.message.reply_text("Введите номер вопроса для удаления:")
            elif text == "✏️ Редактировать вопрос":
                context.user_data["admin_action"] = "edit_question"
                await update.message.reply_text("Введите номер вопроса для редактирования:")
            elif text == "📊 Ответы пользователей":
                try:
                    with open(ANSWERS_FILE, "r", encoding="utf-8") as f:
                        answers = json.load(f)
                except FileNotFoundError:
                    answers = {}

                msg = "📊 Ответы:\n\n"
                for uid, record in answers.items():
                    msg += f"👤 {uid} ({record.get('timestamp')}):\n"
                    for qid, val in record["responses"].items():
                        msg += f"  {qid}: {val}\n"
                await update.message.reply_text(msg or "Ответов нет.")
            return

        if action == "add_question_text":
            lang = context.user_data["lang_order"][context.user_data["lang_step"]]
            context.user_data["new_q_text"][lang] = text
            context.user_data["lang_step"] += 1
            if context.user_data["lang_step"] >= len(context.user_data["lang_order"]):
                context.user_data["admin_action"] = "select_type"
                await update.message.reply_text("📌 Выберите тип вопроса:", reply_markup=ReplyKeyboardMarkup([["📝 Текст", "📋 Выбор"]], resize_keyboard=True))
            else:
                next_lang = context.user_data["lang_order"][context.user_data["lang_step"]]
                await update.message.reply_text(f"📝 Введите текст вопроса на {next_lang}:")
            return

        if action == "select_type":
            if "текст" in text.lower():
                new_q = {
                    "id": len(data["questions"]) + 1,
                    "type": "text",
                    "text": context.user_data["new_q_text"],
                    "options": {}
                }
                data["questions"].append(new_q)
                save_data(data)
                await update.message.reply_text("✅ Вопрос добавлен.")
                context.user_data.clear()
            elif "выбор" in text.lower():
                context.user_data["new_q_options"] = {}
                context.user_data["lang_step"] = 0
                context.user_data["admin_action"] = "add_options"
                await update.message.reply_text("🔢 Введите варианты ответа на ru через запятую:")
            return

        if action == "add_options":
            lang = context.user_data["lang_order"][context.user_data["lang_step"]]
            context.user_data["new_q_options"][lang] = [x.strip() for x in text.split(",")]
            context.user_data["lang_step"] += 1
            if context.user_data["lang_step"] >= len(context.user_data["lang_order"]):
                new_q = {
                    "id": len(data["questions"]) + 1,
                    "type": "choice",
                    "text": context.user_data["new_q_text"],
                    "options": context.user_data["new_q_options"]
                }
                data["questions"].append(new_q)
                save_data(data)
                await update.message.reply_text("✅ Вопрос с вариантами добавлен.")
                context.user_data.clear()
            else:
                next_lang = context.user_data["lang_order"][context.user_data["lang_step"]]
                await update.message.reply_text(f"🔢 Введите варианты ответа на {next_lang} через запятую:")
            return

        if action == "delete_question":
            try:
                idx = int(text) - 1
                if 0 <= idx < len(data["questions"]):
                    del data["questions"][idx]
                    for i, q in enumerate(data["questions"]):
                        q["id"] = i + 1
                    save_data(data)
                    await update.message.reply_text("✅ Вопрос удалён.")
                else:
                    await update.message.reply_text("❗ Неверный номер.")
            except:
                await update.message.reply_text("⚠️ Введите корректный номер.")
            context.user_data.clear()
            return

        if action == "move_question":
            try:
                src, dest = map(int, text.split())
                qlist = data["questions"]
                if 1 <= src <= len(qlist) and 1 <= dest <= len(qlist):
                    q = qlist.pop(src - 1)
                    qlist.insert(dest - 1, q)
                    for i, q in enumerate(qlist): q["id"] = i + 1
                    save_data(data)
                    await update.message.reply_text("↕️ Перемещено.")
                else:
                    await update.message.reply_text("⚠️ Неверный номер.")
            except:
                await update.message.reply_text("⚠️ Ошибка ввода.")
            context.user_data.clear()
            return

        if action == "edit_question":
            try:
                idx = int(text) - 1
                if 0 <= idx < len(data["questions"]):
                    context.user_data["edit_index"] = idx
                    context.user_data["lang_step"] = 0
                    context.user_data["lang_order"] = list(LANGUAGES.values())
                    context.user_data["admin_action"] = "edit_text"
                    await update.message.reply_text("📝 Новый текст на ru:")
                else:
                    await update.message.reply_text("❗ Неверный номер.")
            except:
                await update.message.reply_text("⚠️ Ошибка ввода.")
            return

        if action == "edit_text":
            lang = context.user_data["lang_order"][context.user_data["lang_step"]]
            idx = context.user_data["edit_index"]
            data["questions"][idx]["text"][lang] = text
            context.user_data["lang_step"] += 1
            if context.user_data["lang_step"] >= len(context.user_data["lang_order"]):
                save_data(data)
                await update.message.reply_text("✅ Тексты обновлены.")
                context.user_data.clear()
            else:
                next_lang = context.user_data["lang_order"][context.user_data["lang_step"]]
                await update.message.reply_text(f"📝 Новый текст на {next_lang}:")
            return

    # Ответ пользователя на вопрос
    q = context.user_data.get("current_question")
    if not q:
        await update.message.reply_text(TEXTS["use_start"][lang])
        return

    if q["type"] == "choice":
        options = q.get("options", {}).get(lang, [])
        if text == BUTTONS["other"][lang]:
            context.user_data["awaiting_other"] = True
            await update.message.reply_text(TEXTS["enter_custom"][lang])
            return
        if context.user_data.get("awaiting_other"):
            answer = text
            context.user_data["awaiting_other"] = False
        elif text not in options:
            await update.message.reply_text(TEXTS["select_from_buttons"][lang])
            return
        else:
            answer = text
    else:
        answer = text

    context.user_data["answers"][str(q["id"])] = answer
    context.user_data["step"] += 1
    await send_question(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.run_polling()