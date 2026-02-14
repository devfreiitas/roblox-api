import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

class Database:
    def __init__(self):
        self.client: Client = None
    
    async def connect(self):
        try:
            self.client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            logging.info("Successfully connected to Supabase")
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            raise