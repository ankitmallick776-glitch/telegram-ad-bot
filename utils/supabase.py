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
        """Create users table if not exists"""
        response = self.client.table("users").select("*").limit(0).execute()
        if not response.data:
            # Table doesn't exist, create it
            self.client.table("users").insert({
                "user_id": 0,
                "balance": 0.0
            }).execute()  # This creates the table
    
    async def get_balance(self, user_id: int) -> float:
        """Get user balance"""
        response = self.client.table("users").select("balance").eq("user_id", user_id).execute()
        if response.data:
            return float(response.data[0]["balance"])
        return 0.0
    
    async def add_balance(self, user_id: int, amount: float) -> None:
        """Add amount to user balance (upsert)"""
        # First get current balance
        current_balance = await self.get_balance(user_id)
        new_balance = current_balance + amount
        
        # Upsert user balance
        self.client.table("users").upsert({
            "user_id": user_id,
            "balance": new_balance
        }).execute()

# Global instance
db = SupabaseDB()
