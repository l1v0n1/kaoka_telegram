import statistics
import emoji
from config import vipsum
import logging
import functools
import re
import time
import asyncio
from functools import lru_cache

# Configure logger
logger = logging.getLogger(__name__)

# Constants for better maintainability
SYMBOLS_BLACKLIST = frozenset("""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""")
CITY_BLACKLIST = frozenset("""!"#$%&'()*+,./:;<=>?@[\]^_`{|}~""")

# Precompile regex patterns for better performance
SYMBOL_PATTERN = re.compile(r'[!"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~]')
CITY_PATTERN = re.compile(r'[!"#$%&\'()*+,./:;<=>?@\[\\\]^_`{|}~]')

# Payment cache to avoid repeated requests
_payment_cache = {}
_payment_cache_ttl = 300  # 5 minutes

# Optimization: Using set lookup is O(1) vs iterating through a string which is O(n)
async def simbols_exists(word):
	"""Check if word contains any blacklisted symbols (optimized with regex)"""
	if not word:
		return False
	return SYMBOL_PATTERN.search(word) is not None


async def city_exists(word):
	"""Check if city name contains any blacklisted symbols (optimized with regex)"""
	if not word:
		return False
	return CITY_PATTERN.search(word) is not None


# Precompute emoji mapping for better performance
EMOJI_MAPPING = {
	0: emoji.emojize(':zero:', language='alias'),
	1: emoji.emojize(':one:', language='alias'),
	2: emoji.emojize(':two:', language='alias'),
	3: emoji.emojize(':three:', language='alias'),
	4: emoji.emojize(':four:', language='alias'),
	5: emoji.emojize(':five:', language='alias'),
	6: emoji.emojize(':six:', language='alias'),
	7: emoji.emojize(':seven:', language='alias'),
	8: emoji.emojize(':eight:', language='alias'),
	9: emoji.emojize(':nine:', language='alias'),
	10: emoji.emojize(':ten:', language='alias')
}

# Use LRU cache for emojies function
@lru_cache(maxsize=20)
async def emojies(num):
	"""Return emoji representation of a number (cached)"""
	return EMOJI_MAPPING.get(num)


async def pay(wallet_p2p):
	"""Create a payment invoice with QIWI (with caching to avoid rate limits)"""
	try:
		# Check if we already have a recent active payment in cache
		current_time = time.time()
		for bill_id, (link, timestamp) in list(_payment_cache.items()):
			if current_time - timestamp < _payment_cache_ttl:
				try:
					# Check if this bill is still valid
					status = await check_payment(wallet_p2p, bill_id)
					if status == "WAITING" or status == "PENDING":
						# Return the cached payment info
						return link, bill_id
				except:
					# If error checking status, remove from cache
					_payment_cache.pop(bill_id, None)
			else:
				# Remove expired cache entries
				_payment_cache.pop(bill_id, None)
				
		# Create a new payment
		invoice = wallet_p2p.create_p2p_bill(amount=vipsum)
		if not invoice:
			logger.error("Failed to create payment invoice")
			return None, None
			
		link = invoice.get('payUrl') or invoice.get('pay_url')
		bid = invoice.get('billId') or invoice.get('bill_id')
		
		if link and bid:
			# Cache the new payment info
			_payment_cache[bid] = (link, current_time)
			
		return link, bid
	except Exception as e:
		logger.error(f"Payment error: {str(e)}")
		return None, None


async def check_payment(wallet_p2p, bill_id):
	"""Check payment status with error handling and retries"""
	max_retries = 3
	retry_delay = 1  # seconds
	
	for attempt in range(max_retries):
		try:
			# Try multiple methods to get status for compatibility
			try:
				payment_info = wallet_p2p.get_bill_status(bill_id=bill_id)
				if payment_info:
					status = payment_info.get('status')
					if status:
						return status
			except:
				pass
				
			try:
				payment_info = wallet_p2p.check_p2p_bill(bill_id=bill_id)
				if payment_info:
					status = payment_info.get('status')
					if status:
						return status
						
					# Try to get status from nested object if needed
					status_obj = payment_info.get('status', {})
					if isinstance(status_obj, dict):
						value = status_obj.get('value')
						if value:
							return value
			except:
				pass
				
			# If we get here, try the invoice_status method
			try:
				status = wallet_p2p.invoice_status(bill_id=bill_id)
				if status and isinstance(status, dict):
					value = status.get("status", {}).get("value")
					if value:
						return value
			except:
				pass
				
			# If we couldn't get status by any method, return None
			return None
				
		except Exception as e:
			if attempt < max_retries - 1:
				logger.warning(f"Error checking payment status, attempt {attempt+1}: {str(e)}")
				await asyncio.sleep(retry_delay)
			else:
				logger.error(f"Failed to check payment status after {max_retries} attempts: {str(e)}")
				return None
