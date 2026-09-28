import time

class AlertManager:
    def __init__(self, cooldown=5):
        self.cooldown = cooldown
        self.last = {}

    def allow(self, key):
        now = time.monotonic()
        if now - self.last.get(key, 0) >= self.cooldown:
            self.last[key] = now
            return True
        return False
