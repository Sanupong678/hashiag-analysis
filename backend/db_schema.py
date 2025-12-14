"""
Database Schema Definitions
Collections and their expected structure
"""

# Alerts Collection Schema
ALERTS_SCHEMA = {
    "type": "object",
    "properties": {
        "_id": "ObjectId",
        "type": "string",  # sentiment_spike, mentions_spike, influencer_post, price_divergence, keyword
        "tickers": "array",  # List of ticker symbols
        "threshold": "number",  # For sentiment_spike
        "multiplier": "number",  # For mentions_spike
        "influencer": "string",  # For influencer_post
        "keyword": "string",  # For keyword alerts
        "sensitivity": "string",  # low, medium, high
        "deliveryMethods": "array",  # in-app, telegram, line, email
        "throttle": {
            "count": "number",
            "minutes": "number"
        },
        "escalation": {
            "enabled": "boolean",
            "interval": "number"  # minutes
        },
        "enabled": "boolean",
        "acknowledged": "boolean",
        "createdAt": "datetime",
        "acknowledgedAt": "datetime"
    }
}

# Watchlist Collection Schema
WATCHLIST_SCHEMA = {
    "type": "object",
    "properties": {
        "_id": "ObjectId",
        "userId": "string",  # In production, would use actual user ID
        "tickers": "array",  # List of ticker symbols
        "createdAt": "datetime",
        "updatedAt": "datetime"
    }
}

# Influencers Collection Schema
INFLUENCERS_SCHEMA = {
    "type": "object",
    "properties": {
        "_id": "ObjectId",
        "name": "string",
        "handle": "string",
        "platform": "string",  # twitter, reddit, youtube
        "verified": "boolean",
        "followed": "boolean",
        "detected": "boolean",  # Auto-detected by system
        "suggested": "boolean",  # Suggested to user
        "posts": "number",
        "avgSentiment": "number",
        "avgImpact": "number",  # Average price impact percentage
        "reliability": "number",  # 0-1 score
        "createdAt": "datetime",
        "updatedAt": "datetime"
    }
}

# Topics Collection Schema (for LDA topic clustering)
TOPICS_SCHEMA = {
    "type": "object",
    "properties": {
        "_id": "ObjectId",
        "ticker": "string",
        "topicId": "number",
        "name": "string",
        "weight": "number",  # 0-1
        "posts": "array",  # Post IDs
        "keywords": "array",  # Top keywords for this topic
        "createdAt": "datetime"
    }
}

# Settings Collection Schema
SETTINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "_id": "ObjectId",
        "userId": "string",
        "theme": "string",  # dark, light
        "timezone": "string",
        "defaultTimeRange": "string",
        "apiKeys": {
            "newsApi": "string",
            "twitterToken": "string"
        },
        "notifications": {
            "telegramToken": "string",
            "lineToken": "string",
            "email": "string"
        },
        "updatedAt": "datetime"
    }
}

# Initialize Collections
def initialize_collections(db):
    """Create collections with indexes if they don't exist"""
    try:
        # Alerts collection
        if "alerts" not in db.list_collection_names():
            db.create_collection("alerts")
            db.alerts.create_index("tickers")
            db.alerts.create_index("createdAt")
            db.alerts.create_index("enabled")
        
        # Watchlist collection
        if "watchlist" not in db.list_collection_names():
            db.create_collection("watchlist")
            db.watchlist.create_index("userId")
        
        # Influencers collection
        if "influencers" not in db.list_collection_names():
            db.create_collection("influencers")
            db.influencers.create_index("handle")
            db.influencers.create_index("followed")
        
        # Topics collection
        if "topics" not in db.list_collection_names():
            db.create_collection("topics")
            db.topics.create_index([("ticker", 1), ("topicId", 1)])
        
        # Settings collection
        if "settings" not in db.list_collection_names():
            db.create_collection("settings")
            db.settings.create_index("userId")
        
        print("✅ Database collections initialized")
    except Exception as e:
        print(f"⚠️ Error initializing collections: {e}")

