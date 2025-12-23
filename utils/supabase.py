import os
import asyncio
import random
from datetime import date, timedelta, datetime
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

    # ============================================
    # USER MANAGEMENT
    # ============================================

    async def get_user(self, user_id: int):
        """Get user by user_id"""
        try:
            response = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except:
            return None

    async def get_referrer_by_code(self, referral_code: str):
        """Get referrer user by referral code"""
        try:
            response = self.client.table("users").select("*").eq("referral_code", referral_code).execute()
            return response.data[0] if response.data else None
        except:
            return None

    async def user_already_referred(self, user_id: int) -> bool:
        """Check if user already has a referrer"""
        try:
            response = self.client.table("referral_history").select("id").eq("new_user_id", user_id).execute()
            return len(response.data) > 0
        except:
            return False

    async def create_user_if_not_exists(self, user_id: int, username: str = ""):
        """Create new user if not exists"""
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

    # ============================================
    # BALANCE OPERATIONS
    # ============================================

    async def get_balance(self, user_id: int) -> float:
        """Get user balance"""
        user = await self.get_user(user_id)
        return float(user["balance"]) if user and "balance" in user else 0.0

    async def add_balance(self, user_id: int, amount: float) -> None:
        """Add amount to user balance"""
        current = await self.get_balance(user_id)
        new_balance = current + amount
        try:
            self.client.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
            print(f"💰 User {user_id}: +{amount} = {new_balance}")
        except Exception as e:
            print(f"❌ Balance error: {e}")

    # ============================================
    # DAILY BONUS
    # ============================================

    async def give_daily_bonus(self, user_id: int) -> bool:
        """Give 5 Rs daily bonus (once per day)"""
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

    # ============================================
    # REFERRAL SYSTEM
    # ============================================

    async def process_referral(self, user_id: int, referrer_code: str):
        """Process referral - INSTANT 40 Rs reward"""
        if await self.user_already_referred(user_id):
            print(f"❌ EXPLOIT BLOCKED: User {user_id} already has a referrer!")
            return False

        try:
            referrer = await self.get_referrer_by_code(referrer_code)
            if referrer and referrer["user_id"] != user_id:
                referrer_id = referrer["user_id"]
                
                # Give instant 40 Rs bonus
                await self.add_balance(referrer_id, 40.0)
                current_refs = int(referrer.get("referrals", 0))
                self.client.table("users").update({"referrals": current_refs + 1}).eq("user_id", referrer_id).execute()
                
                # Store referral history
                try:
                    self.client.table("referral_history").insert({
                        "new_user_id": user_id,
                        "referrer_id": referrer_id,
                        "referral_code": referrer_code,
                        "created_at": date.today().isoformat()
                    }).execute()
                    print(f"📊 Referral history stored: {user_id} → {referrer_id}")
                except Exception as e:
                    print(f"⚠️ History error: {e}")
                
                print(f"✅ REFERRAL: {user_id} → {referrer_id} (+40 Rs INSTANT)")
                return True
        except Exception as e:
            print(f"❌ Referral error: {e}")
        return False

    async def add_referral_commission(self, new_user_id: int, reward: float) -> None:
        """Add 5% commission to referrer from user's ad earnings"""
        try:
            response = self.client.table("referral_history").select("referrer_id").eq("new_user_id", new_user_id).execute()
            if response.data:
                referrer_id = response.data[0]["referrer_id"]
                commission = reward * 0.05
                await self.add_balance(referrer_id, commission)
                print(f"🤝 COMMISSION: {new_user_id} earned {reward} → {referrer_id} gets {commission:.2f} Rs")
        except Exception as e:
            print(f"⚠️ Commission error: {e}")

    # ============================================
    # WITHDRAWAL
    # ============================================

    async def can_withdraw(self, user_id: int) -> dict:
        """Check if user can withdraw"""
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

    # ============================================
    # USER MANAGEMENT (ADMIN)
    # ============================================

    async def get_active_users(self) -> list:
        """Get users active in last 30 days"""
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
        """Get all user IDs"""
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
        """Delete user (total_users count stays same for trust)"""
        try:
            self.client.table("users").delete().eq("user_id", user_id).execute()
            self.client.table("referral_history").delete().eq("new_user_id", user_id).execute()
            self.client.table("referral_history").delete().eq("referrer_id", user_id).execute()
            print(f"🧹 DELETED user {user_id} (total_users count unchanged)")
            return True
        except:
            return False

    async def get_global_stats(self) -> dict:
        """Get global bot stats"""
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
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"total_users": 0, "total_balance": 0.0}

    async def get_user_stats(self, user_id: int) -> dict:
        """Get user stats"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return {"total_earned": 0.0, "referrals": 0}
            
            balance = float(user.get("balance", 0))
            referrals = int(user.get("referrals", 0))
            
            return {
                "total_earned": balance,
                "referrals": referrals
            }
        except:
            return {"total_earned": 0.0, "referrals": 0}

    # ============================================
    # BOT STATS (TOTAL USERS)
    # ============================================

    async def get_total_user_count(self) -> int:
        """Get total user count from stats table - INSTANT"""
        try:
            response = self.client.table("bot_stats").select("total_users").eq("id", 1).execute()
            if response.data:
                return int(response.data[0]["total_users"])
            return 0
        except Exception as e:
            print(f"⚠️ Stats error: {e}")
            return 0

    # ============================================
    # DAILY TASKS
    # ============================================

    async def get_user_daily_tasks(self, user_id: int) -> dict:
        """Get user's daily task progress"""
        try:
            today = date.today().isoformat()
            response = self.client.table("daily_tasks").select("*").eq("user_id", user_id).eq("task_date", today).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"⚠️ Task error: {e}")
            return None

    async def create_or_update_daily_task(self, user_id: int, tasks_completed: int = 0, pending_reward: float = 0):
        """Create or update user's daily task progress"""
        try:
            today = date.today().isoformat()
            
            # Check if exists
            existing = await self.get_user_daily_tasks(user_id)
            
            if existing:
                # Update
                self.client.table("daily_tasks").update({
                    "tasks_completed": tasks_completed,
                    "pending_reward": pending_reward,
                    "last_task_time": datetime.now().isoformat()
                }).eq("user_id", user_id).eq("task_date", today).execute()
                print(f"📋 Updated tasks for {user_id}: {tasks_completed}/4 complete, {pending_reward} Rs pending")
            else:
                # Create
                self.client.table("daily_tasks").insert({
                    "user_id": user_id,
                    "task_date": today,
                    "tasks_completed": tasks_completed,
                    "pending_reward": pending_reward,
                    "last_task_time": datetime.now().isoformat()
                }).execute()
                print(f"📋 Created tasks for {user_id}")
        except Exception as e:
            print(f"❌ Task update error: {e}")

    async def check_task_code(self, code: str, user_id: int) -> dict:
        """Verify task code - per-user one-time use"""
        try:
            today = date.today().isoformat()
            response = self.client.table("daily_task_codes").select("*").eq("secret_code", code).eq("created_date", today).execute()
            
            if not response.data:
                return {"valid": False, "reason": "Code not found"}
            
            code_data = response.data[0]
            code_id = code_data["id"]
            
            # Check if THIS USER already used THIS CODE
            usage_response = self.client.table("task_code_usage").select("id").eq("code_id", code_id).eq("user_id", user_id).execute()
            
            if usage_response.data:
                return {"valid": False, "reason": "You already used this code"}
            
            return {
                "valid": True,
                "task_number": code_data["task_number"],
                "code_id": code_id
            }
        except Exception as e:
            print(f"⚠️ Code check error: {e}")
            return {"valid": False, "reason": "Error checking code"}

    async def mark_code_used(self, code_id: int, user_id: int):
        """Mark code as used by this specific user"""
        try:
            self.client.table("task_code_usage").insert({
                "code_id": code_id,
                "user_id": user_id,
                "used_date": datetime.now().isoformat()
            }).execute()
            print(f"✅ Code {code_id} marked used by user {user_id}")
        except Exception as e:
            print(f"⚠️ Mark code error: {e}")

    async def generate_daily_codes(self):
        """Generate 3 daily codes for admin (call once per day)"""
        try:
            import string
            import random
            
            today = date.today().isoformat()
            
            # Check if already generated
            response = self.client.table("daily_task_codes").select("id").eq("created_date", today).execute()
            if response.data and len(response.data) >= 3:
                print("✅ Codes already generated for today")
                return
            
            # Delete old codes (older than today)
            self.client.table("daily_task_codes").delete().lt("created_date", today).execute()
            
            # Generate 3 unique codes
            codes = []
            for task_num in range(1, 4):
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                codes.append({"task_number": task_num, "secret_code": code, "created_date": today})
            
            # Insert codes
            self.client.table("daily_task_codes").insert(codes).execute()
            print(f"📋 Generated 3 daily codes: {[c['secret_code'] for c in codes]}")
            
            return codes
        except Exception as e:
            print(f"❌ Code generation error: {e}")
            return []

    async def get_daily_codes(self) -> list:
        """Get today's codes for admin"""
        try:
            today = date.today().isoformat()
            response = self.client.table("daily_task_codes").select("*").eq("created_date", today).order("task_number").execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Get codes error: {e}")
            return []

# Initialize database
db = SupabaseDB()
