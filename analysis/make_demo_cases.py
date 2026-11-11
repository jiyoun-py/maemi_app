"""시연용 '가상 조합 사례' 파일(demo_data/demo_cases.csv)을 만들어요.

한 사람이 4종 검사를 모두 받은 자료가 없어서, 데이터마다 MDD군·건강대조군에서 한 명씩 골라 값을 조합해요.
- EEG·대사체·코르티솔: 실제 데이터의 한 사람 값 (코르티솔 데이터는 시뮬레이션)
- 사이토카인: 개인 값이 없어 논문 보고 평균±SD를 따르는 로그정규분포에서 뽑은 값
주의: 모델이 학습한 사람들의 값이라 실제 새 환자보다 잘 맞혀 보여요. 화면에는 '가상 조합 사례'로만 소개하세요.

실행: venv\\Scripts\\python.exe analysis\\make_demo_cases.py --data "<데이터 관리 폴더 경로>"
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
N_EACH = 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    d = Path(ap.parse_args().data)
    root = Path(__file__).resolve().parent.parent
    ev = json.loads((root / "model_evidence.json").read_text(encoding="utf-8"))["modalities"]
    rng = np.random.default_rng(SEED)

    eeg = pd.read_csv(d / "machinelearning_data_EEG.csv")
    eeg_y = (eeg["specific.disorder"] == "Depressive disorder").to_numpy()

    raw = pd.read_csv(d / "MSdata_ST000062_AN000100.txt", sep="\t", header=None, dtype=str, encoding_errors="replace")
    groups = raw.iloc[1, 1:].astype(str).str.strip()
    body = raw.iloc[2:]
    body = body[body[0].notna() & (body[0].astype(str).str.strip() != "")]
    valid = groups.str.contains("Group")
    met = body.loc[:, [0] + list(groups.index[valid])].set_index(0).astype(float).T
    met.columns = [str(c).strip() for c in met.columns]
    met = met.loc[:, ~met.columns.duplicated()].reset_index(drop=True)
    met_y = groups[valid].str.contains("Score 50").to_numpy()

    cort = pd.read_csv(d / "MDD_Simulation_Dataset.csv")
    cort_y = (cort["Diagnosis"] == "MDD").to_numpy()
    cyto = ev["cytokine"]["model"]

    def lognormal(mean, sd):
        s2 = np.log(1 + (sd / mean) ** 2)
        return float(rng.lognormal(np.log(mean) - s2 / 2, np.sqrt(s2)))

    rows = []
    for is_mdd, label in ((True, "MDD"), (False, "건강대조군")):
        e_idx = rng.choice(np.where(eeg_y == is_mdd)[0], N_EACH, replace=False)
        m_idx = rng.choice(np.where(met_y == is_mdd)[0], N_EACH, replace=False)
        c_idx = rng.choice(np.where(cort_y == is_mdd)[0], N_EACH, replace=False)
        for k in range(N_EACH):
            row = {"사례명": f"{label} 사례 {k + 1}", "구분": label}
            row.update({f: round(float(eeg.iloc[e_idx[k]][f]), 5) for f in ev["eeg"]["model"]["features"]})
            row.update({f: round(float(met.iloc[m_idx[k]][f]), 4) for f in ev["metabolites"]["model"]["features"]})
            mu, sd = (cyto["mu_mdd"], cyto["sd_mdd"]) if is_mdd else (cyto["mu_ctrl"], cyto["sd_ctrl"])
            row.update({f: round(lognormal(m, s), 3) for f, m, s in zip(cyto["features"], mu, sd)})
            row["Cortisol"] = float(cort.iloc[c_idx[k]]["Cortisol"])
            rows.append(row)
    out = root / "demo_data" / "demo_cases.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"{len(rows)}개 사례를 {out}에 저장했어요.")


if __name__ == "__main__":
    main()
