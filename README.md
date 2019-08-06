# Hever Teamim Card Telegram Bot

## Features

 - check your balance on the "teamim" card
 - charge the hever "teamim" card

## How to use
 1. clone the repository
 2. copy "config.json.example" to "config.json" in the same directory
 3. edit config.json (with your personal data), more details [here](#example-configuration-file)
 4. Install python-telegram-bot by using the following pip command: pip install python-telegram-bot==12.0.0b1 --upgrade
 5. run from command line: `python bot.py`

## Example Configuration file
```
{
	"telegram_api_key": "587285866:jWBJbmaD_dHvVijV_ixJLmEcPEwUUgXsFg3",
	"telegram_chat_id": "445364189",
	"username": "034408997",
	"password": "264759062",
	"credit_card_number": "6136518373625938",
	"card_year": "2025",
	"card_month": "09"
}
```


In order to use this script, you must create your own bot on telegram. You can find more information on the subject here: [telegram bots introduction](https://core.telegram.org/bots)
