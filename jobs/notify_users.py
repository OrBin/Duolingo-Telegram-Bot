"""
# Partial Duolingo API reference: http://tschuy.com/duolingo/

# Possibly interesting data fields:
print json_data[u'language_data'][u'ru'][u'language_strength']
print json_data[u'language_data'][u'ru'][u'level']
print json_data[u'language_data'][u'ru'][u'level_left']
print json_data[u'language_data'][u'ru'][u'level_percent']
print json_data[u'language_data'][u'ru'][u'level_points']
print json_data[u'language_data'][u'ru'][u'level_progress']
print json_data[u'language_data'][u'ru'][u'max_depth_learned']
print json_data[u'language_data'][u'ru'][u'max_tree_level']
print json_data[u'language_data'][u'ru'][u'num_skills_learned']
print json_data[u'language_data'][u'ru'][u'points']
print json_data[u'language_data'][u'ru'][u'streak']
print json_data[u'language_data'][u'ru'][u'max_tree_level']
print json_data[u'rupees']
print json_data[u'site_streak']
print json_data[u'streak_extended_today']
print json_data[u'last_streak'][u'last_reached_goal']

#pprint.pprint(json_data[u'language_data'][u'ru'][u'next_lesson'], indent=4)
#pprint.pprint(json_data[u'language_data'][u'ru'][u'skills'][0], indent=4)
"""

import logging
import os
import pymongo
import requests
from telegram.ext import Updater
from telegram import ParseMode
from config import config

MAX_REQUEST_RETRIES = 3

def get_user_data(duolingo_username):
    response = None
    logging.info("Fetching %s duolingo user data", duolingo_username)

    for i in range(1, MAX_REQUEST_RETRIES + 1):
        try:
            logging.info("Trying to get %s user data grades, attempt %s of %s" % (duolingo_username, i, MAX_REQUEST_RETRIES))
            response = requests.get('https://www.duolingo.com/api/1/users/show?username=' + duolingo_username, timeout=1)
            break
        except requests.exceptions.Timeout as timeout_err:
            if i != MAX_REQUEST_RETRIES:
                logging.info("Timeout reached. Retrying...")
            else:
                logging.info("Maximum attempts reached. Exiting.")
                return None

    return response.json()


logging.basicConfig(filename=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)) + "/" + 'log.txt',
					filemode='a',
					level=logging.INFO,
					format="%(asctime)s %(levelname)s %(module)s %(message)s",
					datefmt='%Y-%m-%d %H:%M:%S %Z')

dp = Updater(config.bot_token).dispatcher
mongo_client = pymongo.MongoClient()
mongo_db = mongo_client.duolingo_telegram_bot
users = mongo_db.users_data.find({})
mongo_client.close()

for user in users:
    data = get_user_data(user[u'duolingo_username'])
    if not data:
        logging.error("Could not get data for duolingo user %s (chat id %s)", user[u'duolingo_username'], user[u'chat_id'])
    elif data[u'streak_extended_today']:
        logging.info("Duolingo user %s (chat id %s) has done a good job today!", user[u'duolingo_username'], user[u'chat_id'])
    else:
        dp.bot.send_message(chat_id=user[u'chat_id'],
                            text="""Hi! You haven\'t completed your daily goal for today yet...
continue your <b>%s</b> day streak.""" % data[u'site_streak'],
                            parse_mode=ParseMode.HTML)
        logging.info("Sent a reminder to duolingo user %s (chat id %s)", user[u'duolingo_username'], user[u'chat_id'])



