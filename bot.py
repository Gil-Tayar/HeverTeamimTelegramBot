import logging
from functools import wraps
import os
from enum import Enum

from dotenv import load_dotenv
from flask import Flask, request, Response
from telegram.ext import CallbackContext, Dispatcher, Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from common import _
from hever_api import HeverAPI, CardType, CardChargeException

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
webapp = Flask(__name__)
APP_HOME = os.environ['APP_HOME']


class CardUnchargeable(Exception):
    pass


class ChatState(Enum):
    idle = 0
    waiting_for_charge_amount = 1
    waiting_for_fill_amount = 2
    waiting_for_transaction_confirmation = 3


def restricted(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        if str(update.effective_chat.id) not in os.environ['telegram_allowed_users'].split(','):
            context.bot.send_message(chat_id=update.effective_chat.id, text='Access denied')
            return
        return func(update, context, *args, **kwargs)
    return wrapped


main_menu = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(_('Switch card'), callback_data='switch-card'),
        # InlineKeyboardButton(_('Check balance'), callback_data='check-balance'),
    ],
    [
        InlineKeyboardButton(_('Charge card'), callback_data='charge-card'),
        InlineKeyboardButton(_('Fill card'), callback_data='fill-card'),
    ]
])
transaction_confirmation_menu = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(_('Confirm, charge card'), callback_data='confirm-transaction'),
        InlineKeyboardButton(_('Cancel'), callback_data='cancel'),
    ]
])
startover_menu = ReplyKeyboardMarkup([[KeyboardButton(_('/start'))]])


def init_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CallbackQueryHandler(handle_action))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^\d+$'), handle_amount))
    dispatcher.add_handler(MessageHandler(Filters.regex('.*'), send_confused))


@restricted
def start(update: Update, context: CallbackContext):
    context.chat_data['selected_card'] = CardType.blue
    context.chat_data['state'] = ChatState.idle
    send_menu(_('Welcome!'), update, context)


def send_menu(message, update: Update, context: CallbackContext):
    balance = hever.get_card_balance(context.chat_data['selected_card'])
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=_('{}\n\nSelected card: {}').format(message, context.chat_data['selected_card'].value) +
                                  _('\nCurrent balance: ₪{balance:.2f}'
                                    '\nChargeable this month: ₪{chargeable-monthly:.2f}'
                                    '\nChargeable right now: ₪{chargeable-now:.2f}').format(**balance) +
                                  _('\nCurrent charge rates: {:.0%} and {:.0%}').format(*hever.charge_rates[context.chat_data['selected_card']]),
                             reply_markup=main_menu)


def send_confused(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=_('Sorry, what were we talking about?'),
                             reply_markup=startover_menu)


@restricted
def handle_action(update: Update, context: CallbackContext):
    action = update.callback_query.data

    try:
        state: ChatState = context.chat_data['state']
    except KeyError:
        send_confused(update, context)
        return

    if action == 'switch-card':
        switch_card(update, context)
        send_menu(_('Switched card!'), update, context)
        return

    elif action == 'charge-card':
        context.chat_data['state'] = ChatState.waiting_for_charge_amount
        context.bot.send_message(chat_id=update.effective_chat.id, text=_('With how much?'))

    elif action == 'fill-card':
        context.chat_data['state'] = ChatState.waiting_for_fill_amount
        context.bot.send_message(chat_id=update.effective_chat.id, text=_('How much is your bill?'))

    elif action == 'confirm-transaction' and state is ChatState.waiting_for_transaction_confirmation:
        context.chat_data['state'] = ChatState.idle
        context.bot.send_message(chat_id=update.effective_chat.id, text=_('Charging your card...'))

        try:
            hever.charge_card(context.chat_data['selected_card'], context.chat_data.pop('to-charge'))
            context.bot.send_message(chat_id=update.effective_chat.id, text=_("Card charged successfully!"))
        except CardChargeException as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text=e.args[0])

    elif action == 'cancel':
        context.chat_data.clear()
        send_menu(_('Start again?'), update, context)

    else:
        send_confused(update, context)


@restricted
def handle_amount(update: Update, context: CallbackContext):
    try:
        state = context.chat_data['state']
    except KeyError:
        send_confused(update, context)
        return

    amount = int(context.match.string)
    balance, chargeable_monthly, chargeable_now = hever.get_card_balance(context.chat_data['selected_card']).values()

    if state is ChatState.waiting_for_charge_amount:
        to_charge = amount
    elif state is ChatState.waiting_for_fill_amount:
        to_charge = max(amount - balance, 0)
    else:
        context.chat_data.clear()
        send_confused(update, context)
        return

    try:
        if to_charge == 0:
            context.chat_data.clear()
            update.message.reply_text(_('You have enough money, have fun!'))
            return

        elif chargeable_now < hever.min_charge_amount:
            context.chat_data.clear()
            update.message.reply_text(_("Sorry, but you can't charge your %s card right now with any amount. You have "
                                        "₪%.2f left") % (context.chat_data['selected_card'].value, balance))
            return

        elif to_charge > chargeable_now:
            to_charge = chargeable_now
            update.message.reply_text(
                _("We can't charge your %s card with enough right now, but can charge it with ₪%.2f and fill it to "
                  "₪%.2f") % (context.chat_data['selected_card'].value, chargeable_now, balance+chargeable_now),
                reply_markup=transaction_confirmation_menu)

        elif chargeable_now >= to_charge:
            to_charge = max(5, to_charge)
            update.message.reply_text(_("We'll charge your %s card ₪%.2f to fill it to ₪%.2f.") % (context.chat_data['selected_card'].value, to_charge, balance+to_charge),
                                      reply_markup=transaction_confirmation_menu)

        else:
            context.chat_data.clear()
            update.message.reply_text(_("Sorry, I got confused. Let me see a doctor"))
    finally:
        context.chat_data['to-charge'] = to_charge
        context.chat_data['state'] = ChatState.waiting_for_transaction_confirmation


def switch_card(update: Update, context: CallbackContext):
    try:
        current_card = context.chat_data['selected_card']
    except KeyError:
        send_confused(update, context)
        return

    if current_card is CardType.blue:
        context.chat_data['selected_card'] = CardType.yellow
    else:
        context.chat_data['selected_card'] = CardType.blue


hever = HeverAPI(os.environ)
bot = Bot(token=os.environ['telegram_api_key'])
dp = Dispatcher(bot, update_queue=None)
init_handlers(dp)


@webapp.post('/')
def index() -> Response:
    dp.process_update(Update.de_json(request.get_json(force=True), bot))
    return 'Request received', 200


if __name__ == '__main__':
    updater = Updater(os.environ['telegram_api_key'], use_context=True)

    init_handlers(updater.dispatcher)
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
