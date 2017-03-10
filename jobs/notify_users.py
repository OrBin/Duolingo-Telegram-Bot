"""
# Partial Duolingo API reference: http://tschuy.com/duolingo/

# More possibly interesting data fields:
print json_data[u'language_data'][u'ru'][u'level_points']
print json_data[u'language_data'][u'ru'][u'level_progress']
print json_data[u'language_data'][u'ru'][u'max_depth_learned']
print json_data[u'language_data'][u'ru'][u'max_tree_level']
print json_data[u'language_data'][u'ru'][u'streak']
print json_data[u'last_streak'][u'last_reached_goal']
"""

import logging
import os
import pymongo
import requests
from telegram.ext import Updater
from telegram import ParseMode
from config import config
from jinja2 import Template
import random

MAX_REQUEST_RETRIES = 3

def get_message(context):

    templates_text = [
        """Hi! You haven\'t met your daily goal for today yet...\ncontinue your <b>{{ current_streak }}</b> day streak.""",
        """Hey, what about increasing your streak to <b>{{ next_streak }}</b>..?""",
        """Wanna make your Duolingo streak <b>{{ next_streak }}</b>? Take a lesson now!""",
        """Only {{ score_left_to_next_level }} points left - take another step towards <b>level {{ next_level }}</b> today!""",
        """Don't forget to strengthen your {{ language_name }} today! Your skills are only {{ language_strength_percent }}% strong.""",
        """You haven't taken any  {{ language_name }} lesson today. Take <b>{{ next_lesson_title }}</b> lesson no. <b>{{ next_lesson_number }}</b> now! :)""",
        """Hey, you're on a {{ current_streak }} day streak! Isn't it the perfect time to make it <b>{{ next_streak }}</b>?""",
        """Only {{ score_left_to_next_level }} points left until you reach level {{ next_level }}!\nThat's pretty impressive, let's do it!""",
        """Whoa, you've learned {{ num_skills_learned }} skills by now! Keep this number growing in just a few minutes, promise not to annoy you again today!""",
        """Speaking {{ language_name }} is a useful skill! Spending only a few minutes of your time now will help you achieve it sooner!"""
    ]

    template = Template(random.choice(templates_text))
    return template.render(context)

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

logging.info("======= Starting notification job =======")
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
    elif ('mute' not in user) or (not user['mute']):
        logging.info("Duolingo user %s (chat id %s) is muted.", user[u'duolingo_username'], user[u'chat_id'])
    else:
        learning_language_data = data[u'language_data'][data[u'learning_language']]

        dp.bot.send_message(chat_id=user[u'chat_id'],
                            text=get_message({
                                'current_streak': data[u'site_streak'],
                                'next_streak': int(data[u'site_streak']) + 1,
                                'score_left_to_next_level': learning_language_data[u'level_left'],
                                'current_level': learning_language_data[u'level'],
                                'next_level': int(learning_language_data[u'level']) + 1,
                                'percent_to_next_level': learning_language_data[u'level_percent'],
                                'language_name': learning_language_data[u'language_string'],
                                'language_strength_percent': int(float(learning_language_data[u'language_strength']) * 100),
                                'num_skills_learned': learning_language_data[u'num_skills_learned'],
                                'language_points': learning_language_data[u'points'],
                                'lingots': data[u'rupees'],
                                'next_lesson_title': learning_language_data[u'next_lesson'][u'skill_title'],
                                'next_lesson_number': learning_language_data[u'next_lesson'][u'lesson_number']
                            }),
                            parse_mode=ParseMode.HTML)
        logging.info("Sent a reminder to duolingo user %s (chat id %s)", user[u'duolingo_username'], user[u'chat_id'])
