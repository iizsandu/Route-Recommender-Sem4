"""
NewsData.io Credit Manager
Tracks API credits and enforces 24-hour reset cycle
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional


class CreditManager:
    def __init__(self, credits_file: str = "newsdata_credits.json"):
        self.credits_file = credits_file
        self.max_credits = 200
        self.reset_hours = 24
    
    def _load_credits(self) -> Dict:
        """Load credit data from file"""
        if not os.path.exists(self.credits_file):
            return self._create_new_credits()
        
        try:
            with open(self.credits_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"⚠ Error loading credits file: {e}")
            return self._create_new_credits()
    
    def _create_new_credits(self) -> Dict:
        """Create new credit data"""
        now = datetime.now()
        return {
            "credits_remaining": self.max_credits,
            "credits_used": 0,
            "last_reset": now.isoformat(),
            "next_reset": (now + timedelta(hours=self.reset_hours)).isoformat(),
            "last_used": None
        }
    
    def _save_credits(self, data: Dict):
        """Save credit data to file"""
        try:
            with open(self.credits_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠ Error saving credits file: {e}")
    
    def _check_reset(self, data: Dict) -> Dict:
        """Check if credits should be reset"""
        now = datetime.now()
        next_reset = datetime.fromisoformat(data['next_reset'])
        
        if now >= next_reset:
            # Reset credits
            print(f"\n🔄 24 hours passed. Resetting credits to {self.max_credits}")
            return self._create_new_credits()
        
        return data
    
    def get_status(self) -> Dict:
        """Get current credit status"""
        data = self._load_credits()
        data = self._check_reset(data)
        self._save_credits(data)
        
        now = datetime.now()
        next_reset = datetime.fromisoformat(data['next_reset'])
        time_until_reset = next_reset - now
        
        hours = int(time_until_reset.total_seconds() // 3600)
        minutes = int((time_until_reset.total_seconds() % 3600) // 60)
        
        return {
            "credits_remaining": data['credits_remaining'],
            "credits_used": data['credits_used'],
            "max_credits": self.max_credits,
            "next_reset": data['next_reset'],
            "hours_until_reset": hours,
            "minutes_until_reset": minutes,
            "can_use": data['credits_remaining'] > 0
        }
    
    def use_credits(self, amount: int) -> bool:
        """
        Use credits if available
        
        Args:
            amount: Number of credits to use
            
        Returns:
            True if credits were used, False if insufficient
        """
        data = self._load_credits()
        data = self._check_reset(data)
        
        if data['credits_remaining'] < amount:
            return False
        
        # Use credits
        data['credits_remaining'] -= amount
        data['credits_used'] += amount
        data['last_used'] = datetime.now().isoformat()
        
        self._save_credits(data)
        return True
    
    def print_status(self):
        """Print credit status to terminal"""
        status = self.get_status()
        
        print(f"\n{'='*70}")
        print(f"📊 NewsData.io Credit Status")
        print(f"{'='*70}")
        print(f"Credits Remaining: {status['credits_remaining']}/{status['max_credits']}")
        print(f"Credits Used: {status['credits_used']}")
        print(f"Reset in: {status['hours_until_reset']}h {status['minutes_until_reset']}m")
        print(f"Next Reset: {status['next_reset']}")
        print(f"{'='*70}\n")
        
        return status


# Global instance
credit_manager = CreditManager()


if __name__ == "__main__":
    # Test the credit manager
    manager = CreditManager()
    
    print("Testing Credit Manager:")
    status = manager.print_status()
    
    print("\nTesting credit usage:")
    if manager.use_credits(50):
        print("✓ Used 50 credits")
        manager.print_status()
    else:
        print("✗ Insufficient credits")
    
    print("\nTesting insufficient credits:")
    if manager.use_credits(200):
        print("✓ Used 200 credits")
    else:
        print("✗ Insufficient credits (expected)")
        manager.print_status()
