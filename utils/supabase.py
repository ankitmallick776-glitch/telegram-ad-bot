import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv
import random
from datetime import date, timedelta

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
            print("✅ Users table ready")
        except:
            print("⚠️ Table ready")
    
    async def get_user(self, user_id: int):
        response = self.client.table("users").select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else None
    
    async def create_user(self, user_id: int, username: str = ""):
        referral_code = f"REF_{user_id}_{random.randint(1000, 9999)}"
        self.client.table("users").upsert({
            "user_id": user_id,
            "username": username,
            "balance": 0.0,
            "referrals": 0,
            "referral_code": referral_code,
            "daily_bonus_date": None,
            "total_withdrawn": 0.00
        }).execute()
    
    async def get_balance(self, user_id: int) -> float:
        user = await self.get_user(user_id)
        return float(user["balance"]) if user else 0.0
    
    async def add_balance(self, user_id: int, amount: float) -> None:
        current = await self.get_balance(user_id)
        new_balance = current + amount
        self.client.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
        print(f"💰 User {user_id}: +{amount} = {new_balance}")
    
    async def give_daily_bonus(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        
        today = date.today()
        last_bonus = user.get("daily_bonus_date")
        
        if last_bonus and date.fromisoformat(last_bonus[:10]) >= today - timedelta(days=1):
            return False  # Already claimed today
        
        await self.add_balance(user_id, 5.0)
        self.client.table("users").update({"daily_bonus_date": str(today)}).eq("user_id", user_id).execute()
        return True
    
    async def get_referral_link(self, user_id: int) -> str:
        user = await self.get_user(user_id)
        if user:
            return f"https://t.me/{os.getenv('BOT_USERNAME', 'Cashyads2_bot')}?start=ref_{user['referral_code']}"
        return ""
    
    async def process_referral(self, user_id: int, referrer_code: str):
        referrer = self.client.table("users").select("user_id").eq("referral_code", referrer_code).execute()
        if referrer.data:
            referrer_id = referrer.data[0]["user_id"]
            if referrer_id != user_id:  # Not self-referral
                await self.add_balance(referrer_id, 40.0)  # Flat referral bonus
                self.client.table("users").update({"referrals": int(referrer.data[0]["referrals"]) + 1}).eq("user_id", referrer_id).execute()
                return True
        return False
    
    async def can_withdraw(self, user_id: int) -> dict:
        user = await self.get_user(user_id)
        if not user:
            return {"can": False, "reason": "User not found"}
        
        balance = float(user["balance"])
        referrals = user["referrals"] or 0
        
        if balance < 380:
            return {"can": False, "reason": f"Minimum 380 Rs. Current: {balance:.1f} Rs"}
        if referrals < 12:
            return {"can": False, "reason": f"Minimum 12 referrals. Current: {referrals}"}
        
        return {"can": True, "balance": balance, "referrals": referrals}

db = SupabaseDB()
