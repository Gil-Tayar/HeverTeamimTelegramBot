#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
import random

#HVR_LOGIN_PAGE = 'https://www.hvr.co.il/signin.aspx?tmpl=signin_m'
HVR_LOGIN_PAGE = 'https://www.hvr.co.il/signin.aspx'
HVR_HOME_PAGE = 'https://www.hvr.co.il/home_page.aspx?page=m_main&t=637003008000000000'
HVR_TEAMIM_CONTROL_URL = 'https://www.hvr.co.il/gift_2000.aspx'
HVR_WRONG_CREDIT_CARD_MSG = "<br/><br/><div align=\"center\" style=\"height:400px\"><table width=\"80%\" bgcolor=\"red\" cellspacing=\"0\" cellpadding=\"20\" bordercolor=\"black\" border=\"2\">"

def init_session():
    session=requests.session()
        # Note: only accept and user-agent headers are needed, everything else is to look more innocent
    session.headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'he,en-US;q=0.9,en;q=0.8,he-IL;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'referer': 'https://www.hvr.co.il/signin.aspx?tmpl=signin_m&redirect=',
        'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 9; SM-G960F Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.157 Mobile Safari/537.36'
    }
    return session

class CardChargeException(Exception):
    pass


class HvrLoginException(Exception):
    pass

class Hvr():
    def __init__(self, user_config):
        self.session = init_session()
        self.username = user_config['username']
        self.password = user_config['password']
        self.credit_card_number = user_config['credit_card_number']
        self.card_year = user_config['card_year']
        self.card_month = user_config['card_month']


    def get_teamim_balance(self):
        # make sure session is up
        self.init_connection()

        # perform balance request
        payload = {
            'balance_only': 1,
            'current_max_month_load': 2000,
            'current_max_load': 1000,
            'vv': str(random.random())
        }
        balance_response = self.session.post(HVR_TEAMIM_CONTROL_URL, params={'food': 1}, data=payload)

        # parse the the output
        balance_string = str(balance_response.content)[2:-1] if str(balance_response.content).startswith("b'",0,2) else str(balance_response.content)
        balance = balance_string.split('|')

        return balance

    def format_teamim_balance(self, balance):
        reply = "יתרה בכרטיס: {0}\nיתרה לטעינה החודש: {1}\nסכום מירבי לטעינה: {2}".format(*balance)
        return reply

    def charge_teamim_card(self, amount=10):
        # make sure session is up
        self.init_connection()

        # build load payload
        load_page_response = self.session.get(HVR_TEAMIM_CONTROL_URL, params={'food': 1})
        sn_match = re.search('<input type="hidden" name="sn" value="([a-z,0-9,-]*)">', str(load_page_response.content))
        if not sn_match:
            raise CardChargeException("Could not find sn token in response")

        sn = sn_match.group(1)
        payload = {
            'price': amount,
            'card_num': self.credit_card_number,
            'card_year': self.card_year,
            'card_month': self.card_month,
            'chkTakanon': '',
            'om': 'load',
            'req_sent': 1,
            'food': 1,
            'sn': sn
        }

        # load the card
        result = self.session.post(HVR_TEAMIM_CONTROL_URL, data=payload)

        # return result
        if result.status_code != 200 or HVR_WRONG_CREDIT_CARD_MSG in result.text:
            raise CardChargeException("Card charge response indicated failure")

    def is_session_up(self):
        response = self.session.get(HVR_HOME_PAGE)
        if response.url.find('signin.aspx') != -1:
            # session disconnected
            self.session = init_session()
            return False
        return True

    def init_connection(self):
        if self.is_session_up():
            return
        self.perform_login()

    def perform_login(self):
        # get login page
        login_page_response = self.session.get(HVR_LOGIN_PAGE)
        try:
            if self.session.cookies.get('bn') == None:
                print('could not retrive sesssion id, aborting...')
            cn = re.findall('<input type="hidden" name="cn" value="([0-9]*)" />', str(login_page_response.content))[0]
        except Exception as e:
            print('error getting tokens')
            return

        # sign in
        payload = {
            'tz': self.username,
            'password': self.password,
            'oMode': 'login',
            'tmpl_filename': 'signin_m',
            'reffer': '',
            'redirect': 'home_page.aspx?page=m_main',
            'emailRestore': '',
            'email_id': 'mobile',
            'cn': cn,
            'email_loc': ''
        }
        login = self.session.post(HVR_LOGIN_PAGE, data=payload)
        if login.status_code != 200 or login.url.find('signin.aspx') != -1:
            raise HvrLoginException("Failed to login")
