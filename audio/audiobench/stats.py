"""Uncertainty tools: Wilson CI, cluster bootstrap over items, paired comparisons, judge-error correction."""
import math

import numpy as np
from scipy import stats as st


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def cluster_bootstrap(matrix, B=5000, seed=0):
    """matrix: items x runs (NaN allowed). Resamples items, keeps each item's runs together.
    Returns (mean, lo, hi). Captures item-sampling variance; run variance enters via the item means."""
    m = np.asarray(matrix, dtype=float)
    item_means = np.nanmean(m, axis=1)
    item_means = item_means[~np.isnan(item_means)]
    if len(item_means) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(item_means), size=(B, len(item_means)))
    boots = item_means[idx].mean(axis=1)
    return (item_means.mean(), *np.percentile(boots, [2.5, 97.5]))


def flip_rate(matrix):
    """Share of items whose binary outcome is not the same in every run."""
    m = np.asarray(matrix, dtype=float)
    ok = ~np.isnan(m).any(axis=1)
    m = m[ok]
    if m.shape[0] == 0 or m.shape[1] < 2:
        return np.nan
    return float(np.mean(m.min(axis=1) != m.max(axis=1)))


def paired_bootstrap_diff(a, b, B=5000, seed=0):
    """a, b: per-item means for two models on the same items (aligned). Returns (diff, lo, hi, p_two_sided)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    d = a[ok] - b[ok]
    if len(d) == 0:
        return (np.nan,) * 4
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, len(d), size=(B, len(d)))].mean(axis=1)
    p = 2 * min(np.mean(boots <= 0), np.mean(boots >= 0))
    return (d.mean(), *np.percentile(boots, [2.5, 97.5]), min(1.0, p))


def mcnemar(a, b):
    """Exact McNemar test on paired binary outcomes."""
    a, b = np.asarray(a), np.asarray(b)
    n01 = int(np.sum((a == 0) & (b == 1)))
    n10 = int(np.sum((a == 1) & (b == 0)))
    if n01 + n10 == 0:
        return 1.0
    return float(st.binomtest(n01, n01 + n10, 0.5).pvalue)


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def cohen_kappa(x, y):
    x, y = np.asarray(x), np.asarray(y)
    cats = np.union1d(x, y)
    po = np.mean(x == y)
    pe = sum(np.mean(x == c) * np.mean(y == c) for c in cats)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def binary_metrics(pred, truth):
    pred, truth = np.asarray(pred), np.asarray(truth)
    tp = int(np.sum((pred == 1) & (truth == 1)))
    fp = int(np.sum((pred == 1) & (truth == 0)))
    fn = int(np.sum((pred == 0) & (truth == 1)))
    tn = int(np.sum((pred == 0) & (truth == 0)))
    prec = tp / (tp + fp) if tp + fp else np.nan
    rec = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else np.nan
    return dict(n=len(pred), tp=tp, fp=fp, fn=fn, tn=tn, accuracy=(tp + tn) / len(pred),
                precision=prec, recall=rec, f1=f1, specificity=spec, fpr=1 - spec if spec == spec else np.nan)


def rogan_gladen(p_obs, sens, spec):
    """Corrects an observed rate for judge sensitivity/specificity; clipped to [0, 1]."""
    den = sens + spec - 1
    if den <= 0:
        return np.nan
    return float(np.clip((p_obs + spec - 1) / den, 0, 1))


def corrected_ci(matrix, calib_pred, calib_truth, B=5000, seed=0):
    """Bootstraps test items AND the human-labelled calibration set together, so judge error widens the CI."""
    m = np.asarray(matrix, float)
    item_means = np.nanmean(m, axis=1)
    item_means = item_means[~np.isnan(item_means)]
    cp, ct = np.asarray(calib_pred), np.asarray(calib_truth)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        im = item_means[rng.integers(0, len(item_means), len(item_means))]
        j = rng.integers(0, len(cp), len(cp))
        bm = binary_metrics(cp[j], ct[j])
        v = rogan_gladen(im.mean(), bm["recall"], bm["specificity"])
        if v == v:
            vals.append(v)
    bm = binary_metrics(cp, ct)
    point = rogan_gladen(item_means.mean(), bm["recall"], bm["specificity"])
    if not vals:
        return (point, np.nan, np.nan)
    return (point, *np.percentile(vals, [2.5, 97.5]))
