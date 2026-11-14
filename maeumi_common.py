"""환자용·의사용·연구·관리자 페이지가 함께 쓰는 경로, 관리자 설정, 환자 기록 도우미."""
import csv
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta

import streamlit as st

SHARED_DIR = os.environ.get("MAEUMI_SHARED_DIR") or os.path.join(os.path.expanduser("~"), "maeumi_shared")
os.makedirs(SHARED_DIR, exist_ok=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LAB_FILE = "lab_results.json"        # 환자별 검사 기록 {환자ID: [검사 회차, ...]}
DX_FILE = "clinical_dx.json"         # 의사가 기록한 임상 진단 {환자ID: {...}}
# 환자 기록 파일 (관리자 리셋·백업 대상). 관리자 설정 파일은 리셋해도 남아요.
DATA_FILES = ["patient_profile.json", "alerts.json", "appointments.json", "checkins.json", "garden.json",
              "bio_report.json", "diagnosis_report.json", "consultation_req.txt", LAB_FILE, DX_FILE]
SETTINGS_NAME = "admin_settings.json"
SEEN_FILE = os.path.join(BASE_DIR, "seen_events.json")       # 환자 앱의 '확인한 알림' 기록
CONSENT_VERSION = "2026-11 v1"

MOD_LABEL = {"eeg": "EEG", "metabolites": "대사체", "cytokine": "사이토카인", "cortisol": "코르티솔"}
DEFAULT_SETTINGS = {
    "doctor_login": True,                 # 의료진 로그인 화면 표시
    "doctor_id": "doctor01",
    "doctor_name": "홍길동",
    "doctor_dept": "정신건강의학과",
    "fusion_default": ["eeg", "metabolites", "cytokine", "cortisol"],   # 통합 점수에 기본으로 포함할 검사
    "patient_tools": False,               # 환자 앱 사이드바의 시연 도구 (다른 환자 기록이 보이므로 기본 숨김)
    "show_risk_debug": True,              # 환자 대화 아래 '위험도: ...' 표시
    "auto_seed_demo": True,               # 환자가 한 명도 없으면 시연 환자 6명을 자동으로 만들기
}


def shared_path(name):
    return os.path.join(SHARED_DIR, name)


def read_shared(name, default):
    try:
        with open(shared_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_shared(name, data):
    with open(shared_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_settings():
    saved = read_shared(SETTINGS_NAME, {})
    out = dict(DEFAULT_SETTINGS)
    out.update({k: v for k, v in (saved or {}).items() if k in DEFAULT_SETTINGS})
    return out


def save_settings(settings):
    write_shared(SETTINGS_NAME, {k: settings[k] for k in DEFAULT_SETTINGS if k in settings})


def get_secret(name):
    """Streamlit Cloud Secrets → 환경변수(.env) 순서로 읽어요."""
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name)


def patient_id(name):
    """환자 앱과 같은 방식: 이름으로 만든 ID (같은 이름 = 같은 환자)"""
    return "P-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:6]


def research_code(pid):
    """연구 데이터에서 쓰는 가명 코드 (이름·환자 ID를 노출하지 않아요)"""
    return "R-" + hashlib.sha256(("maeumi-research:" + pid).encode("utf-8")).hexdigest()[:8].upper()


# ---------------------------------------------------------------- 시연 환자 6명
# (이름, 임상 진단, 나이, 성별, 키, 몸무게, 연구 동의, HAM-D, PHQ-9 기록) — demo_cases.csv의 행 순서와 같아요
DEMO_PATIENTS = [
    ("예시환자 A", "MDD", 34, "여성", 161, 52, True, 21, [11, 15, 18]),
    ("예시환자 B", "MDD", 47, "남성", 173, 78, True, 19, [13, 16, 17]),
    ("예시환자 C", "MDD", 29, "여성", 165, 57, False, 24, [14, 19, 21]),
    ("예시환자 D", "비MDD", 38, "남성", 176, 71, True, 4, [3, 4, 2]),
    ("예시환자 E", "비MDD", 52, "여성", 158, 55, True, 3, [2, 3, 3]),
    ("예시환자 F", "비MDD", 26, "남성", 180, 74, False, 2, [1, 2, 1]),
]
PHQ_BANDS = [(0, 4, "거의 없음"), (5, 9, "가벼운 수준"), (10, 14, "중간 수준"), (15, 19, "다소 심한 수준"), (20, 27, "심한 수준")]


def _phq_answers(total):
    ans, left = [0] * 9, total
    for i in range(9):
        if i == 8:
            break              # 9번(자해 생각) 문항은 0점으로 둬요
        take = min(3, left)
        ans[i], left = take, left - take
    return ans


def seed_demo_patients():
    """시연 환자 6명을 만들어요: 프로필(동의 포함) · 검사 기록 1회 · 임상 진단 · PHQ-9 3회. 이미 있는 환자는 건너뛰어요."""
    path = os.path.join(BASE_DIR, "demo_data", "demo_cases.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    profiles = read_shared("patient_profile.json", {}) or {}
    labs = read_shared(LAB_FILE, {}) or {}
    dx = read_shared(DX_FILE, {}) or {}
    checkins = read_shared("checkins.json", []) or []
    now = datetime.now()
    made = 0
    for k, (name, diag, age, sex, h, w, research, hamd, phqs) in enumerate(DEMO_PATIENTS):
        pid = patient_id(name)
        if pid in profiles:
            continue
        stamp = (now - timedelta(minutes=10 * (k + 1))).strftime("%Y-%m-%d %H:%M:%S")   # A가 가장 최근 → 목록 맨 위
        profiles[pid] = {"name": name, "age": age, "sex": sex, "height_cm": h, "weight_kg": w, "updated": stamp, "demo": True,
                         "consent": {"service": True, "research": research, "version": CONSENT_VERSION, "time": stamp}}
        row = rows[k]
        values = {c: float(v) for c, v in row.items() if c not in ("사례명", "구분") and v not in ("", None)}
        labs[pid] = [{"id": uuid.uuid4().hex[:8], "date": (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                      "label": "1회차 검사", "group": "", "file": "demo_cases.csv", "values": values, "demo": True}]
        dx[pid] = {"dx": diag, "hamd": hamd, "updated": stamp, "demo": True}
        for j, total in enumerate(phqs):
            t = (now - timedelta(days=14 * (len(phqs) - 1 - j))).strftime("%Y-%m-%d %H:%M:%S")
            sev = next(lbl for lo, hi, lbl in PHQ_BANDS if lo <= total <= hi)
            checkins.append({"patient_id": pid, "patient_name": name, "time": t, "total": total, "severity": sev,
                             "item9": 0, "answers": _phq_answers(total), "care_step": "doctor" if total >= 10 else "self",
                             "demo": True})
        made += 1
    write_shared("patient_profile.json", profiles)
    write_shared(LAB_FILE, labs)
    write_shared(DX_FILE, dx)
    write_shared("checkins.json", sorted(checkins, key=lambda c: c.get("time", "")))
    return made


def research_dataset():
    """연구 데이터: 연구 활용에 동의 + 임상 진단 기록 + 검사 기록이 있는 환자만, 가명 코드로 (이름·대화 제외)"""
    profiles = read_shared("patient_profile.json", {}) or {}
    labs = read_shared(LAB_FILE, {}) or {}
    dx = read_shared(DX_FILE, {}) or {}
    rows, excluded = [], {"no_consent": 0, "no_dx": 0, "no_lab": 0}
    for pid, prof in profiles.items():
        if not (prof.get("consent") or {}).get("research"):
            excluded["no_consent"] += 1
            continue
        d = (dx.get(pid) or {}).get("dx")
        if d not in ("MDD", "비MDD"):
            excluded["no_dx"] += 1
            continue
        if not labs.get(pid):
            excluded["no_lab"] += 1
            continue
        age = prof.get("age")
        rows.append({"code": research_code(pid), "dx": d, "hamd": (dx.get(pid) or {}).get("hamd"),
                     "age_group": f"{(age // 10) * 10}대" if age else "-", "sex": prof.get("sex") or "-",
                     "n_labs": len(labs[pid]), "demo": bool(prof.get("demo"))})
    return rows, excluded
