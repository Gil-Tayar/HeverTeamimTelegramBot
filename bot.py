#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import json
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from functools import wraps
from hvr import *

hvr = None
user_config = {}

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

custom_keyboard = [[KeyboardButton('/charge'), KeyboardButton('/balance')]]
yes_no_keyboard = [[KeyboardButton('/no'), KeyboardButton('/yes')]]
reply_markup = ReplyKeyboardMarkup(custom_keyboard)
yes_no_markup = ReplyKeyboardMarkup(yes_no_keyboard)
remove_markup = ReplyKeyboardRemove()

waiting_for_amount = False
wating_for_confirmation = False
charge_amount = 0

def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        chat_id = update.message.chat.id
        if str(chat_id) != user_config['telegram_chat_id']:
            print("Unauthorized access denied for chat {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)
    return wrapped

@restricted
def check_balance(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(text="בודק...")
    reply = hvr.get_teamim_balance()

    update.message.reply_text(text=reply, reply_markup=reply_markup)
    update.message.reply_text(text='איך תרצה להמשיך?')

@restricted
def start_charge_process(update, context):
    global waiting_for_amount
    update.message.reply_text(text="בכמה להטעין?", reply_markup=remove_markup)
    waiting_for_amount = True

@restricted
def set_amount(update, context):
    global waiting_for_amount
    global wating_for_confirmation
    global charge_amount

    if waiting_for_amount == False:
        update.message.reply_text(text="לא חיכיתי לסכום טעינה...נסה מחדש בבקשה", reply_markup=reply_markup)

    waiting_for_amount = False
    if update.message.text.isnumeric() == True:
        charge_amount = int(update.message.text)
        update.message.reply_text(text="האם אתה בטוח שברצונך להטעין את הכרטיס \"חבר טעמים\" בסכום של: {0} ש\"ח?".format(charge_amount), reply_markup=yes_no_markup)
        wating_for_confirmation = True
    else:
     update.message.reply_text(text="הסכום אינו מספר, מבטל תהליך!", reply_markup=reply_markup)  
        
@restricted
def confirm_charge(update, context):
    global wating_for_confirmation
    global charge_amount

    if wating_for_confirmation == False:
        update.message.reply_text(text="לא חיכיתי לאישור עסקה, אנא נסה מחדש", reply_markup=reply_markup)

    wating_for_confirmation = False
    if update.message.text == '/no':
        update.message.reply_text(text="מבטל פעולה", reply_markup=reply_markup)
        charge_amount = 0
        update.message.reply_text(text='איך תרצה להמשיך?', reply_markup=reply_markup)
    elif update.message.text == '/yes':
        update.message.reply_text(text="מבצע טעינה", reply_markup=reply_markup)
        result = hvr.charge_teamim_card(charge_amount)
        
        # check the new balance
        balance = hvr.get_teamim_balance()
        
        # send reply to end user
        reply = "{0}\n{1}".format(result, balance)
        update.message.reply_text(text=reply, reply_markup=reply_markup)
        update.message.reply_text(text='איך תרצה להמשיך?')

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def initialize_user_config(path='config.json'):
    global user_config
    with open(path, 'rb') as f:
        data = f.read()
    user_config = json.loads(data)

def main():
    global hvr

    # load user configuration file
    initialize_user_config()

    # set Hvr instance
    hvr = Hvr(user_config)

    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(user_config["telegram_api_key"], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("balance", check_balance))
    dp.add_handler(CommandHandler("charge", start_charge_process))
    dp.add_handler(CommandHandler("yes", confirm_charge))
    dp.add_handler(CommandHandler("no", confirm_charge))
    dp.add_handler(RegexHandler("^[0-9]+.$", set_amount))

    # log all errors
    dp.add_error_handler(error)

    # send first conversation message and set the keyboad layout
    updater.bot.send_message(chat_id=user_config['telegram_chat_id'], text="מה תרצה לעשות?", reply_markup=reply_markup)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
