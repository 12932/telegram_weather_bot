# Telegram Weather Bot

This is a Telegram bot that provides current weather information and forecasts for specified locations using the Foreca API.

## Features

- Get current weather conditions for a specified location.
- Receive a 3-day weather forecast.
- Simple commands to interact with the bot.

## Commands

- `/start` - Start the bot and receive a welcome message.
- `/help` - Display available commands.
- `/w <location>` - Get current weather for the specified location.
- `/wf <location>` - Get a 3-day weather forecast for the specified location.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/telegram-weather-bot.git
   cd telegram-weather-bot
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```

4. Run the bot:
   ```bash
   python telegram_weather_bot.py
   ```

## Logging

- Logs are stored in the `logs` directory.
- `weather_bot.log` contains general information logs.
- `weather_bot_errors.log` contains error logs with backtrace and diagnostics.