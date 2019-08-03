import requests
import re
import random

#HVR_LOGIN_PAGE = 'https://www.hvr.co.il/signin.aspx?tmpl=signin_m'
HVR_LOGIN_PAGE = 'https://www.hvr.co.il/signin.aspx'
HVR_HOME_PAGE = 'https://www.hvr.co.il/home_page.aspx?page=m_main&t=637003008000000000'
HVR_TEAMIM_CONTROL_URL = 'https://www.hvr.co.il/gift_2000.aspx'

class Hvr():
	def __init__(self, user_config):
		self.session = requests.session()
		self.username = user_config['username']
		self.password = user_config['password']
		self.credit_card_number = user_config['credit_card_number']
		self.card_year = user_config['card_year']
		self.card_month = user_config['card_month']

	def get_teamim_balance(self):
		# make sure session is up
		self.init_connection()

		# perform balance request
		payload2 = {
			'balance_only': 1,
			'current_max_month_load': 2000,
			'current_max_load': 1000,
			'vv': str(random.random())
		}
		balance_response = self.session.post(HVR_TEAMIM_CONTROL_URL, params={'food': 1}, data=payload2)

		# parse the the output
		balance_string = str(balance_response.content)[2:-1]
		balance = balance_string.split('|')
		#print("balance in card: {0}, total available: {1}, max amount for current load: {2}".format(*balance))
		reply = "יתרה בכרטיס: {0}\nיתרה לטעינה החודש: {1}\nסכום מירבי לטעינה: {2}".format(*balance)
		return reply

	def charge_teamim_card(self, amount=10):
		# make sure session is up
		self.init_connection()

		# build load payload
		load_page_response = self.session.get(HVR_TEAMIM_CONTROL_URL, params={'food': 1})
		try:
			sn = re.findall('<input type="hidden" name="sn" value="([a-z,0-9,-]*)">', str(load_page_response.content))[0]
		except Exception as e:
			return 'could not get sn token, aborting...'
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
		if result.status_code == 200:
			return 'טעינה הושלמה בהצלחה'
		return 'הטעינה לא הצליחה'

	def is_session_up(self):
		response = self.session.get(HVR_HOME_PAGE)
		if response.url.find('signin.aspx') != -1:
			# session disconnected
			self.session = requests.session()
			return False
		return True

	def init_connection(self):
		if self.is_session_up() == True:
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
			print('error in login, aborting...')
			return
