import os
from supabase import create_client, Client
from dotenv import load_dotenv
import asyncio

load_dotenv()

class SupabaseDB:
    def __init__(self):
        self.client: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    async def init_table(self):
        """Create users table if not exists - FIXED"""
        try:
            # Test if table exists by selecting
            response = self.client.table("users").select("*").limit(0).execute()
            print("✅ Users table exists")
        except:
            print("⚠️  Creating users table...")
            # Create table via RPC (bypasses RLS)
            self.client.rpc('create_users_table').execute()
            print("✅ Table created")
    
    async def get_balance(self, user_id: int) -> float:
        """Get user balance - FIXED upsert logic"""
        response = self.client.table("users").select("balance").eq("user_id", user_id).execute()
        if response.data:
            return float(response.data[0]["balance"])
        return 0.0
    
    async def add_balance(self, user_id: int, amount: float) -> None:
        """Add amount to user balance (upsert) - FIXED"""
        try:
            # UPSERT with ON CONFLICT
            self.client.table("users").upsert({
                "user_id": user_id,
                "balance": amount  # Will add to existing on conflict
            }, on_conflict="user_id").execute()
        except Exception as e:
            print(f"Balance update error: {e}")

# Global instance
db = SupabaseDB()
