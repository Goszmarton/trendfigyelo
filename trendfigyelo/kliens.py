"""Trends-kliens véletlenített késleltetéssel és 429-backoffal (IP-blokkolás elleni védelem)."""

import random
import time


class AgFeladva(Exception):
    """Egy lekérdezési ág feladva ismételt 429 (rate limit) miatt."""

    def __init__(self, ag: str, hibakodok):
        super().__init__(f"'{ag}' ág feladva {len(hibakodok)} próba után: {hibakodok}")
        self.ag = ag
        self.hibakodok = hibakodok


def rate_limit_hiba(exc: Exception) -> bool:
    """Igaz, ha a kivétel HTTP 429 / rate limit."""
    kod = getattr(exc, "status_code", None)
    if kod is None:
        valasz = getattr(exc, "response", None)
        kod = getattr(valasz, "status_code", None)
    if kod == 429:
        return True
    szoveg = str(exc).lower()
    return "429" in szoveg or "too many requests" in szoveg


class Kliens:
    """Minden Google-hívás ezen megy át: késleltetés, 429-backoff, hívásszámlálás."""

    def __init__(self, config, trends=None, trends_gyar=None):
        self.config = config
        if trends is None:
            if trends_gyar is None:
                from trendspy import Trends
                trends_gyar = Trends
            trends = trends_gyar(
                language=config.nyelv,
                request_delay=config.alap_keses_mp,
                proxy=config.proxy,
            )
        self.tr = trends
        self._szamlalok = {}

    def _var(self):
        also, felso = self.config.szoras_mp
        time.sleep(random.uniform(also, felso))

    def _backoff(self, proba: int):
        bo = self.config.backoff_mp
        alap = bo[min(proba, len(bo) - 1)]
        time.sleep(alap + random.uniform(0, alap * 0.25))

    def hivas(self, ag: str, fn, *args, **kwargs):
        """fn meghívása anti-block védelemmel; 429 kimerülésnél AgFeladva."""
        self._szamlalok.setdefault(ag, 0)
        hibakodok = []
        for proba in range(self.config.max_probak):
            self._var()
            self._szamlalok[ag] += 1
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if not rate_limit_hiba(e):
                    raise
                hibakodok.append("429")
                if proba < self.config.max_probak - 1:
                    self._backoff(proba)
        raise AgFeladva(ag, hibakodok)

    def hivasszam(self, ag: str) -> int:
        return self._szamlalok.get(ag, 0)

    def osszes_hivas(self) -> int:
        return sum(self._szamlalok.values())
