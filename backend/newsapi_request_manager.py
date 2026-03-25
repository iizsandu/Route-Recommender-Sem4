"""
NewsAPI.org Request Manager
Tracks the daily request limit for the free Developer plan:
  - 100 requests / 24 hours
  - 100 articles per request (pageSize max, free tier)
  - Free tier: page 1 only (no pagination beyond page 1)
  - No separate rate window — just the daily cap
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict


class NewsAPIRequestManager:
    def __init__(self, requests_file: str = "newsapi_requests.json"):
        self.requests_file = requests_file
        self.max_requests = 100      # daily cap (free tier)
        self.reset_hours = 24
        self.articles_per_request = 100  # pageSize max on free tier

    # ── File I/O ───────────────────────────────────────────────────────────────

    def _load(self) -> Dict:
        if not os.path.exists(self.requests_file):
            return self._fresh()
        try:
            with open(self.requests_file, 'r') as f:
                return json.load(f)
        except Exception:
            return self._fresh()

    def _fresh(self) -> Dict:
        now = datetime.now()
        return {
            "requests_remaining": self.max_requests,
            "requests_used": 0,
            "last_reset": now.isoformat(),
            "next_reset": (now + timedelta(hours=self.reset_hours)).isoformat(),
            "last_used": None,
        }

    def _save(self, data: Dict):
        try:
            with open(self.requests_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  WARNING: Could not save newsapi requests file: {e}")

    def _apply_daily_reset(self, data: Dict) -> Dict:
        now = datetime.now()
        if now >= datetime.fromisoformat(data['next_reset']):
            print(f"  24h passed — resetting NewsAPI.org daily requests to {self.max_requests}")
            return self._fresh()
        return data

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        data = self._load()
        data = self._apply_daily_reset(data)
        self._save(data)

        now = datetime.now()
        next_reset = datetime.fromisoformat(data['next_reset'])
        secs_to_reset = max(0, (next_reset - now).total_seconds())
        hours = int(secs_to_reset // 3600)
        mins  = int((secs_to_reset % 3600) // 60)

        return {
            "requests_remaining": data['requests_remaining'],
            "requests_used": data['requests_used'],
            "max_requests": self.max_requests,
            "articles_per_request": self.articles_per_request,
            "next_reset": data['next_reset'],
            "hours_until_reset": hours,
            "minutes_until_reset": mins,
            "can_use": data['requests_remaining'] > 0,
        }

    def use_request(self) -> Dict:
        """
        Consume one request.
        Returns dict with:
          - allowed (bool)
          - reason (str)
        """
        data = self._load()
        data = self._apply_daily_reset(data)

        if data['requests_remaining'] <= 0:
            self._save(data)
            return {'allowed': False, 'reason': 'daily_exhausted'}

        data['requests_remaining'] -= 1
        data['requests_used'] += 1
        data['last_used'] = datetime.now().isoformat()
        self._save(data)
        return {'allowed': True, 'reason': 'ok'}

    def print_status(self) -> Dict:
        status = self.get_status()
        print(f"\n  NewsAPI.org Request Status")
        print(f"  Daily  : {status['requests_remaining']}/{status['max_requests']} remaining  "
              f"(resets in {status['hours_until_reset']}h {status['minutes_until_reset']}m)")
        print(f"  Max articles per request : {status['articles_per_request']}")
        return status


# Global instance
newsapi_request_manager = NewsAPIRequestManager()
