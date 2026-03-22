"""
NewsData.io Credit Manager
Tracks two limits:
  - Daily budget  : 200 credits per 24 hours
  - Rate window   : 30 requests per 15 minutes (rolling)
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict


class CreditManager:
    def __init__(self, credits_file: str = "newsdata_credits.json"):
        self.credits_file = credits_file
        self.max_credits = 200       # daily cap
        self.reset_hours = 24
        self.max_per_window = 30     # requests per window
        self.window_seconds = 900    # 15 minutes

    # ── File I/O ───────────────────────────────────────────────────────────────

    def _load(self) -> Dict:
        if not os.path.exists(self.credits_file):
            return self._fresh()
        try:
            with open(self.credits_file, 'r') as f:
                return json.load(f)
        except Exception:
            return self._fresh()

    def _fresh(self) -> Dict:
        now = datetime.now()
        return {
            "credits_remaining": self.max_credits,
            "credits_used": 0,
            "last_reset": now.isoformat(),
            "next_reset": (now + timedelta(hours=self.reset_hours)).isoformat(),
            "last_used": None,
            # rate window
            "window_start": now.isoformat(),
            "window_used": 0,
        }

    def _save(self, data: Dict):
        try:
            with open(self.credits_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  WARNING: Could not save credits file: {e}")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _apply_daily_reset(self, data: Dict) -> Dict:
        """Reset daily budget if 24h have passed."""
        now = datetime.now()
        if now >= datetime.fromisoformat(data['next_reset']):
            print(f"  24h passed — resetting daily credits to {self.max_credits}")
            fresh = self._fresh()
            # preserve window state across daily reset
            fresh['window_start'] = data.get('window_start', now.isoformat())
            fresh['window_used'] = data.get('window_used', 0)
            return fresh
        return data

    def _window_info(self, data: Dict):
        """
        Returns (window_used, window_remaining, wait_seconds).
        wait_seconds > 0 means the window is full and caller must wait.
        """
        now = datetime.now()
        window_start = datetime.fromisoformat(data.get('window_start', now.isoformat()))
        window_used = data.get('window_used', 0)
        elapsed = (now - window_start).total_seconds()

        if elapsed >= self.window_seconds:
            # Window has expired — reset it
            data['window_start'] = now.isoformat()
            data['window_used'] = 0
            window_used = 0
            elapsed = 0

        window_remaining = self.max_per_window - window_used
        if window_remaining <= 0:
            wait_seconds = self.window_seconds - elapsed
            return window_used, 0, max(0, wait_seconds)

        return window_used, window_remaining, 0

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        data = self._load()
        data = self._apply_daily_reset(data)
        self._save(data)

        now = datetime.now()
        next_reset = datetime.fromisoformat(data['next_reset'])
        secs_to_daily = max(0, (next_reset - now).total_seconds())
        daily_hours = int(secs_to_daily // 3600)
        daily_mins  = int((secs_to_daily % 3600) // 60)

        window_used, window_remaining, wait_secs = self._window_info(data)

        return {
            # daily
            "credits_remaining": data['credits_remaining'],
            "credits_used": data['credits_used'],
            "max_credits": self.max_credits,
            "next_reset": data['next_reset'],
            "hours_until_reset": daily_hours,
            "minutes_until_reset": daily_mins,
            "can_use": data['credits_remaining'] > 0 and window_remaining > 0,
            # window
            "window_used": window_used,
            "window_remaining": window_remaining,
            "window_max": self.max_per_window,
            "window_wait_seconds": round(wait_secs),
        }

    def use_credit(self) -> Dict:
        """
        Consume one credit.
        Returns dict with:
          - allowed (bool)
          - wait_seconds (int) — if > 0, caller should sleep this long then retry
          - reason (str)
        """
        data = self._load()
        data = self._apply_daily_reset(data)

        # Check daily budget
        if data['credits_remaining'] <= 0:
            self._save(data)
            return {'allowed': False, 'wait_seconds': 0, 'reason': 'daily_exhausted'}

        # Check window
        window_used, window_remaining, wait_secs = self._window_info(data)
        if window_remaining <= 0:
            self._save(data)
            return {'allowed': False, 'wait_seconds': round(wait_secs) + 1, 'reason': 'window_full'}

        # Consume
        data['credits_remaining'] -= 1
        data['credits_used'] += 1
        data['window_used'] = window_used + 1
        data['last_used'] = datetime.now().isoformat()
        self._save(data)
        return {'allowed': True, 'wait_seconds': 0, 'reason': 'ok'}

    # kept for backward compat — uses N credits at once (no window check per-credit)
    def use_credits(self, amount: int) -> bool:
        data = self._load()
        data = self._apply_daily_reset(data)
        if data['credits_remaining'] < amount:
            self._save(data)
            return False
        data['credits_remaining'] -= amount
        data['credits_used'] += amount
        data['window_used'] = data.get('window_used', 0) + amount
        data['last_used'] = datetime.now().isoformat()
        self._save(data)
        return True

    def print_status(self) -> Dict:
        status = self.get_status()
        print(f"\n  NewsData.io Credit Status")
        print(f"  Daily  : {status['credits_remaining']}/{status['max_credits']} remaining  (resets in {status['hours_until_reset']}h {status['minutes_until_reset']}m)")
        print(f"  Window : {status['window_remaining']}/{status['window_max']} remaining in current 15-min window")
        if status['window_wait_seconds'] > 0:
            m, s = divmod(status['window_wait_seconds'], 60)
            print(f"  Window full — wait {m}m {s}s before next request")
        return status


# Global instance
credit_manager = CreditManager()
