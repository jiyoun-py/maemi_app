"""연구 모드: 건강검진 항목으로 우울 증상 관련 바이오마커 후보를 탐색해요. 결과는 research_evidence.json으로 저장돼요.

데이터: 국민건강영양조사 2024 원시자료(질병관리청) — 팀 폴더의 '건강 정보 자료 2024.csv'
정답(라벨): PHQ-9 총점 10점 이상 = 우울 증상 선별 양성 (진단이 아닌 선별 기준)
대상: 만 19세 이상, PHQ-9 응답자

계산 내용
1) 항목별 연관성: 나이·성별 보정 로지스틱 회귀 → 1 표준편차 증가당 오즈비(OR), 95% 구간, p, FDR q
2) 선택 안정성: 부트스트랩 100회 × L1 로지스틱(모든 항목 동시) → 항목이 선택된 비율
3) 예측 성능: 검진 항목 + 나이·성별 모델 vs 나이·성별만 모델의 교차검증 AUC
4) 데이터 증가 시나리오: 500명~전체를 무작위로 뽑아 '발견되는 후보 수'와 AUC가 어떻게 변하는지

실행: venv\\Scripts\\python.exe analysis\\research_checkup.py --data "<건강 정보 자료 2024.csv 경로>"
주의: 단면 조사라 원인·결과를 말할 수 없고, 조사 가중치(전 국민 대표성)는 탐색 단계에서 적용하지 않았어요.
"""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
# (변수, 이름, 단위, 그룹, 로그 변환 여부)
VARS = [
    ("HE_BMI", "체질량지수(BMI)", "kg/m²", "신체계측", False), ("HE_wc", "허리둘레", "cm", "신체계측", False),
    ("HE_sbp", "수축기 혈압", "mmHg", "혈압", False), ("HE_dbp", "이완기 혈압", "mmHg", "혈압", False),
    ("HE_glu", "공복혈당", "mg/dL", "당대사", False), ("HE_HbA1c", "당화혈색소", "%", "당대사", False),
    ("HE_chol", "총콜레스테롤", "mg/dL", "지질", False), ("HE_HDL_st2", "HDL 콜레스테롤", "mg/dL", "지질", False),
    ("HE_TG", "중성지방", "mg/dL", "지질", True), ("HE_LDL_drct", "LDL 콜레스테롤", "mg/dL", "지질", False),
    ("HE_ast", "AST(간)", "IU/L", "간기능", True), ("HE_alt", "ALT(간)", "IU/L", "간기능", True),
    ("HE_ALP", "알칼리인산분해효소", "IU/L", "간기능", False),
    ("HE_BUN", "혈중요소질소", "mg/dL", "신장", False), ("HE_crea", "크레아티닌", "mg/dL", "신장", False),
    ("HE_Uacid", "요산", "mg/dL", "신장", False),
    ("HE_HB", "혈색소", "g/dL", "혈액", False), ("HE_HCT", "적혈구용적률", "%", "혈액", False),
    ("HE_WBC", "백혈구", "천/µL", "혈액·면역", False), ("HE_RBC", "적혈구", "백만/µL", "혈액", False),
    ("HE_Bplt", "혈소판", "천/µL", "혈액", False), ("HE_MCV", "평균적혈구용적", "fL", "혈액", False),
    ("HE_MCH", "평균적혈구혈색소", "pg", "혈액", False), ("HE_MCHC", "평균적혈구혈색소농도", "g/dL", "혈액", False),
    ("HE_hsCRP", "고감도 CRP(염증)", "mg/L", "염증", True),
    ("HE_Ca", "칼슘", "mg/dL", "무기질·호르몬", False), ("HE_P", "인", "mg/dL", "무기질·호르몬", False),
    ("HE_Mg", "마그네슘", "mg/dL", "무기질·호르몬", False), ("HE_PTH", "부갑상선호르몬", "pg/mL", "무기질·호르몬", True),
    ("HE_D3", "비타민 D", "ng/mL", "무기질·호르몬", False),
    ("HE_Usg", "소변 비중", "", "소변", False), ("HE_Uph", "소변 pH", "", "소변", False),
    ("HE_Ucrea", "소변 크레아티닌", "mg/dL", "소변", True), ("HE_UNa", "소변 나트륨", "mmol/L", "소변", False),
    ("HE_Ualb", "소변 알부민", "mg/L", "소변", True), ("HE_Ukal", "소변 칼륨", "mmol/L", "소변", False),
    ("HE_fvc", "노력성 폐활량", "L", "폐기능", False), ("HE_fev1", "1초간 노력성 호기량", "L", "폐기능", False),
    ("HE_fev1fvc", "1초율(FEV1/FVC)", "", "폐기능", False),
]


def load(path):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise SystemExit("CSV 인코딩을 읽지 못했어요.")


def logit_fit(X, y, iters=50):
    """뉴턴-랩슨 로지스틱 회귀 → 계수와 표준오차"""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ b)))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-8:
            break
    p = 1 / (1 + np.exp(-(X @ b)))
    cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))
    return b, np.sqrt(np.diag(cov))


def adjusted_assoc(d, y_col="y"):
    """항목별로 나이·성별 보정 → 1 SD당 오즈비"""
    out = []
    for v, *_ in VARS:
        sub = d[[v, "age", "female", y_col]].dropna()
        if sub[y_col].sum() < 10 or len(sub) < 100:
            out.append(None)
            continue
        z = (sub[v] - sub[v].mean()) / sub[v].std()
        age = (sub["age"] - sub["age"].mean()) / sub["age"].std()
        X = np.column_stack([np.ones(len(sub)), age, sub["female"], z])
        b, se = logit_fit(X, sub[y_col].to_numpy(float))
        pval = 2 * stats.norm.sf(abs(b[3] / se[3]))
        out.append({"n": len(sub), "n_pos": int(sub[y_col].sum()), "beta": b[3], "se": se[3], "p": pval})
    ps = [o["p"] for o in out if o]
    qs = iter(stats.false_discovery_control(ps, method="bh")) if ps else iter([])
    for o in out:
        if o:
            o["q"] = float(next(qs))
    return out


def model(C=0.5):
    return Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler()),
                     ("lr", LogisticRegression(C=C, class_weight="balanced", max_iter=3000))])


def cv_auc(X, y, repeats, seed):
    aucs = []
    for r in range(repeats):
        cv = StratifiedKFold(5, shuffle=True, random_state=seed + r)
        aucs.append(roc_auc_score(y, cross_val_predict(model(), X, y, cv=cv, method="predict_proba")[:, 1]))
    return aucs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    root = Path(__file__).resolve().parent.parent
    raw = load(ap.parse_args().data)

    d = raw.copy()
    d["age"] = pd.to_numeric(d["age"], errors="coerce")
    d["phq"] = pd.to_numeric(d["mh_PHQ_S"], errors="coerce")
    d = d[(d["age"] >= 19) & d["phq"].between(0, 27)].copy()
    d["y"] = (d["phq"] >= 10).astype(int)
    d["female"] = (pd.to_numeric(d["sex"], errors="coerce") == 2).astype(int)
    for v, _, _, _, logv in VARS:
        x = pd.to_numeric(d[v], errors="coerce")
        d[v] = np.log(x.clip(lower=1e-3)) if logv else x
    y = d["y"].to_numpy()
    print(f"대상 {len(d)}명, PHQ-9 10점 이상 {int(y.sum())}명 ({y.mean() * 100:.1f}%)")

    # 1) 항목별 보정 연관성
    assoc = adjusted_assoc(d)

    # 2) 선택 안정성 (L1 로지스틱, 부트스트랩 100회)
    feats = [v for v, *_ in VARS]
    Xall = d[feats + ["age", "female"]].to_numpy(float)
    rng = np.random.default_rng(SEED)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    hits = np.zeros(len(feats))
    B = 100
    l1 = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                   ("lr", LogisticRegression(penalty="l1", solver="liblinear", C=0.03, class_weight="balanced", max_iter=3000))])
    for _ in range(B):
        idx = np.r_[rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]
        l1.fit(Xall[idx], y[idx])
        hits += np.abs(l1.named_steps["lr"].coef_[0][:len(feats)]) > 1e-6
    stability = hits / B

    # 3) 예측 성능
    base_auc = cv_auc(d[["age", "female"]].to_numpy(float), y, 5, SEED)
    full_auc = cv_auc(Xall, y, 5, SEED)
    print(f"AUC 나이·성별 {np.mean(base_auc):.3f} / 검진 항목 포함 {np.mean(full_auc):.3f}")

    # 4) 데이터 증가 시나리오
    sizes = [500, 1000, 2000, 3500, len(d)]
    growth = []
    for n in sizes:
        disc, aucs = [], []
        reps = 1 if n == len(d) else 20
        for r in range(reps):
            if n == len(d):
                sub = d
            else:          # 양성 비율을 유지하며 n명을 무작위로 뽑아요
                rr = np.random.default_rng(SEED + r)
                k_pos = int(round(len(pos) * n / len(d)))
                pick = np.r_[rr.choice(pos, k_pos, replace=False), rr.choice(neg, n - k_pos, replace=False)]
                sub = d.iloc[pick]
            a = adjusted_assoc(sub)
            disc.append(sum(1 for o in a if o and o["q"] < 0.05))
            ys = sub["y"].to_numpy()
            if ys.sum() >= 10:
                cv = StratifiedKFold(5, shuffle=True, random_state=SEED + r)
                pr = cross_val_predict(model(), sub[feats + ["age", "female"]].to_numpy(float), ys, cv=cv, method="predict_proba")[:, 1]
                aucs.append(roc_auc_score(ys, pr))
        growth.append({"n": int(n), "n_pos": int(round(y.mean() * n)), "discoveries_mean": float(np.mean(disc)),
                       "discoveries_sd": float(np.std(disc)), "auc_mean": float(np.mean(aucs)), "auc_sd": float(np.std(aucs)),
                       "reps": reps})
        print(f"  n={n}: 발견 {np.mean(disc):.1f}개, AUC {np.mean(aucs):.3f}")

    rows = []
    for (v, label, unit, group, logv), a, s in zip(VARS, assoc, stability):
        if not a:
            continue
        sub = d[[v, "y"]].dropna()
        orr = math.exp(a["beta"])
        lo, hi = math.exp(a["beta"] - 1.96 * a["se"]), math.exp(a["beta"] + 1.96 * a["se"])
        if a["q"] < 0.05 and s >= 0.6:
            tier = "유망 후보"
        elif a["q"] < 0.05 or s >= 0.5:
            tier = "검토 필요"
        else:
            tier = "근거 약함"
        raw_v = pd.to_numeric(raw.loc[sub.index, v], errors="coerce")
        rows.append({"var": v, "label": label, "unit": unit, "group": group, "log": logv, "n": a["n"], "n_pos": a["n_pos"],
                     "mean_pos": round(float(raw_v[sub["y"] == 1].mean()), 3), "mean_neg": round(float(raw_v[sub["y"] == 0].mean()), 3),
                     "or": round(orr, 3), "or_lo": round(lo, 3), "or_hi": round(hi, 3), "p": a["p"], "q": a["q"],
                     "stability": round(float(s), 2), "tier": tier})
    rows.sort(key=lambda r: (["유망 후보", "검토 필요", "근거 약함"].index(r["tier"]), r["q"]))

    out = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "source": "국민건강영양조사 2024 원시자료 (질병관리청)",
        "label": "PHQ-9 총점 10점 이상 (우울 증상 선별 양성, 진단 아님)",
        "population": "만 19세 이상 PHQ-9 응답자",
        "n": int(len(d)), "n_pos": int(y.sum()), "prevalence": round(float(y.mean()), 4),
        "n_vars": len(rows),
        "method": {"assoc": "항목별 나이·성별 보정 로지스틱 회귀, 1 SD당 오즈비, BH-FDR",
                   "stability": f"부트스트랩 {B}회 L1 로지스틱(모든 항목+나이·성별), 선택 비율",
                   "tier": "유망 후보: q<0.05 그리고 안정성≥0.6 / 검토 필요: 둘 중 하나 / 근거 약함: 둘 다 아님",
                   "model": "중앙값 대체+결측 표시 → 표준화 → L2 로지스틱(균형 가중), 층화 5겹 × 5회"},
        "auc": {"base_mean": float(np.mean(base_auc)), "base_sd": float(np.std(base_auc)),
                "full_mean": float(np.mean(full_auc)), "full_sd": float(np.std(full_auc))},
        "variables": rows, "growth": growth,
        "limits": ["PHQ-9는 선별 설문이며 임상 진단이 아님", "단면 조사라 연관성만 알 수 있고 인과관계는 알 수 없음",
                   "흡연·음주·만성질환·복용 약·소득 등은 보정하지 않음 (나이·성별만 보정)",
                   "조사 가중치를 적용하지 않아 전 국민 추정치가 아님", "폐기능·비타민 D·부갑상선호르몬 등은 일부 대상자만 측정"],
    }
    (root / "research_evidence.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장:", root / "research_evidence.json")
    for r in rows[:15]:
        print(f"  [{r['tier']}] {r['label']}: OR {r['or']:.2f} ({r['or_lo']:.2f}-{r['or_hi']:.2f}) q={r['q']:.4f} 안정성 {r['stability']:.2f}")


if __name__ == "__main__":
    main()
