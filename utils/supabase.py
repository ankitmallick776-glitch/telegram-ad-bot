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
        try:
            self.client.table("users").select("*").limit(0).execute()
            print("✅ Users table exists")
        except:
            print("⚠️ Table check failed - assuming exists")
    
    async def get_balance(self, user_id: int) -> float:
        """Get current balance"""
        try:
            response = self.client.table("users").select("balance").eq("user_id", user_id).execute()
            return float(response.data[0]["balance"]) if response.data else 0.0
        except:
            return 0.0
    
    async def add_balance(self, user_id: int, amount: float) -> None:
        """FIXED: Proper increment (not overwrite)"""
        try:
            # Get current balance first
            current_balance = await self.get_balance(user_id)
            new_balance = current_balance + amount
            
            # Upsert with NEW total
            self.client.table("users").upsert({
                "user_id": user_id,
                "balance": new_balance
            }, on_conflict="user_id").execute()
            print(f"💰 Added {amount} to user {user_id}. New balance: {new_balance}")
        except Exception as e:
            print(f"❌ Balance error: {e}")

db = SupabaseDB()
