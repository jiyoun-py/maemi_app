"""EEG · 대사체 · 코르티솔 · 사이토카인과 MDD의 연관성을 계산하고, 앱에서 쓸 모델을 model_evidence.json으로 내보내요.

실행 (maeumi_app 폴더에서):
    venv\\Scripts\\python.exe analysis\\train_evidence.py --data "<데이터 관리 폴더 경로>"

- 필요 패키지: scikit-learn, scipy, openpyxl (앱 실행에는 numpy만 있으면 돼요)
- 시드가 고정돼 있어서 다시 돌리면 같은 숫자가 나와요.
- 네 데이터는 서로 다른 사람들에게서 나왔기 때문에, 모달리티별로 따로 학습해요. 통합은 학습이 아니라 규칙이에요.
"""
import argparse
import json
import math
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
REPEATS = 10
N_PERM = 199
N_BOOT = 300
GRID = np.linspace(0, 1, 51)
BAND = {"delta": "Delta", "theta": "Theta", "alpha": "Alpha", "beta": "Beta", "highbeta": "High-beta", "gamma": "Gamma"}
warnings.filterwarnings("ignore", category=RuntimeWarning)


def eeg_label(c):
    p = c.split(".")
    if p[0] == "COH":
        return f"{BAND[p[1]]} 연결성 {p[2]}–{p[3]}"
    return f"{BAND[p[0]]} 파워 {p[1]}"


def cohens_d(a, b):
    sp = math.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
    return (np.mean(a) - np.mean(b)) / sp if sp > 0 else 0.0


def associations(X, y, labels=None):
    """지표별 MDD와의 연관성: 점이연 상관 r, Cohen d, Mann-Whitney p, BH-FDR q"""
    rows = []
    for c in X.columns:
        v = X[c].to_numpy(float)
        a, b = v[y == 1], v[y == 0]
        if np.nanstd(v) == 0:
            continue
        rows.append({
            "feature": c, "label": (labels or {}).get(c, c), "r": float(stats.pearsonr(y, v)[0]), "d": float(cohens_d(a, b)),
            "p": float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue),
            "mean_mdd": float(a.mean()), "mean_ctrl": float(b.mean()),
        })
    q = stats.false_discovery_control([r["p"] for r in rows], method="bh")
    for r, v in zip(rows, q):
        r["q"] = float(v)
    return sorted(rows, key=lambda r: r["p"])


def make_pipe(k, c, balanced):
    steps = [("scale", StandardScaler())]
    if k:
        steps.append(("sel", SelectKBest(f_classif, k=k)))
    steps.append(("lr", LogisticRegression(C=c, max_iter=3000, class_weight="balanced" if balanced else None)))
    return Pipeline(steps)


def evaluate(X, y, k, c, balanced):
    """변수 선택까지 각 겹 안에서 수행하는 5겹 교차검증 × 10회 + 순열검정"""
    aucs, tprs, oofs, limits = [], [], [], []
    rng = np.random.default_rng(SEED)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    for r in range(REPEATS):
        cv = StratifiedKFold(5, shuffle=True, random_state=SEED + r)
        oof = cross_val_predict(make_pipe(k, c, balanced), X, y, cv=cv, method="predict_proba")[:, 1]
        aucs.append(roc_auc_score(y, oof))
        fpr, tpr, _ = roc_curve(y, oof)
        tprs.append(np.interp(GRID, fpr, tpr))
        oofs.append(oof)
        # 반복별로 환자를 재표집해 95% 구간을 구한 뒤 평균 (예측을 먼저 평균하면 AUC가 높게 치우쳐요)
        boot = []
        for _ in range(300):
            idx = np.r_[rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]
            boot.append(roc_auc_score(y[idx], oof[idx]))
        limits.append(np.percentile(boot, [2.5, 97.5]))
    mean_tpr = np.mean(tprs, axis=0)
    mean_tpr[0], mean_tpr[-1] = 0.0, 1.0
    oof = np.mean(oofs, axis=0)

    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    null = []
    for _ in range(N_PERM):
        yp = rng.permutation(y)
        null.append(roc_auc_score(yp, cross_val_predict(make_pipe(k, c, balanced), X, yp, cv=cv, method="predict_proba")[:, 1]))
    auc = float(np.mean(aucs))
    pred = oof >= 0.5
    return {
        "auc": auc, "auc_sd": float(np.std(aucs, ddof=1)), "auc_ci95": [float(v) for v in np.mean(limits, axis=0)],
        "sensitivity_at_0.5": float(pred[y == 1].mean()), "specificity_at_0.5": float((~pred[y == 0]).mean()),
        "sensitivity_at_spec80": float(np.interp(0.2, GRID, mean_tpr)),
        "perm_p": float((1 + sum(n >= auc for n in null)) / (N_PERM + 1)), "perm_mean_auc": float(np.mean(null)),
        "roc": [[round(float(f), 3), round(float(t), 4)] for f, t in zip(GRID, mean_tpr)],
        "cv": f"층화 5겹 × {REPEATS}회" + (" (변수 선택도 겹 내부)" if k else ""),
    }


def fit_final(X, y, k, c, balanced):
    """최종 모델 계수와 부트스트랩 계수(개인별 신뢰구간용), 변수 선택 안정성"""
    pipe = make_pipe(k, c, balanced).fit(X, y)
    mask = pipe.named_steps["sel"].get_support() if k else np.ones(X.shape[1], bool)
    scaler = pipe.named_steps["scale"]
    lr = pipe.named_steps["lr"]
    feats = list(X.columns[mask])
    Z = scaler.transform(X)
    Zs = Z[:, mask]
    rng = np.random.default_rng(SEED + 1)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    draws, hits = [], np.zeros(len(feats))
    for _ in range(N_BOOT):
        idx = np.r_[rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]
        m = LogisticRegression(C=c, max_iter=3000, class_weight="balanced" if balanced else None).fit(Zs[idx], y[idx])
        draws.append([round(float(m.intercept_[0]), 5)] + [round(float(v), 5) for v in m.coef_[0]])
        if k:
            top = SelectKBest(f_classif, k=k).fit(Z[idx], y[idx]).get_support()
            hits += top[mask]
    manual = 1 / (1 + np.exp(-(lr.intercept_[0] + Zs @ lr.coef_[0])))
    assert np.allclose(manual, pipe.predict_proba(X)[:, 1], atol=1e-8), "내보낸 계수가 학습 모델과 달라요"
    return {
        "features": feats, "mean": [float(v) for v in scaler.mean_[mask]], "scale": [float(v) for v in scaler.scale_[mask]],
        "intercept": float(lr.intercept_[0]), "coef": [float(v) for v in lr.coef_[0]], "boot": draws,
        "selection_stability": [round(float(v / N_BOOT), 3) for v in hits] if k else None,
    }


def group_values(X, y, feats, inverse=lambda v: v):
    return ({f: float(inverse(X.loc[y == 1, f].mean())) for f in feats}, {f: float(inverse(X.loc[y == 0, f].mean())) for f in feats})


def compact(rows, n):
    keep = ("feature", "label", "r", "d", "p", "q")
    return [{k: (round(r[k], 5) if isinstance(r.get(k), float) else r.get(k)) for k in keep} for r in rows[:n]]


def run_eeg(path):
    df = pd.read_csv(path).drop(columns=lambda c: c.startswith("Unnamed"), errors="ignore")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    y = (df["specific.disorder"] == "Depressive disorder").astype(int).to_numpy()
    X = df.drop(columns=["specific.disorder"]).astype(float)
    lab = {c: eeg_label(c) for c in X.columns}
    rows = associations(X, y, lab)

    # 대역별 요약 지표와 흔히 언급되는 지표(가설 검증용)
    s = pd.DataFrame(index=X.index)
    names = {}
    for b, nm in BAND.items():
        pw = [c for c in X.columns if c.startswith(b + ".") and not c.startswith("COH")]
        co = [c for c in X.columns if c.startswith(f"COH.{b}.")]
        s[f"pow_{b}"], names[f"pow_{b}"] = X[pw].mean(axis=1), f"{nm} 파워 (전 채널 평균)"
        s[f"coh_{b}"], names[f"coh_{b}"] = X[co].mean(axis=1), f"{nm} 연결성 (전 쌍 평균)"
    s["alpha_beta"], names["alpha_beta"] = s["pow_alpha"] / s["pow_beta"], "Alpha/Beta 비율"
    s["faa"], names["faa"] = np.log(X["alpha.F4"].clip(lower=1e-6)) - np.log(X["alpha.F3"].clip(lower=1e-6)), "전두 알파 비대칭 (ln F4 − ln F3)"
    summary = associations(s, y, names)

    k, c = 10, 1.0
    perf, final = evaluate(X.to_numpy(), y, k, c, True), fit_final(X, y, k, c, True)
    mdd, ctrl = group_values(X, y, final["features"])
    final.update(type="logistic", transform="none", labels=[lab[f] for f in final["features"]], k=k, C=c)
    return {
        "name": "EEG", "label": "뇌파 (EEG)", "tier": "data", "tier_label": "개인별 측정값 학습", "n_mdd": int(y.sum()), "n_control": int((1 - y).sum()),
        "source": "machinelearning_data_EEG.csv (Depressive disorder vs Healthy control)",
        "limits": ["파일에 원 논문·기관 정보가 없어 출처 확인 필요", "피험자 ID가 없어 반복 측정 여부를 확인할 수 없음", "변수 1,140개 대비 표본 294명: 선택 변수의 재현 연구 필요",
                   "확률은 두 군을 같은 비율로 가정한 값이며 유병률을 반영하지 않음"],
        "n_tested": len(rows), "n_fdr05": sum(r["q"] < .05 for r in rows), "associations": compact(rows, 12), "summary_markers": compact(summary, 20),
        "perf": perf, "model": final, "demo": {"mdd": mdd, "control": ctrl},
    }


def run_metabolites(path):
    raw = pd.read_csv(path, sep="\t", header=None, dtype=str, encoding="utf-8", encoding_errors="replace")
    groups = raw.iloc[1, 1:].astype(str).str.strip()
    body = raw.iloc[2:]
    body = body[body[0].notna() & (body[0].astype(str).str.strip() != "")]
    valid = groups.str.contains("Group")
    X = body.loc[:, [0] + list(groups.index[valid])].set_index(0).astype(float).T
    X.columns = [str(c).strip() for c in X.columns]
    X = X.loc[:, ~X.columns.duplicated()].reset_index(drop=True)
    y = groups[valid].str.contains("Score 50").astype(int).to_numpy()
    L = np.log2(X.clip(lower=0) + 1)
    rows = associations(L, y)
    k, c = 5, 0.5
    perf, final = evaluate(L.to_numpy(), y, k, c, True), fit_final(L, y, k, c, True)
    mdd, ctrl = group_values(L, y, final["features"], lambda v: 2 ** v - 1)
    final.update(type="logistic", transform="log2p1", labels=final["features"], k=k, C=c)
    return {
        "name": "Metabolites", "label": "대사체", "tier": "data", "tier_label": "개인별 측정값 학습", "n_mdd": int(y.sum()), "n_control": int((1 - y).sum()),
        "source": "Metabolomics Workbench ST000062 / AN000100, 혈장 GC-MS (UC Davis WCMC). MDD는 BDI 기준 (CC BY-NC-ND)",
        "limits": ["Group 2(Score 50)=MDD, Group 1(Score 0)=대조는 연구 설명(BDI 기반 MDD 50·대조 50)에서 해석한 것으로 파일에 명시되지 않음",
                   "임상 진단이 아니라 설문(BDI) 기준의 일반인 표본", "표본 97명으로 작아 AUC 변동이 큼", "질량분석 강도값이라 다른 실험실 값과 바로 비교할 수 없음"],
        "n_tested": len(rows), "n_fdr05": sum(r["q"] < .05 for r in rows), "associations": compact(rows, 12),
        "perf": perf, "model": final, "demo": {"mdd": mdd, "control": ctrl},
    }


def run_cortisol(path):
    df = pd.read_csv(path)
    y = (df["Diagnosis"] == "MDD").astype(int).to_numpy()
    rows = associations(df[["Cortisol", "IGF1", "Age", "BMI"]].astype(float), y,
                        {"Cortisol": "코르티솔", "IGF1": "IGF-1", "Age": "나이", "BMI": "BMI"})
    X = df[["Cortisol"]].astype(float)
    perf, final = evaluate(X.to_numpy(), y, 0, 1.0, False), fit_final(X, y, 0, 1.0, False)
    mdd, ctrl = group_values(X, y, ["Cortisol"])
    final.update(type="logistic", transform="none", labels=["코르티솔"], k=None, C=1.0)
    return {
        "name": "Cortisol", "label": "코르티솔", "tier": "simulation", "tier_label": "시뮬레이션 데이터", "n_mdd": int(y.sum()), "n_control": int((1 - y).sum()),
        "source": "MDD_Simulation_Dataset.csv (시뮬레이션 자료, 실제 환자 코호트가 아님)",
        "limits": ["시뮬레이션 데이터라 MDD 연관성의 근거로 인용할 수 없음", "측정 단위와 채혈 시각 정보 없음", "GAF, HAM-D는 MDD 군에만 있어 정보 누수 방지를 위해 제외"],
        "n_tested": len(rows), "n_fdr05": sum(r["q"] < .05 for r in rows), "associations": compact(rows, 12),
        "perf": perf, "model": final, "demo": {"mdd": mdd, "control": ctrl},
    }


def run_cytokine(path):
    t = pd.read_excel(path)
    rows = []
    for _, r in t.iterrows():
        try:
            hm, hs = [float(v) for v in str(r["HC_Mean_SD"]).split("±")]
            mm, ms = [float(v) for v in str(r["MDD_Mean_SD"]).split("±")]
        except ValueError:
            continue
        d = (mm - hm) / math.sqrt((hs ** 2 + ms ** 2) / 2)
        rows.append({
            "feature": str(r["Marker"]).strip(), "label": str(r["Marker"]).strip(), "hc_mean": hm, "hc_sd": hs, "mdd_mean": mm, "mdd_sd": ms,
            "d": round(d, 3), "r": round(d / math.sqrt(d ** 2 + 4), 3), "auc_if_normal": round(float(stats.norm.cdf((mm - hm) / math.sqrt(hs ** 2 + ms ** 2))), 3),
            "H": float(r["H_value"]), "q_reported": str(r["q_value"]), "post_hoc": str(r["Post_hoc"]),
        })
    rows.sort(key=lambda r: -r["H"])
    top = rows[:5]
    return {
        "name": "Cytokine", "label": "사이토카인", "tier": "summary", "tier_label": "논문 요약통계 기반", "n_mdd": None, "n_control": None,
        "source": "STable1_MDD_HC_only.xlsx (논문 보충표의 군별 평균±SD, H값, q값)",
        "limits": ["개인별 값이 없어 교차검증·AUC·신뢰구간 산출 불가", "표본 수와 원 논문 정보 미기재: 출처 확인 필요", "정규분포와 마커 간 독립을 가정하며 실제 농도 분포는 치우침이 큼",
                   "H값은 원 논문의 다군 비교 결과일 수 있고, r은 d에서 환산한 추정치"],
        "n_tested": len(rows), "n_fdr05": sum(r["q_reported"].strip() in ("<.001", "<0.001") or (r["q_reported"].replace(".", "", 1).isdigit() and float(r["q_reported"]) < .05) for r in rows),
        "associations": rows[:12], "perf": None,
        "model": {"type": "gaussian_lr", "transform": "none", "features": [r["feature"] for r in top], "labels": [r["label"] for r in top],
                  "mu_mdd": [r["mdd_mean"] for r in top], "sd_mdd": [r["mdd_sd"] for r in top], "mu_ctrl": [r["hc_mean"] for r in top], "sd_ctrl": [r["hc_sd"] for r in top]},
        "demo": {"mdd": {r["feature"]: r["mdd_mean"] for r in top}, "control": {r["feature"]: r["hc_mean"] for r in top}},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    root = Path(__file__).resolve().parent.parent
    d = Path(ap.parse_args().data)
    mods = {
        "eeg": run_eeg(d / "machinelearning_data_EEG.csv"),
        "metabolites": run_metabolites(d / "MSdata_ST000062_AN000100.txt"),
        "cytokine": run_cytokine(d / "STable1_MDD_HC_only.xlsx"),
        "cortisol": run_cortisol(d / "MDD_Simulation_Dataset.csv"),
    }
    out = {
        "generated": datetime.now().isoformat(timespec="seconds"), "seed": SEED,
        "disclaimer": "연구용 시연 모델이며 개인 진단 도구가 아닙니다.",
        "fusion": {"rule": "입력된 모달리티 로짓의 동일 가중 평균", "validated": False,
                   "why": "4종 데이터가 서로 다른 사람들에게서 나와 같은 환자의 4종 값이 없으므로 결합 가중치를 학습·검증할 수 없음"},
        "modalities": mods,
    }
    demo_dir = root / "demo_data"
    demo_dir.mkdir(exist_ok=True)
    for key, fn in (("mdd", "demo_patient_mdd_pattern.csv"), ("control", "demo_patient_control_pattern.csv")):
        row = {f: round(v, 5) for m in mods.values() for f, v in m["demo"][key].items()}
        pd.DataFrame([row]).to_csv(demo_dir / fn, index=False, encoding="utf-8-sig")
    (root / "model_evidence.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for k, m in mods.items():
        p = m["perf"]
        print(f"\n[{k}] {m['tier']} mdd={m['n_mdd']} ctrl={m['n_control']} tested={m['n_tested']} FDR<.05={m['n_fdr05']}")
        if p:
            print(f"  AUC {p['auc']:.3f} sd {p['auc_sd']:.3f} CI {p['auc_ci95'][0]:.3f}-{p['auc_ci95'][1]:.3f} sens {p['sensitivity_at_0.5']:.2f} spec {p['specificity_at_0.5']:.2f} "
                  f"sens@spec80 {p['sensitivity_at_spec80']:.2f} perm_p {p['perm_p']:.3f} null {p['perm_mean_auc']:.3f}")
        print("  model:", list(zip(m["model"]["labels"], m["model"].get("selection_stability") or [None] * len(m["model"]["labels"]))))
        for r in m["associations"][:6]:
            print(f"   {r['label']}: r={r['r']:+.3f} d={r['d']:+.2f} q={r.get('q', r.get('q_reported'))}")
        for r in m.get("summary_markers", [])[:16]:
            print(f"   [요약] {r['label']}: r={r['r']:+.3f} d={r['d']:+.2f} q={r['q']:.3f}")


if __name__ == "__main__":
    main()
