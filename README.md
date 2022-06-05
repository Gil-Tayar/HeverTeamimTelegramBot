# Hever chargeable cards telegram bot

## Features

 - Check your balance on both the blue (Teamim) & yellow cards
 - Charge cards

## How to use
 1. Create your own telegram bot with [BotFather](https://t.me/botfather)
 2. Clone the repository
 3. Copy "config.example.yml" to "config.yml" in the same directory
 4. Edit the `.env` file with your personal data
    - Get your own user ID from [userinfobot](https://t.me/userinfobot)
 5. Run from command line: `python bot.py`

## Deploy to GCP
1. Add your personal data as environment variables with the GCP Secrets Manager
2. Deploy
    ```bash
    gcloud run deploy bot --source . --platform managed --project hever-cards-telegram-bot --set-secrets telegram_api_key=telegram_api_key:latest --set-secrets hever_credentials=hever_credentials:latest --set-secrets payment_method=payment_method:latest --set-secrets telegram_allowed_users=telegram_allowed_users:latest
    ```
3. Set bot webhook
    ```bash
   curl https://api.telegram.org/bot{telegram_api_key}/setWebhook?url={gcp_service_url}
    ```

## Example environment variables
```
telegram_api_key=19345890345:ABN9gQ9UH4UovTD0dGUZGFvb0ZZeisvNWVg
telegram_allowed_users=3745839457,2741843457
hever_credentials=3453465462:sfgj88n3
payment_method=5326100348392750:26:10
```
