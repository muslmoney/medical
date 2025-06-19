import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "7366253745:AAEGD7nh93tBAg-g70ZDXlpyRnEaT_xXLkk"
DATA_FILE = "questions.json"
ANSWERS_FILE = "answers.json"

LANGUAGES = {
    "Русский": "ru",
    "O'zbekcha": "uz",
    "English": "en"
}

TEXTS = {
    "thank_you": {
        "ru": "✅ Спасибо за участие!\n\n🔄 Хотите пройти опрос заново?",
        "uz": "✅ Ishtirokingiz uchun rahmat!\n\n🔄 So‘rovnomani qayta boshlaysizmi?",
        "en": "✅ Thank you for participating!\n\n🔄 Want to start again?"
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

def save_user_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        save_user_answers(update, context)
        restart_btn = BUTTONS["restart"][lang]
        keyboard = [[restart_btn]]
        await update.message.reply_text(TEXTS["thank_you"][lang], reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
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

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)

    # перезапуск
    if any(text == BUTTONS["restart"][code] for code in LANGUAGES.values()):
        await start(update, context)
        return

    data = load_data()
    lang = context.user_data.get("lang", "ru")

    if text.lower() in ["🔙", "отмена", "🔙 отмена", BUTTONS["cancel"][lang].lower()]:
        await cancel_action(update, context)
        return

    if context.user_data.get("step") == -1:
        await handle_language_selection(update, context)
        return

    if user_id in map(str, ADMIN_ID):
        # [Админ-панель — как в предыдущем коде, оставь без изменений]
        pass  # Оставлено для краткости, у тебя уже реализовано

    q = context.user_data.get("current_question")
    if not q:
        await update.message.reply_text(TEXTS["use_start"][lang])
        return

    if q["type"] == "choice":
        options = q.get("options", {}).get(lang, [])
        if text == BUTTONS["other"].get(lang, "Другое"):
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

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("⛔ Только для админа.")
        return
    await update.message.reply_text("🔧 Админ-панель:", reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.run_polling()
