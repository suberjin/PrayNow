# Prayer Telegram Bot

A Telegram bot for recording and organizing prayers. This bot allows users to submit, categorize, view, edit, and delete prayers, providing a community-based prayer request system.

## Description

This Telegram bot is designed to help individuals and communities organize their prayer requests. Users can submit prayers under specific categories, view prayers from other community members, and manage their own prayer submissions.

### Features

- Submit prayers with category selection
- View personal prayers with edit/delete options
- Browse all community prayers by category
- Pagination for viewing large numbers of prayers
- Support for prayers of any length (automatically splits long texts)

## Technologies Used

- Python 3.11+
- aiogram 3.20+ (Telegram Bot API framework)
- SQLite (for database storage)
- asyncio (for asynchronous operations)
- python-dotenv (for environment variable management)
- json-log-formatter (for structured logging)

## Installation

### Prerequisites

- Python 3.11 or higher
- A Telegram Bot Token (obtained from [@BotFather](https://t.me/BotFather))

### Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/prayer-telegram-bot.git
   cd prayer-telegram-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root and add your Telegram Bot Token:
   ```
   TELEGRAM_TOKEN=your_bot_token_here
   ```

6. Start the bot:
   ```bash
   python bot.py
   ```

## Usage

1. Start the bot by sending `/start` in Telegram
2. Select from available options in the menu:
   - Send a prayer
   - View your prayers
   - View all prayers
3. When sending a prayer, select a category and then enter your prayer text
4. You can edit or delete your own prayers using the provided buttons

## Project Structure

- `bot.py` - Main entry point and bot initialization
- `handlers.py` - Message and callback handlers
- `services.py` - Database service functions
- `database.py` - Database connection and schema setup
- `requirements.txt` - Project dependencies

## License

This project is licensed under the MIT License - see the LICENSE file for details. 