import motor.motor_asyncio
import certifi
import functions
import logging
import asyncio
import time
import os
from contextlib import asynccontextmanager
from functools import lru_cache


# Configure logger
logger = logging.getLogger(__name__)

# Database connection with connection pooling
CONNECTION_STRING = os.environ.get("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(
    CONNECTION_STRING, 
    # Use TLS for remote connections but not for localhost
    tlsCAFile=certifi.where() if "localhost" not in CONNECTION_STRING and "127.0.0.1" not in CONNECTION_STRING else None,
    maxPoolSize=10,  # Connection pooling for better performance
    serverSelectionTimeoutMS=5000,  # Timeout for server selection
    connectTimeoutMS=10000,  # Timeout for connection
)
db = client.baraboba
posts = db.posts

# Set up indexes for better query performance
async def ensure_indexes():
    """Create indexes for common queries to improve performance"""
    await posts.create_index("chat_id", unique=True)
    await posts.create_index("name")
    await posts.create_index([("count", -1), ("active", 1), ("block", 1)])
    await posts.create_index([("mark", -1), ("active", 1), ("block", 1)])
    logger.info("Database indexes created")

# Cache for frequently accessed documents
_document_cache = {}
_cache_ttl = 300  # seconds
_bulk_cache = {}  # Cache for bulk operations results

async def _get_from_cache(chat_id):
    """Get document from cache if available and not expired"""
    if chat_id in _document_cache:
        doc, timestamp = _document_cache[chat_id]
        if (time.time() - timestamp) < _cache_ttl:
            return doc
        # Remove expired cache entry
        del _document_cache[chat_id]
    return None

async def _add_to_cache(chat_id, document):
    """Add document to cache with current timestamp"""
    if document:
        _document_cache[chat_id] = (document, time.time())

def _get_cache_key(operation, **params):
    """Generate a cache key for bulk operations"""
    return f"{operation}:{hash(frozenset(params.items()))}"

async def _get_from_bulk_cache(key):
    """Get bulk operation result from cache if available and not expired"""
    if key in _bulk_cache:
        result, timestamp = _bulk_cache[key]
        if (time.time() - timestamp) < _cache_ttl:
            return result
        # Remove expired cache entry
        del _bulk_cache[key]
    return None

async def _add_to_bulk_cache(key, result):
    """Add bulk operation result to cache with current timestamp"""
    if result is not None:
        _bulk_cache[key] = (result, time.time())

@asynccontextmanager
async def db_operation():
    """Context manager for database operations with error handling"""
    try:
        yield
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise

async def check(chat_id):
    """Check if a document with the given chat_id exists"""
    # First check cache
    cached_doc = await _get_from_cache(chat_id)
    if cached_doc:
        return True
        
    async with db_operation():
        return await posts.count_documents({'chat_id': chat_id}) > 0


async def insert(chat_id, name, photo, city):
    """Insert a new user document"""
    async with db_operation():
        if not await check(chat_id):
            post_data = {
                'chat_id': chat_id,
                'name': name,
                'photo': photo,
                'count': 0,
                'by': [],
                'mark': 0,
                'block': 0,
                'active': 1,
                'answer': [],
                'vip': 0,
                'city': city
            }
            await posts.insert_one(post_data)
            await _add_to_cache(chat_id, post_data)


async def get_document(chat_id):
    """Get a document by chat_id with caching"""
    # Try to get from cache first
    cached_doc = await _get_from_cache(chat_id)
    if cached_doc:
        return cached_doc
    
    # If not in cache, get from database
    async with db_operation():
        document = await posts.find_one({'chat_id': chat_id})
        await _add_to_cache(chat_id, document)
        return document


async def change_field(chat_id, field, key):
    """Update a specific field in a document"""
    async with db_operation():
        await posts.update_one({'chat_id': chat_id}, {'$set': {field: key}})
        # Invalidate cache for this chat_id
        if chat_id in _document_cache:
            del _document_cache[chat_id]


async def find_answer(chat_id):
    """Find answers for a specific chat ID"""
    async with db_operation():
        return await posts.find_one({'chat_id': chat_id}, {'answer.id': 1})


async def get_users_by_name(name):
    """Find users by name with regex search"""
    # Use cache for name searches if the same name is searched multiple times
    cache_key = _get_cache_key("name_search", name=name)
    cached_result = await _get_from_bulk_cache(cache_key)
    if cached_result:
        return cached_result
        
    async with db_operation():
        result = [doc async for doc in posts.find(
            {'name': {'$regex': name, '$options': 'i'}},
            {'chat_id': 1, 'name': 1, 'photo': 1, 'count': 1, 'mark': 1, 'active': 1, 'city': 1}  # Project only needed fields
        )]
        await _add_to_bulk_cache(cache_key, result)
        return result


async def get_random_form(chat_id, city):
    """Get a random profile for rating that matches the city criteria"""
    query = {
        'by.id': {'$ne': chat_id},
        'chat_id': {'$ne': chat_id},
        'block': {'$ne': 1},
        'active': {'$ne': 0},
        'city': {'$regex': city, '$options': 'i'}
    }
    pipeline = [
        {'$match': query},
        {'$project': {'chat_id': 1, 'name': 1, 'photo': 1, 'city': 1}},  # Project only needed fields
        {'$sample': {'size': 1}}
    ]
    
    async with db_operation():
        result = [doc async for doc in posts.aggregate(pipeline)]
        return await get_default_form(chat_id) if not result else result


async def get_default_form(chat_id):
    """Get a random profile for rating with no city filter"""
    query = {
        'by.id': {'$ne': chat_id},
        'chat_id': {'$ne': chat_id},
        'block': {'$ne': 1},
        'active': {'$ne': 0}
    }
    pipeline = [
        {'$match': query},
        {'$project': {'chat_id': 1, 'name': 1, 'photo': 1, 'city': 1}},  # Project only needed fields
        {'$sample': {'size': 1}}
    ]
    
    async with db_operation():
        result = [doc async for doc in posts.aggregate(pipeline)]
        return False if not result else result


async def update_by(chat_id, id, mark, comm):
    """Add a rating to a user profile"""
    async with db_operation():
        await posts.update_one(
            {'chat_id': chat_id}, 
            {'$push': {'by': {'id': id, 'mark': mark, 'comment': comm}}}, 
            upsert=True
        )
        # Invalidate cache for this chat_id
        if chat_id in _document_cache:
            del _document_cache[chat_id]


async def update_answer(chat_id, id):
    """Add an answer record to a user profile"""
    async with db_operation():
        await posts.update_one(
            {'chat_id': chat_id}, 
            {'$push': {'answer': {'id': id}}}, 
            upsert=True
        )
        # Invalidate cache for this chat_id
        if chat_id in _document_cache:
            del _document_cache[chat_id]


async def get_likers(chat_id):
    """Get list of users who rated a specific user"""
    async with db_operation():
        return [doc async for doc in posts.find({'chat_id': chat_id}, {'by': 1})]


async def get_profile(chat_id):
    """Get user profile with block check"""
    user = await get_document(chat_id)
    if user and user.get('block', 0) == 1:
        return None
    return user


async def check_counts():
    """Get sum of all counts (optimized to use aggregation)"""
    cache_key = "total_counts"
    cached_result = await _get_from_bulk_cache(cache_key)
    if cached_result:
        return cached_result
        
    async with db_operation():
        pipeline = [
            {'$group': {'_id': None, 'total': {'$sum': '$count'}}}
        ]
        result = await posts.aggregate(pipeline).to_list(length=1)
        total = result[0]['total'] if result else 0
        
        await _add_to_bulk_cache(cache_key, total)
        return total


async def sender():
    """Get all chat IDs (optimized with projection)"""
    cache_key = "all_chat_ids"
    cached_result = await _get_from_bulk_cache(cache_key)
    if cached_result:
        return cached_result
        
    async with db_operation():
        result = await posts.distinct("chat_id")
        await _add_to_bulk_cache(cache_key, result)
        return result


async def sort_collection_by_mark():
    """Get top 10 profiles by mark score"""
    cache_key = "top_by_mark"
    cached_result = await _get_from_bulk_cache(cache_key)
    if cached_result:
        return cached_result
        
    async with db_operation():
        query = {
            'count': {'$gte': 100},
            'active': {'$gte': 1},
            'block': {'$ne': 1}
        }
        pipeline = [
            {'$match': query},
            {'$sort': {'mark': -1}},
            {'$limit': 10},
            {'$project': {'chat_id': 1, 'name': 1, 'photo': 1, 'mark': 1, 'count': 1}}  # Project only needed fields
        ]
        result = [doc async for doc in posts.aggregate(pipeline)]
        await _add_to_bulk_cache(cache_key, result)
        return result


async def sort_collection_by_count():
    """Get top 10 profiles by rating count"""
    cache_key = "top_by_count"
    cached_result = await _get_from_bulk_cache(cache_key)
    if cached_result:
        return cached_result
        
    async with db_operation():
        query = {
            'count': {'$gte': 100},
            'active': {'$gte': 1},
            'block': {'$ne': 1}
        }
        pipeline = [
            {'$match': query},
            {'$sort': {'count': -1}},
            {'$limit': 10},
            {'$project': {'chat_id': 1, 'name': 1, 'photo': 1, 'mark': 1, 'count': 1}}  # Project only needed fields
        ]
        result = [doc async for doc in posts.aggregate(pipeline)]
        await _add_to_bulk_cache(cache_key, result)
        return result


async def update_mark(chat_id):
    """Update user's mark based on ratings received (optimized)"""
    async with db_operation():
        fb = await get_document(chat_id)
        if not fb:
            return 0.0
            
        marks = [int(i.get('mark', 0)) for i in fb.get('by', [])]
        likes = round(sum(marks) / len(marks), 2) if marks else 0.0
        await change_field(chat_id, 'mark', likes)
        return likes


async def add_new_field():
    """Add a new field to all documents"""
    async with db_operation():
        await posts.update_many({}, {"$set": {"city": 'не важно'}}, upsert=False)


async def delete_field():
    """Remove a field from all documents"""
    async with db_operation():
        await posts.update_many({}, {"$unset": {"city": 1}}, upsert=False)


async def toDecimal():
    """Convert mark field to float"""
    async with db_operation():
        async for doc in posts.find({}, {"mark": 1}):
            await posts.update_one({"_id": doc["_id"]}, {"$set": {"mark": float(doc["mark"])}})


async def delete_form(chat_id):
    """Delete a user profile"""
    async with db_operation():
        await posts.delete_one({'chat_id': chat_id})
        # Remove from cache if exists
        if chat_id in _document_cache:
            del _document_cache[chat_id]


async def exists():
    """Get all documents with active field"""
    async with db_operation():
        return [doc async for doc in posts.find({"active": {"$exists": True}}, {"chat_id": 1, "active": 1})]


async def check_users_for_bugs():
    """Check for invalid character bugs in user names"""
    async with db_operation():
        async for doc in posts.find({}, {"chat_id": 1, "name": 1}):
            check = await functions.simbols_exists(doc['name'])
            if check is True and not doc['name'].startswith('@'):
                logger.warning(f"User with invalid name: {doc['chat_id']}, {doc['name']}")


# Initialize database indexes when module is loaded
async def init_db():
    """Initialize database connection and ensure indexes"""
    try:
        await ensure_indexes()
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")

# Instead of creating a task immediately, provide a function to be called when the event loop is running
def setup_db():
    """Setup function to be called after event loop is running"""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(init_db())
    else:
        loop.run_until_complete(init_db())
