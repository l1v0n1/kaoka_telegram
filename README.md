# Kaoka Telegram Bot

A Telegram bot built with Python for user profiles, ratings, and interactions with MongoDB backend.

## Features

- User registration with photo, video, or voice message uploads
- Profile rating system where users can rate each other
- Caching system for improved performance
- VIP subscription system
- Top users leaderboard
- City-based filtering
- Admin panel for moderation
- Payment integration with QIWI

## Requirements

- Python 3.7+
- MongoDB
- Telegram Bot API Token

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kaoka_telegram.git
cd kaoka_telegram
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

4. Configure MongoDB:
- Install MongoDB if not already installed
- Create a database named 'baraboba' with a collection called 'posts'
- Create a unique index on the 'chat_id' field

5. Configure the bot:
   - Method 1: Edit `config.py` directly with your Telegram Bot API token and other settings
   - Method 2: Create a `.env` file based on `.env.example` and set your environment variables
   - Method 3: Set system environment variables directly

   The following settings need to be configured:
   - `TELEGRAM_API_TOKEN`: Your Telegram Bot API token (get from @BotFather)
   - `ADMIN_IDS`: Comma-separated list of admin user IDs
   - `ADMIN_USERNAME`: Admin contact username
   - `ADMIN_CHAT_ID`: Admin group chat ID for reports
   - `QIWI_NUMBER`: QIWI wallet phone number
   - `QIWI_SEC_TOKEN`: QIWI secret token

## Usage

Run the bot with:
```bash
python bot.py
```

## Docker Deployment

For Docker deployment:

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Project Structure

- `bot.py` - Main bot file with message handlers
- `database.py` - MongoDB interaction layer with caching
- `functions.py` - Utility functions
- `keyboard.py` - Keyboard layouts for the bot
- `config.py` - Configuration settings

## Performance Optimizations

- Multi-level caching for database operations
- Batched processing for API requests
- MongoDB indexing for faster queries
- Connection pooling

## License

MIT 