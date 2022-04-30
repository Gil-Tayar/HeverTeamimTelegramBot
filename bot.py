import logging
from functools import wraps
import locale
import gettext
import yaml
from enum import Enum

from telegram.ext import CallbackContext, Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from hever_api import HeverAPI, CardType

_ = gettext.gettext

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class CardUnchargeable(Exception):
    pass


class ChatState(Enum):
    waiting_for_charge_amount = 1
    waiting_for_fill_amount = 2
    waiting_for_transaction_confirmation = 3


def restricted(func):
    @wraps(func)
    def wrapped(self, update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.id not in self.config['telegram']['allowed-users']:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Access denied')
            return
        return func(self, update, context, *args, **kwargs)
    return wrapped


class Bot:
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

    def read_user_config(self, path='config.yml'):
        with open(path, 'rb') as f:
            data = f.read()
        return yaml.safe_load(data)

    def __init__(self):
        self.updater = None
        self.config = config = self.read_user_config()

        self.hever = HeverAPI(creds=config['hever'], credit_card_data=config['credit-card'])

        self.selected_card = CardType.blue

    @restricted
    def start(self, update: Update, context: CallbackContext):
        self.send_menu(_('Welcome!'), update, context)

    def send_menu(self, message, update: Update, context: CallbackContext):
        balance = self.hever.get_card_balance(self.selected_card)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=_('{}\n\nSelected card: {}').format(message, self.selected_card.value) +
                                        _('\nCurrent balance: ₪{balance:.2f}'
                                        '\nChargeable this month: ₪{chargeable-monthly:.2f}'
                                        '\nChargeable right now: ₪{chargeable-now:.2f}').format(**balance) +
                                        _('\nCurrent charge rates: {:.0%} and {:.0%}').format(*self.hever.charge_rates[self.selected_card]),
                                 reply_markup=Bot.main_menu)

    def send_confused(self, update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=_('Sorry, what were we talking about?'),
                                 reply_markup=self.startover_menu)

    @restricted
    def handle_action(self, update: Update, context: CallbackContext):
        action = update.callback_query.data

        if action == 'switch-card':
            self.switch_card()
            self.send_menu(_('Switched card!'), update, context)
            return

        elif action == 'charge-card':
            context.chat_data['state'] = ChatState.waiting_for_charge_amount
            context.bot.send_message(chat_id=update.effective_chat.id, text=_('With how much?'))

        elif action == 'fill-card':
            context.chat_data['state'] = ChatState.waiting_for_fill_amount
            context.bot.send_message(chat_id=update.effective_chat.id, text=_('How much is your bill?'))

        elif action == 'confirm-transaction':
            pass
            # context.bot.send_message(chat_id=update.effective_chat.id, text=_('Charging your card...'))

        elif action == 'cancel':
            context.chat_data.clear()
            self.send_menu(_('Start again?'), update, context)

        else:
            self.send_confused(update, context)

    @restricted
    def handle_amount(self, update: Update, context: CallbackContext):
        state = context.chat_data.get('state')

        amount = int(context.match.string)
        balance, chargeable_monthly, chargeable_now = self.hever.get_card_balance(self.selected_card).values()

        if state is ChatState.waiting_for_charge_amount:
            to_charge = amount
        elif state is ChatState.waiting_for_fill_amount:
            to_charge = max(amount - balance, 0)
        else:
            context.chat_data.clear()
            self.send_confused(update, context)
            return

        try:
            if to_charge == 0:
                context.chat_data.clear()
                update.message.reply_text(_('You have enough money, have fun!'))
                return

            elif chargeable_now < self.hever.min_charge_amount:
                context.chat_data.clear()
                update.message.reply_text(_("Sorry, but you can't charge your card right now with any amount. You have "
                                            "₪%.2f left") % balance)
                return

            elif to_charge > chargeable_now:
                to_charge = chargeable_now
                update.message.reply_text(
                    _("We can't charge your card with enough right now, but can charge it with ₪%.2f and fill it to "
                      "₪%.2f") % (chargeable_now, balance+chargeable_now),
                    reply_markup=self.transaction_confirmation_menu)

            elif chargeable_now >= to_charge:
                    to_charge = min(5, to_charge)
                    update.message.reply_text(_("We'll charge your card ₪%.2f to fill it to ₪%.2f.") % (to_charge, amount),
                                              reply_markup=self.transaction_confirmation_menu)

            else:
                context.chat_data.clear()
                update.message.reply_text(_("Sorry, I got confused. Let me see a doctor"))
        finally:
            context.chat_data['to_charge'] = to_charge
            context.chat_data['state'] = ChatState.waiting_for_transaction_confirmation

    def switch_card(self):
        if self.selected_card is CardType.blue:
            self.selected_card = CardType.yellow
        else:
            self.selected_card = CardType.blue

    def dispatch(self):
        self.updater = Updater(self.config['telegram']['api-key'], use_context=True)

        # Get the dispatcher to register handlers
        dp = self.updater.dispatcher

        dp.add_handler(CommandHandler('start', self.start))
        dp.add_handler(CallbackQueryHandler(self.handle_action))
        dp.add_handler(MessageHandler(Filters.regex(r'^\d+$'), self.handle_amount))
        dp.add_handler(MessageHandler(Filters.regex('.*'), self.send_confused))

        # Start the Bot
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        self.updater.idle()


def main():
    Bot().dispatch()


if __name__ == '__main__':
    # Make locale understand commas is number parsing!
    # See https://stackoverflow.com/questions/2953746/python-parse-comma-separated-number-into-int.
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    main()
