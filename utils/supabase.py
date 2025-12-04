import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseDB:
    def __init__(self):
        self.client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    async def init_table(self):
        try:
            self.client.table("users").select("*").limit(0).execute()
            print("✅ Users table exists")
        except:
            print("⚠️ Table ready")
    
    async def get_balance(self, user_id: int) -> float:
        try:
            response = self.client.table("users").select("balance").eq("user_id", user_id).execute()
            return float(response.data[0]["balance"]) if response.data else 0.0
        except:
            return 0.0
    
    async def add_balance(self, user_id: int, amount: float) -> None:
        try:
            current = await self.get_balance(user_id)
            new_balance = current + amount
            self.client.table("users").upsert({
                "user_id": user_id,
                "balance": new_balance
            }).execute()
            print(f"💰 User {user_id}: +{amount} Rs = {new_balance} Rs")
        except Exception as e:
            print(f"❌ DB Error: {e}")

db = SupabaseDB()
