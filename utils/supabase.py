import os
import random
from datetime import date, timedelta, datetime
from supabase import create_client
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

    # USER MANAGEMENT
    async def get_user(self, user_id: int):
        try:
            response = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except:
            return None

    async def get_referrer_by_code(self, referral_code: str):
        try:
            response = self.client.table("users").select("*").eq("referral_code", referral_code).execute()
            return response.data[0] if response.data else None
        except:
            return None

    async def user_already_referred(self, user_id: int) -> bool:
        try:
            response = self.client.table("referral_history").select("id").eq("new_user_id", user_id).execute()
            return len(response.data) > 0
        except:
            return False

    async def create_user_if_not_exists(self, user_id: int, username: str = ""):
        user = await self.get_user(user_id)
        if user:
            return

        user_data = {
            "user_id": user_id,
            "balance": 0.0,
            "referrals": 0,
            "last_task_completion": None
        }

        if username:
            user_data["username"] = username

        referral_code = f"REF_{user_id}_{random.randint(1000, 9999)}"
        user_data["referral_code"] = referral_code

        try:
            self.client.table("users").insert(user_data).execute()
            print(f"👤 User {user_id} created")
        except Exception as e:
            print(f"⚠️ Create error: {e}")

    # BALANCE
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

    # DAILY BONUS
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

    # REFERRAL SYSTEM
    async def process_referral(self, user_id: int, referrer_code: str):
        if await self.user_already_referred(user_id):
            print(f"❌ User {user_id} already referred!")
            return False

        try:
            referrer = await self.get_referrer_by_code(referrer_code)
            if not referrer:
                return False
            
            referrer_id = referrer["user_id"]
            
            await self.create_user_if_not_exists(user_id)
            await self.create_user_if_not_exists(referrer_id)
            
            if referrer_id != user_id:
                await self.add_balance(referrer_id, 40.0)
                current_refs = int(referrer.get("referrals", 0))
                
                try:
                    self.client.table("users").update({
                        "referrals": current_refs + 1
                    }).eq("user_id", referrer_id).execute()
                except:
                    pass
                
                try:
                    self.client.table("referral_history").insert({
                        "new_user_id": user_id,
                        "referrer_id": referrer_id,
                        "referral_code": referrer_code,
                        "created_at": date.today().isoformat()
                    }).execute()
                except:
                    pass
                
                print(f"✅ Referral: {user_id} → {referrer_id}")
                return True
        except Exception as e:
            print(f"❌ Referral error: {e}")
        
        return False

    async def add_referral_commission(self, new_user_id: int, reward: float) -> None:
        try:
            response = self.client.table("referral_history").select("referrer_id").eq("new_user_id", new_user_id).execute()
            if response.data:
                referrer_id = response.data[0]["referrer_id"]
                commission = reward * 0.05
                await self.add_balance(referrer_id, commission)
                print(f"🤝 Commission: {referrer_id} +{commission:.2f}")
        except:
            pass

    # WITHDRAWAL
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

    # ADMIN FUNCTIONS
    async def get_active_users(self) -> list:
        try:
            all_users = []
            batch_size = 500
            offset = 0
            thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
            
            while True:
                response = self.client.table("users").select("user_id").gte("created_at", thirty_days_ago).range(offset, offset + batch_size - 1).execute()
                if not response.data:
                    break
                all_users.extend([user["user_id"] for user in response.data])
                offset += batch_size
            
            print(f"✅ Active users: {len(all_users)}")
            return all_users
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

    async def get_all_user_ids(self) -> list:
        try:
            all_users = []
            batch_size = 500
            offset = 0
            
            while True:
                response = self.client.table("users").select("user_id").range(offset, offset + batch_size - 1).execute()
                if not response.data:
                    break
                all_users.extend([user["user_id"] for user in response.data])
                offset += batch_size
            
            print(f"✅ Total users: {len(all_users)}")
            return all_users
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

    async def delete_user(self, user_id: int) -> bool:
        try:
            self.client.table("users").delete().eq("user_id", user_id).execute()
            self.client.table("referral_history").delete().eq("new_user_id", user_id).execute()
            self.client.table("referral_history").delete().eq("referrer_id", user_id).execute()
            print(f"🧹 User {user_id} deleted")
            return True
        except:
            return False

    async def get_global_stats(self) -> dict:
        try:
            all_users = []
            batch_size = 500
            offset = 0
            total_balance = 0.0
            
            while True:
                response = self.client.table("users").select("balance").range(offset, offset + batch_size - 1).execute()
                if not response.data:
                    break
                all_users.extend(response.data)
                total_balance += sum(float(user["balance"]) for user in response.data)
                offset += batch_size
            
            total_users = len(all_users)
            return {"total_users": total_users, "total_balance": total_balance}
        except:
            return {"total_users": 0, "total_balance": 0.0}

    async def get_user_stats(self, user_id: int) -> dict:
        try:
            user = await self.get_user(user_id)
            if not user:
                return {"total_earned": 0.0, "referrals": 0}
            
            balance = float(user.get("balance", 0))
            referrals = int(user.get("referrals", 0))
            
            return {"total_earned": balance, "referrals": referrals}
        except:
            return {"total_earned": 0.0, "referrals": 0}

    # TASKS
    async def get_user_task_time(self, user_id: int):
        user = await self.get_user(user_id)
        if user:
            return user.get("last_task_completion")
        return None

    async def set_task_completion(self, user_id: int):
        try:
            self.client.table("users").update({
                "last_task_completion": datetime.now().isoformat()
            }).eq("user_id", user_id).execute()
        except Exception as e:
            print(f"⚠️ Task time error: {e}")

    # STATS
    async def get_total_user_count(self) -> int:
        try:
            response = self.client.table("bot_stats").select("total_users").eq("id", 1).execute()
            if response.data:
                return int(response.data[0]["total_users"])
            return 0
        except:
            return 0

db = SupabaseDB()
