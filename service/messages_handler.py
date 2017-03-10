import re
import pymongo
import logging
import os
from telegram.ext import Updater, CommandHandler
from config import config # This line requires PYTHONPATH to include config's parent directory

SET_USERNAME_REGEXP = re.compile("\/set_username (\w+) *")

# /start handler
def start(bot, update):
    update.message.reply_text("""Hello! I am Duolingo Reminder Bot.
I will remind you to learn in Duolingo every day.

Let's get started by telling me what is your Duolingo username:
Please type /set_username <your_duolingo_username>

Type /help for help""")
    logging.info("/start message sent")

# /help handler
def help(bot, update):
    update.message.reply_text("""My available commands:
/help - to show this help message
/set_username <your_duolingo_username> - to let me know what is your duolingo username""")
    logging.info("/help message sent")

# /set_username handler
def set_username(bot, update):

    match = SET_USERNAME_REGEXP.match(update.message.text)
    if not match:
        update.message.reply_text('Invalid command structure.\nUsage: /set_username <duolingo_username>')
    else:
        duolingo_username = match.groups()[0]

        mongo_client = pymongo.MongoClient()
        mongo_db = mongo_client.duolingo_telegram_bot

        mongo_db.users_data.update(
            {
                "chat_id": update.message.chat_id
            },
            {
                "$set": {
                    "duolingo_username": duolingo_username
                },
                "$setOnInsert": {
                    "chat_id": update.message.chat_id
                }
            },
            upsert=True)

        mongo_client.close()

        update.message.reply_text('Username successfully saved as %s, thank you!' % duolingo_username)
        logging.info("/set_username: Chat id %s set username to %s", update.message.chat_id, duolingo_username)

# /mute and /unmute handler
def mute_and_unmute(bot, update):

    requested_to_mute = update.message.text.startswith("/mute")
    command = "mute" if requested_to_mute else "unmute"

    mongo_client = pymongo.MongoClient()
    mongo_db = mongo_client.duolingo_telegram_bot

    if mongo_db.users_data.find( { "chat_id": update.message.chat_id } ).count() > 0:

        mongo_db.users_data.update(
            {
                "chat_id": update.message.chat_id
            },
            {
                "$set": {
                    "mute": requested_to_mute
                }
            },
            upsert=False)

    mongo_client.close()

    if requested_to_mute:
        update.message.reply_text('Successfully muted reminders. Hope to see you soon!')
    else:
        update.message.reply_text('Successfully unmuted reminders. Glad to see you back!')

    logging.info("/%s: Chat id %s %sd", command, update.message.chat_id, command)

# Errors handler
def error(bot, update, error):
    logging.warning('Update "%s" caused error "%s"' % (update, error))


logging.basicConfig(filename=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)) + "/" + 'log.txt',
					filemode='a',
					level=logging.INFO,
					format="%(asctime)s %(levelname)s %(module)s %(message)s",
					datefmt='%Y-%m-%d %H:%M:%S %Z')

logging.info("**************** Starting service ****************")

# Create the Updater and pass it your bot's token.
updater = Updater(config.bot_token)

# Get the dispatcher to register handlers
dp = updater.dispatcher

# on different commands - answer in Telegram
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("help", help))
dp.add_handler(CommandHandler("set_username", set_username))
dp.add_handler(CommandHandler("mute", mute_and_unmute))
dp.add_handler(CommandHandler("unmute", mute_and_unmute))

# TODO Add "remind me in ..." option
# log all errors
dp.add_error_handler(error)

logging.info("Starting to listen")
# Start the Bot
updater.start_polling()

# Block until the user presses Ctrl-C or the process receives SIGINT,
# SIGTERM or SIGABRT. This should be used most of the time, since
# start_polling() is non-blocking and will stop the bot gracefully.
updater.idle()
