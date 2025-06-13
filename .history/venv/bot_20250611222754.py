import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "7366253745:AAEGD7nh93tBAg-g70ZDXlpyRnEaT_xXLkk"
DATA_FILE = "questions.json"

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = 0
    context.user_data["answers"] = {}
    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    step = context.user_data["step"]
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
    data = load_data()
    step = context.user_data.get("step", 0)
    if step < len(data["questions"]):
        q = data["questions"][step]
        context.user_data["answers"][str(q["id"])] = update.message.text
        context.user_data["step"] += 1
        await send_question(update, context)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
app.run_polling()
