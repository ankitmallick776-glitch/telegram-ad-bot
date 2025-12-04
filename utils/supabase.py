import os
import asyncio
import random
from datetime import date, timedelta
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
            print("✅ Users table ready")
        except:
            print("⚠️ Table ready")
    
    async def get_user(self, user_id: int):
        try:
            response = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except:
            return None
    
    async def get_referrer_by_code(self, referral_code: str):
        """Get referrer info by referral code"""
        try:
            response = self.client.table("users").select("*").eq("referral_code", referral_code).execute()
            return response.data[0] if response.data else None
        except:
            return None
    
    async def create_user_if_not_exists(self, user_id: int, username: str = ""):
        user = await self.get_user(user_id)
        if user:
            print(f"👤 User {user_id} already exists - SKIPPING")
            return
        
        user_data = {
            "user_id": user_id,
            "balance": 0.0,
            "referrals": 0
        }
        
        if username:
            user_data["username"] = username
            
        referral_code = f"REF_{user_id}_{random.randint(1000, 9999)}"
        user_data["referral_code"] = referral_code
        
        try:
            self.client.table("users").insert(user_data).execute()
            print(f"👤 CREATED new user {user_id} with code {referral_code}")
        except Exception as e:
            print(f"⚠️ Create error: {e}")
    
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
            last_bonus = user.get("daily_bonus_date", "")
            
            if last_bonus and last_bonus[:10] == today:
                return False
            
            await self.add_balance(user_id, 5.0)
            self.client.table("users").update({"daily_bonus_date": today}).eq("user_id", user_id).execute()
            return True
        except:
            return False
    
    async def process_referral(self, user_id: int, referrer_code: str):
        """Process when new user joins via referral link"""
        try:
            referrer = await self.get_referrer_by_code(referrer_code)
            if referrer and referrer["user_id"] != user_id:
                referrer_id = referrer["user_id"]
                
                # Give 40 Rs bonus to referrer
                await self.add_balance(referrer_id, 40.0)
                
                # Increment referral count
                current_refs = int(referrer.get("referrals", 0))
                self.client.table("users").update({"referrals": current_refs + 1}).eq("user_id", referrer_id).execute()
                
                print(f"✅ REFERRAL: {user_id} joined via {referrer_id} → +40 Rs")
                return True
        except Exception as e:
            print(f"❌ Referral error: {e}")
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
