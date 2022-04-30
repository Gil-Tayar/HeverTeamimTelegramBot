# Hever chargeable cards telegram bot

## Features

 - Check your balance on both the blue (Teamim) & yellow cards
 - Charge cards

## How to use
 1. Create your own telegram bot with [BotFather](https://t.me/botfather)
 2. Clone the repository
 3. Copy "config.example.yml" to "config.yml" in the same directory
 4. Edit the configuration file with your personal data
    - Get your own user ID from [userinfobot](https://t.me/userinfobot)
 5. Run from command line: `python bot.py`

## Example Configuration file
```yaml
telegram:
  api-key: 19345890345:ABN9gQ9UH4UovTD0dGUZGFvb0ZZeisvNWVg
  allowed-users:
    - 3745839457

hever:
  username: 3453465462
  password: sfgj88n3

credit-card:
  number: 5326100348392750
  expiry-year: 26
  expiry-month: 10
```
