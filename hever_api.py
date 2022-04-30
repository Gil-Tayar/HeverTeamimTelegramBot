import requests
import re
import random
from enum import Enum
from time import sleep

BASE_URL = 'https://www.hvr.co.il'
HOME_PAGE = BASE_URL + '/site/pg/hvr_home'
CARD_CONTROL_URL = BASE_URL + '/orders/gift_2000.aspx'

USER_AGENT = 'HeverBot-Mobile'  # just make sure 'mobile' is in the string :)

CHARGE_FACTOR1_REGEX = re.compile(r'var gift_card_factor1 = (0.\d{1,2})')
CHARGE_FACTOR2_REGEX = re.compile(r'var gift_card_factor2 = (0.\d{1,2})')


class CardType(Enum):
    yellow = 'Yellow (Hever shel Keva)'
    blue = 'Blue (Teamim)'

    def get_param(self):
        return int(self.name == 'blue')


class CardChargeException(Exception):
    pass


class LoginException(Exception):
    pass


class HeverAPI:
    def __init__(self, creds, credit_card_data):
        self.session = requests.Session()
        self.session.headers.update({'user-agent': USER_AGENT})

        self.username = creds['username']
        self.password = creds['password']

        self.credit_card_number = credit_card_data['number']
        self.card_year = credit_card_data['expiry-year']
        self.card_month = credit_card_data['expiry-month']

    charge_rates = {
        CardType.blue: (None, None),
        CardType.yellow: (None, None),
    }

    min_charge_amount = 5

    def get_charge_rates(self, card_type: CardType):
        info_resp = self.session.get(CARD_CONTROL_URL, params={'food': card_type.get_param()})

        factor_1 = float(CHARGE_FACTOR1_REGEX.search(info_resp.text).group(1))
        factor_2 = float(CHARGE_FACTOR2_REGEX.search(info_resp.text).group(1))

        return factor_1, factor_2

    def refresh_charge_rates(self):
        self.charge_rates[CardType.blue] = self.get_charge_rates(CardType.blue)
        sleep(2)  # probably some ugly protection mechanism they have
        self.charge_rates[CardType.yellow] = self.get_charge_rates(CardType.yellow)

    def get_card_balance(self, card_type: CardType):
        self.refresh_session()

        payload = {
            'balance_only': 1,
            'current_max_month_load': 2000,
            'current_max_load': 1000,
            'vv': str(random.random())
        }

        balance_resp = self.session.post(CARD_CONTROL_URL, params={'food': card_type.get_param()}, data=payload)
        balance, chargeable_monthly, chargeable_now = map(float, balance_resp.text.split('|'))

        return {
            'balance': balance,
            'chargeable-monthly': chargeable_monthly,
            'chargeable-now': chargeable_now,
        }

    def charge_card(self, card_type: CardType, amount=10):
        self.refresh_session()
        pass

    def refresh_session(self):
        resp = self.session.get(HOME_PAGE, allow_redirects=False)
        if resp.is_redirect:
            self.login()
            self.refresh_charge_rates()

    def login(self):
        self.session.get(BASE_URL)  # sadly this is required

        payload = {
            'tz': self.username,
            'password': self.password,
            'oMode': 'login',
        }

        resp = self.session.post(BASE_URL, data=payload)

        if 'cart.aspx' not in resp.text or 'email' not in self.session.cookies:
            raise LoginException("Login failed")
