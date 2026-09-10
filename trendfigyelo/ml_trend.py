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


def _linearis_fp(xt, yt, xq):
    b1, b0 = np.polyfit(xt, yt, 1)
    return b0 + b1 * xq


def nemlin_trend(pontok, gorbe_pont=60, margo=0.05, spanok=(0.3, 0.5, 0.7), k=5):
    y = np.array([p["ertek"] for p in pontok], float)
    n = len(y)
    if n < 12:
        return None
    x = np.arange(n, dtype=float)
    idok = [p["idopont_utc"] for p in pontok]
    lin_cv = cv_r2(x, y, _linearis_fp, k)
    # legjobb span CV szerint
    best = None
    for sp in spanok:
        fp = (lambda s: (lambda xt, yt, xq: _loess_predict(xt, yt, xq, s)))(sp)
        cv = cv_r2(x, y, fp, k)
        if best is None or cv > best[1]:
            best = (sp, cv)
    span, cv = best
    # túltanulás-őr: a nemlineáris görbét CSAK akkor jelöljük struktúrának, ha (1) a
    # kereszt-validált R² a lineáris bázist legalább `margo`-val veri, ÉS (2) abszolút
    # értelemben pozitív (out-of-sample jobb a lapos átlagnál). A (2) padló zárja a relatív
    # őr vakfoltját: ha MINDKÉT illesztés a mérce alatti (negatív cv), a „kevésbé rossz"
    # nemlineáris se rajzoljon negatív R²-ű görbét (naming-discipline: zajra nincs trend).
    van = cv >= lin_cv + margo and cv > 0
    if not van:
        return {"van_struktura": False, "gorbe": [], "cv_r2": round(cv, 3),
                "lin_cv_r2": round(lin_cv, 3), "span": span, "eff_df": None,
                "irany": None, "fordulopontok": None, "rezidualis_szoras": None}
    sim = loess(x, y, span)
    # metrikák
    resid = float(np.std(y - sim))
    irany = "novekszik" if sim[-1] - sim[0] > 1 else ("csokken" if sim[-1] - sim[0] < -1 else "hullamzik")
    d = np.diff(sim)
    fordulo = int(np.sum(np.abs(np.diff(np.sign(d))) > 0))   # előjelváltások a deriváltban
    eff_df = round(_eff_df(x, span), 1)
    # görbe ritkítva ~gorbe_pont pontra (a sima elég sűrű, kevesebb pont is jó)
    lep = max(1, n // gorbe_pont)
    gorbe = [{"idopont_utc": idok[i], "ertek": round(float(sim[i]), 1)} for i in range(0, n, lep)]
    if gorbe[-1]["idopont_utc"] != idok[-1]:
        gorbe.append({"idopont_utc": idok[-1], "ertek": round(float(sim[-1]), 1)})
    return {"van_struktura": True, "gorbe": gorbe, "cv_r2": round(cv, 3),
            "lin_cv_r2": round(lin_cv, 3), "span": span, "eff_df": eff_df,
            "irany": irany, "fordulopontok": fordulo, "rezidualis_szoras": round(resid, 1)}


def _loess_predict(xt, yt, xq, span):
    """LOESS becslés tetszőleges xq query-pontokon (a CV-hez; a train-only pontokból)."""
    xt = np.asarray(xt, float); yt = np.asarray(yt, float); xq = np.asarray(xq, float)
    k = max(3, int(np.ceil(span * len(xt))))
    out = np.empty(len(xq))
    for i, x0 in enumerate(xq):
        d = np.abs(xt - x0); idx = np.argsort(d)[:k]; dm = d[idx].max() or 1.0
        w = (1 - (d[idx] / dm) ** 3) ** 3; w[w < 0] = 0
        X = np.vstack([np.ones(len(idx)), xt[idx]]).T; W = np.diag(w)
        try:
            beta = np.linalg.solve(X.T @ W @ X + 1e-9 * np.eye(2), X.T @ W @ yt[idx])
            out[i] = beta[0] + beta[1] * x0
        except np.linalg.LinAlgError:
            out[i] = np.average(yt[idx], weights=w) if w.sum() else yt[idx].mean()
    return out


def _eff_df(x, span):
    """Effektív szabadságfok ≈ a simító-mátrix nyoma (trace(L)). O(N*k)."""
    n = len(x); k = max(3, int(np.ceil(span * n))); tr = 0.0
    for i in range(n):
        d = np.abs(x - x[i]); idx = np.argsort(d)[:k]; dm = d[idx].max() or 1.0
        w = (1 - (d[idx] / dm) ** 3) ** 3; w[w < 0] = 0
        X = np.vstack([np.ones(len(idx)), x[idx]]).T; W = np.diag(w)
        try:
            H = X @ np.linalg.solve(X.T @ W @ X + 1e-9 * np.eye(2), X.T @ W)
            j = list(idx).index(i)
            tr += H[j, j]
        except np.linalg.LinAlgError:
            tr += 1.0 / k
    return tr
