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
            print("✅ Full table ready")
        except:
            print("⚠️ Table ready")
    
    async def get_user(self, user_id: int):
        try:
            response = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except:
            return None
    
    async def create_user(self, user_id: int, username: str = ""):
        """Safe create - handles missing columns"""
        user_data = {
            "user_id": user_id,
            "balance": 0.0,
            "referrals": 0
        }
        
        # Safe optional fields
        if username:
            user_data["username"] = username
            
        referral_code = f"REF_{user_id}_{random.randint(1000, 9999)}"
        user_data["referral_code"] = referral_code
        
        try:
            self.client.table("users").upsert(user_data).execute()
            print(f"👤 Created user {user_id}")
        except Exception as e:
            print(f"⚠️ User create warning: {e}")
    
    async def get_balance(self, user_id: int) -> float:
        user = await self.get_user(user_id)
        return float(user["balance"]) if user and "balance" in user else 0.0
    
    async def add_balance(self, user_id: int, amount: float) -> None:
        current = await self.get_balance(user_id)
        new_balance = current + amount
        
        try:
            self.client.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
            print(f"💰 User {user_id}: +{amount} = {new_balance}")
        except Exception as e:
            print(f"❌ Balance error: {e}")
    
    async def give_daily_bonus(self, user_id: int) -> bool:
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            today = date.today().isoformat()
            
            # Safe date check
            last_bonus = user.get("daily_bonus_date")
            if last_bonus and last_bonus[:10] == today:
                return False
            
            await self.add_balance(user_id, 5.0)
            
            # Safe date update
            self.client.table("users").update({"daily_bonus_date": today}).eq("user_id", user_id).execute()
            return True
        except:
            return False
    
    async def get_referral_link(self, user_id: int) -> str:
        bot_username = os.getenv("BOT_USERNAME", "Cashyads2_bot")
        return f"https://t.me/{bot_username}?start=ref_REF_{user_id}"
    
    async def process_referral(self, user_id: int, referrer_code: str):
        try:
            referrer = self.client.table("users").select("user_id").eq("referral_code", referrer_code).execute()
            if referrer.data and referrer.data[0]["user_id"] != user_id:
                referrer_id = referrer.data[0]["user_id"]
                await self.add_balance(referrer_id, 40.0)
                return True
        except:
            pass
        return False
    
    async def can_withdraw(self, user_id: int) -> dict:
        user = await self.get_user(user_id)
        if not user:
            return {"can": False, "reason": "User not found"}
        
        balance = float(user.get("balance", 0))
        referrals = int(user.get("referrals", 0))
        
        if balance < 380:
            return {"can": False, "reason": f"Min 380 Rs. Current: {balance:.1f}"}
        if referrals < 12:
            return {"can": False, "reason": f"Min 12 referrals. Current: {referrals}"}
        
        return {"can": True, "balance": balance, "referrals": referrals}

db = SupabaseDB()
