"""Nemlineáris (LOESS) trend — tiszta numpy, determinista, nulla új függőség."""
import numpy as np


def loess(x, y, span=0.4, robusztus_iter=1):
    """Lokális súlyozott lineáris regresszió (tricube kernel). Visszaad: sima értékek az x-en.
    `span` = az ablak aránya (a legközelebbi ceil(span*N) pont)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x)
    if n < 3:
        return y.copy()
    k = max(3, int(np.ceil(span * n)))
    sulyok = np.ones(n)                       # robusztussági súlyok (kezdetben 1)
    yhat = y.copy()
    for _ in range(max(1, robusztus_iter)):
        for i in range(n):
            d = np.abs(x - x[i])
            idx = np.argsort(d)[:k]
            dm = d[idx].max() or 1.0
            w = (1 - (d[idx] / dm) ** 3) ** 3
            w[w < 0] = 0
            w = w * sulyok[idx]
            X = np.vstack([np.ones(k), x[idx]]).T
            W = np.diag(w)
            try:
                beta = np.linalg.solve(X.T @ W @ X + 1e-9 * np.eye(2), X.T @ W @ y[idx])
                yhat[i] = beta[0] + beta[1] * x[i]
            except np.linalg.LinAlgError:
                yhat[i] = np.average(y[idx], weights=w) if w.sum() else y[i]
        # robusztussági súlyok frissítése a reziduumból (bisquare)
        r = y - yhat
        s = np.median(np.abs(r)) or 1.0
        u = np.clip(r / (6 * s), -1, 1)
        sulyok = (1 - u ** 2) ** 2
    return yhat


def cv_r2(x, y, fit_predict, k=5):
    """Determinista k-fold out-of-sample R². Fold = index % k (NINCS véletlen)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x)
    if n < k + 2:
        return 0.0
    yhat = np.full(n, np.nan)
    for f in range(k):
        teszt = np.arange(n) % k == f
        tren = ~teszt
        if tren.sum() < 2 or teszt.sum() == 0:
            continue
        yhat[teszt] = fit_predict(x[tren], y[tren], x[teszt])
    ok = ~np.isnan(yhat)
    ss_tot = ((y[ok] - y[ok].mean()) ** 2).sum()
    if ss_tot <= 0:
        return 0.0
    return float(1 - ((y[ok] - yhat[ok]) ** 2).sum() / ss_tot)
