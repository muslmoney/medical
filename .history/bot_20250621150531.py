import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

ADMIN_ID = [572979988, 103525470]
TOKEN = "7539569165:AAF6TUZAS0vZAHe7wGS4iKwesfDsnXPbTVA"
CHANNEL_ID = -1001234567890  # ⬅️ Замени на ID своего канала
DATA_FILE = "questions.json"

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


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def send_user_answers_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    answers = context.user_data.get("answers", {})
    lang = context.user_data.get("lang", "ru")

    msg = f"📩 <b>Ответ от:</b> {user.full_name} (@{user.username or '—'})\n🆔 <code>{user.id}</code>\n🕒 <i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>\n\n"

    data = load_data()
    for q in data["questions"]:
        qid = str(q["id"])
        question_text = q["text"].get(lang, q["text"].get("ru", "❓"))
        answer = answers.get(qid, "—")
        msg += f"<b>{question_text}</b>\n{answer}\n\n"

    await context.bot.send_message(chat_id=CHANNEL_ID, text=msg.strip(), parse_mode="HTML")


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
        await send_user_answers_to_channel(update, context)
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


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lang = context.user_data.get("lang", "ru")

    if any(text == BUTTONS["restart"][code] for code in LANGUAGES.values()):
        await start(update, context)
        return

    if text.lower() in ["🔙", "отмена", "🔙 отмена", BUTTONS["cancel"][lang].lower()]:
        await cancel_action(update, context)
        return

    if context.user_data.get("step") == -1:
        await handle_language_selection(update, context)
        return

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    app.run_polling()
