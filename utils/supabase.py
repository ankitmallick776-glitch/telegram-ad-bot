import os
import random
from datetime import date
from supabase import create_client
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class SupabaseDB:
    def __init__(self):
        self.client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    async def get_user(self, user_id):
        try:
            response = self.client.table('users').select('*').eq('user_id', user_id).execute()
            return response.data[0] if response.data else None
        except:
            return None
    
    async def create_user(self, user_id, username):
        for _ in range(5):
            ref_code = f"REF{random.randint(10000, 99999)}"
            try:
                data = {
                    'user_id': user_id,
                    'username': username,
                    'balance': 0.0,
                    'referrals': 0,
                    'referral_code': ref_code,
                    'daily_bonus_date': None
                }
                self.client.table('users').insert(data).execute()
                return True
            except:
                continue
        return False
    
    async def add_balance(self, user_id, amount):
        try:
            response = self.client.table('users').select('balance').eq('user_id', user_id).execute()
            if response.data:
                new_balance = response.data[0]['balance'] + amount
                self.client.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
                return new_balance
        except Exception as e:
            logger.error(f"Balance error: {e}")
        return 0.0
    
    async def process_referral(self, user_id, ref_code):
        try:
            referrer = self.client.table('users').select('user_id').eq('referral_code', ref_code).execute()
            if referrer.data:
                referrer_id = referrer.data[0]['user_id']
                
                user = self.client.table('users').select('referrer_id').eq('user_id', user_id).execute()
                if not user.data or not user.data[0].get('referrer_id'):
                    await self.add_balance(user_id, 40.0)
                    
                    ref_data = self.client.table('users').select('referrals').eq('user_id', referrer_id).execute()
                    new_refs = (ref_data.data[0]['referrals'] + 1) if ref_data.data else 1
                    self.client.table('users').update({'referrals': new_refs}).eq('user_id', referrer_id).execute()
                    
                    self.client.table('users').update({'referrer_id': referrer_id}).eq('user_id', user_id).execute()
        except Exception as e:
            logger.error(f"Referral error: {e}")
    
    async def claim_daily_bonus(self, user_id):
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            today = date.today().isoformat()
            if user.get('daily_bonus_date') != today:
                await self.add_balance(user_id, 5.0)
                self.client.table('users').update({'daily_bonus_date': today}).eq('user_id', user_id).execute()
                return True
        except Exception as e:
            logger.error(f"Bonus error: {e}")
        return False
    
    async def process_withdrawal(self, user_id, method):
        try:
            self.client.table('users').update({'balance': 0.0}).eq('user_id', user_id).execute()
        except Exception as e:
            logger.error(f"Withdrawal error: {e}")
    
    async def get_leaderboard(self, limit: int = 5):
        try:
            response = self.client.table('users').select('user_id, username, balance').order('balance', desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            return []

db = SupabaseDB()
