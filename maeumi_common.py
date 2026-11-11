"""환자용·의사용·관리자 페이지가 함께 쓰는 경로와 관리자 설정."""
import json
import os

import streamlit as st

SHARED_DIR = os.environ.get("MAEUMI_SHARED_DIR") or os.path.join(os.path.expanduser("~"), "maeumi_shared")
os.makedirs(SHARED_DIR, exist_ok=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 환자 기록 파일 (관리자 리셋·백업 대상). 관리자 설정 파일은 리셋해도 남아요.
DATA_FILES = ["patient_profile.json", "alerts.json", "appointments.json", "checkins.json", "garden.json",
              "bio_report.json", "diagnosis_report.json", "consultation_req.txt"]
SETTINGS_NAME = "admin_settings.json"
SEEN_FILE = os.path.join(BASE_DIR, "seen_events.json")       # 환자 앱의 '확인한 알림' 기록

MOD_LABEL = {"eeg": "EEG", "metabolites": "대사체", "cytokine": "사이토카인", "cortisol": "코르티솔"}
DEFAULT_SETTINGS = {
    "doctor_login": True,                 # 의료진 로그인 화면 표시
    "doctor_id": "doctor01",
    "doctor_name": "홍길동",
    "doctor_dept": "정신건강의학과",
    "fusion_default": ["eeg", "metabolites", "cytokine", "cortisol"],   # 통합 점수에 기본으로 포함할 검사
    "patient_tools": False,               # 환자 앱 사이드바의 시연 도구 (다른 환자 기록이 보이므로 기본 숨김)
    "show_risk_debug": True,              # 환자 대화 아래 '위험도: ...' 표시
}


def shared_path(name):
    return os.path.join(SHARED_DIR, name)


def load_settings():
    try:
        with open(shared_path(SETTINGS_NAME), "r", encoding="utf-8") as f:
            saved = json.load(f)
    except Exception:
        saved = {}
    out = dict(DEFAULT_SETTINGS)
    out.update({k: v for k, v in saved.items() if k in DEFAULT_SETTINGS})
    return out


def save_settings(settings):
    clean = {k: settings[k] for k in DEFAULT_SETTINGS if k in settings}
    with open(shared_path(SETTINGS_NAME), "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)


def get_secret(name):
    """Streamlit Cloud Secrets → 환경변수(.env) 순서로 읽어요."""
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name)
