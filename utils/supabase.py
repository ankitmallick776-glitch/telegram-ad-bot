import os
import asyncio
import random
from datetime import date
from supabase import create_client, Client
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
        """Get user or None"""
        try:
            response = self.client.table('users').select('*').eq('user_id', user_id).execute()
            return response.data[0] if response.data else None
        except:
            return None
    
    async def create_user(self, user_id, username):
        """Create new user with unique referral code"""
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
                logger.info(f"✅ Created user {user_id} with code {ref_code}")
                return True
            except:
                continue
        logger.error(f"❌ Failed to create unique code for {user_id}")
        return False
    
    async def add_balance(self, user_id, amount):
        """Add balance atomically"""
        try:
            # Get current balance
            response = self.client.table('users').select('balance').eq('user_id', user_id).execute()
            if response.data:
                new_balance = response.data[0]['balance'] + amount
                self.client.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
                logger.info(f"💰 Added ₹{amount:.2f} to {user_id}. New: ₹{new_balance:.2f}")
                return new_balance
        except Exception as e:
            logger.error(f"Balance error: {e}")
        return 0.0
    
    async def process_referral(self, user_id, ref_code):
        """Process referral - only if not already processed"""
        try:
            referrer = self.client.table('users').select('user_id').eq('referral_code', ref_code).execute()
            if referrer.data:
                referrer_id = referrer.data[0]['user_id']
                
                # Check if already linked
                user = self.client.table('users').select('referrer_id').eq('user_id', user_id).execute()
                if not user.data or not user.data[0].get('referrer_id'):
                    
                    # Give 40rs to new user
                    await self.add_balance(user_id, 40.0)
                    
                    # Increment referrer referrals +1
                    referrer_data = self.client.table('users').select('referrals').eq('user_id', referrer_id).execute()
                    new_refs = (referrer_data.data[0]['referrals'] + 1) if referrer_data.data else 1
                    self.client.table('users').update({'referrals': new_refs}).eq('user_id', referrer_id).execute()
                    
                    # Link referrer
                    self.client.table('users').update({'referrer_id': referrer_id}).eq('user_id', user_id).execute()
                    
                    logger.info(f"✅ Referral: {user_id} <- {referrer_id}")
        except Exception as e:
            logger.error(f"Referral error: {e}")
    
    async def claim_daily_bonus(self, user_id):
        """Claim 5rs daily bonus"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            today = date.today().isoformat()
            if user.get('daily_bonus_date') != today:
                await self.add_balance(user_id, 5.0)
                self.client.table('users').update({'daily_bonus_date': today}).eq('user_id', user_id).execute()
                logger.info(f"🎁 Daily bonus claimed by {user_id}")
                return True
        except Exception as e:
            logger.error(f"Bonus error: {e}")
        return False
    
    async def process_withdrawal(self, user_id, method):
        """Reset balance to 0 after withdrawal"""
        try:
            self.client.table('users').update({'balance': 0.0}).eq('user_id', user_id).execute()
            logger.info(f"💸 Withdrawal processed for {user_id}")
        except Exception as e:
            logger.error(f"Withdrawal error: {e}")
    
    async def notify_admin(self, user_id, method, amount):
        """Log withdrawal for admin review"""
        try:
            user = await self.get_user(user_id)
            message = f"💸 **WITHDRAWAL REQUEST**\n👤 {user['username']} (ID: {user_id})\n💰 ₹{amount:.1f} via {method}"
            logger.info(message)
            print(message)  # Replace with Telegram admin notification
        except Exception as e:
            logger.error(f"Admin notify error: {e}")
    
    async def get_leaderboard(self, limit: int = 5):
        """Get top 5 richest users"""
        try:
            response = self.client.table('users').select('user_id, username, balance').order('balance', desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            return []

db = SupabaseDB()
