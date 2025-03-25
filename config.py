import os
from typing import List

# Load environment variables with fallbacks
API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
admin: List[int] = [int(x) for x in os.environ.get('ADMIN_IDS', '123456789').split(',')]
username = os.environ.get('ADMIN_USERNAME', '@your_username')
unban = os.environ.get('UNBAN_COST', '200')
vipsum = os.environ.get('VIP_COST', '99')
admchat = int(os.environ.get('ADMIN_CHAT_ID', '-1001000000000'))
number = os.environ.get('QIWI_NUMBER', '70000000000')
QIWI_SEC_TOKEN = os.environ.get('QIWI_SEC_TOKEN', 'YOUR_QIWI_SECRET_TOKEN')