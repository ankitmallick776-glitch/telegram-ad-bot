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
        """Create users table if not exists"""
        try:
            response = self.client.table('users').select('*').limit(0).execute()
        except:
            # Create table
            self.client.rpc('create_users_table').execute()
        
        # Ensure required columns
        columns = """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS balance DECIMAL(10,2) DEFAULT 0.00,
        ADD COLUMN IF NOT EXISTS referrals INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS referral_code TEXT UNIQUE,
        ADD COLUMN IF NOT EXISTS referrer_id BIGINT,
        ADD COLUMN IF NOT EXISTS daily_bonus_date TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS total_withdrawn DECIMAL(10,2) DEFAULT 0.00;
        """
        self.client.rpc('execute_sql', {'sql': columns}).execute()
        
        logger.info("✅ Database initialized")
    
    async def get_user(self, user_id):
        """Get user or None"""
        response = self.client.table('users').select('*').eq('user_id', user_id).execute()
        return response.data[0] if response.data else None
    
    async def create_user(self, user_id, username):
        """Create new user with unique referral code"""
        ref_code = f"REF{random.randint(10000, 99999)}"
        
        data = {
            'user_id': user_id,
            'username': username,
            'balance': 0.0,
            'referrals': 0,
            'referral_code': ref_code,
            'daily_bonus_date': None
        }
        
        self.client.table('users').insert(data).execute()
    
    async def add_balance(self, user_id, amount):
        """Add balance and return new balance"""
        response = self.client.table('users').select('balance').eq('user_id', user_id).execute()
        if response.data:
            new_balance = response.data[0]['balance'] + amount
            self.client.table('users').update({'balance': new_balance}).eq('user_id', user_id).execute()
            return new_balance
        return 0.0
    
    async def process_referral(self, user_id, ref_code):
        """Process referral - 40rs + link referrer"""
        referrer = self.client.table('users').select('user_id').eq('referral_code', ref_code).execute()
        if referrer.data:
            referrer_id = referrer.data[0]['user_id']
            
            # Add 40rs to new user
            await self.add_balance(user_id, 40.0)
            
            # Increment referrer count
            self.client.table('users').update({'referrals': 1}).eq('user_id', referrer_id).execute()
            
            # Link referrer
            self.client.table('users').update({'referrer_id': referrer_id}).eq('user_id', user_id).execute()
    
    async def claim_daily_bonus(self, user_id):
        """Claim 5rs daily bonus"""
        user = await self.get_user(user_id)
        today = date.today()
        
        if user['daily_bonus_date'] != today.isoformat():
            await self.add_balance(user_id, 5.0)
            self.client.table('users').update({'daily_bonus_date': today.isoformat()}).eq('user_id', user_id).execute()
            return True
        return False
    
    async def process_withdrawal(self, user_id, method):
        """Process withdrawal - set balance to 0"""
        self.client.table('users').update({'balance': 0.0}).eq('user_id', user_id).execute()
    
    async def notify_admin(self, user_id, method, amount):
        """Notify admin of withdrawal"""
        admin_id = 123456789  # YOUR TELEGRAM ID
        user = await self.get_user(user_id)
        
        message = f"💸 **WITHDRAWAL REQUEST**\n\n"
        message += f"👤 User: {user['username']} (ID: {user_id})\n"
        message += f"💰 Amount: ₹{amount}\n"
        message += f"📱 Method: {method}"
        
        # Send to admin bot (implement as needed)
        print(message)  # Replace with actual admin notification
    
    async def get_leaderboard(self, limit: int = 5):
        """Get top users by balance"""
        try:
            response = self.client.table('users').select('user_id, username, balance').order('balance', desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Leaderboard error: {e}")
            return []

db = SupabaseDB()
