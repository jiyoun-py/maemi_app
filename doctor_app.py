from collections import defaultdict
from datetime import datetime, date, timedelta
import calendar as pycal
import html
import json
import math
import os
import uuid

import numpy as np
import pandas as pd
import streamlit as st

from maeumi_common import DX_FILE, LAB_FILE, MOD_LABEL, load_settings, seed_demo_patients

st.set_page_config(
    page_title="MDD Clinical Decision Support System",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =====================================================================
# 디자인 (환자용 플랫폼과 같은 블루 톤, 의료기관 프로그램에 맞게 정돈)
# =====================================================================
DOC_CSS = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
:root{--bg:#F4F6FB;--line:#E2E8F3;--text:#0F172A;--muted:#64748B;--primary:#4F6BD3;--primary-dark:#2F3F8F;
      --soft:#EEF2FF;--ok:#2F9E8F;--warn:#F5A524;--danger:#E5484D;color-scheme:light;}
.stApp, .stApp p, .stApp label, .stApp li, .stApp button, .stApp input, .stApp textarea{
  font-family:'Pretendard','Noto Sans KR','Malgun Gothic',-apple-system,sans-serif !important;}
.stApp{background:var(--bg);}
.block-container, [data-testid="stMainBlockContainer"]{max-width:1560px !important;padding:1.1rem 1.6rem 3rem !important;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer{display:none !important;}
.stApp [data-testid="stMarkdownContainer"] p{color:var(--text);}
[data-testid="stHorizontalBlock"]{gap:.9rem !important;}

/* ---- 공통 카드 ---- */
[class*="st-key-card_"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;
  box-shadow:0 1px 3px rgba(15,23,42,.05);margin-bottom:12px;}
.panel, .quad{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;
  box-shadow:0 1px 3px rgba(15,23,42,.05);margin-bottom:14px;}
.panel-title{display:flex;justify-content:space-between;align-items:baseline;font-weight:800;font-size:.95rem;
  color:var(--text);margin-bottom:8px;letter-spacing:-.01em;}
.panel-sub{font-size:.72rem;color:var(--muted);font-weight:500;}
.sec-label{font-size:.7rem;font-weight:800;letter-spacing:.09em;color:var(--muted);margin:10px 2px 8px;}
.card-label{font-size:.7rem;font-weight:800;letter-spacing:.07em;color:var(--muted);margin-bottom:8px;}
.empty{font-size:.82rem;color:var(--muted);padding:26px 0;text-align:center;}

/* ---- 칩 ---- */
.chip{display:inline-block;font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:999px;white-space:nowrap;line-height:1.4;}
.chip-ok{background:#DFF3F0;color:#17695E;}
.chip-warn{background:#FEF3C7;color:#92400E;}
.chip-danger{background:#FEE2E2;color:#991B1B;}
.chip-info{background:#E8EEFF;color:#2F3F8F;}
.chip-muted{background:#EEF2F7;color:#475569;}

/* ---- 상단 상태 줄 ---- */
.strip{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);
  border-radius:12px;padding:9px 14px;margin-bottom:14px;font-size:.82rem;color:#334155;}
.strip-l{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.strip-r{color:var(--muted);font-size:.76rem;font-feature-settings:"tnum";}

/* ---- 바이오마커 4분할 ---- */
.quad-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
.quad-name{font-weight:800;font-size:1.08rem;letter-spacing:-.01em;color:var(--text);}
.quad-body{display:flex;gap:16px;align-items:center;}
.quad-gauge{flex:0 0 190px;}
.quad-gauge svg, .fusion-gauge svg{width:100%;height:auto;display:block;}
.quad-detail{flex:1;min-width:0;}
.dhead{font-size:.66rem;font-weight:800;letter-spacing:.07em;color:var(--muted);margin-bottom:4px;}
.drow{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #EEF2F8;
  font-size:.84rem;color:#334155;}
.drow:last-child{border-bottom:none;}
.mono{font-feature-settings:"tnum";color:var(--text);font-weight:700;}
@keyframes sweep{from{stroke-dasharray:0 100}to{stroke-dasharray:100 100}}

/* ---- 환자 프로필 ---- */
.pf{display:flex;align-items:center;gap:12px;}
.pf-av{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,#4F6BD3,#7C93E8);color:#fff;font-weight:800;
  font-size:1.15rem;display:flex;align-items:center;justify-content:center;flex:none;}
.pf-name{font-weight:800;font-size:1.05rem;color:var(--text);line-height:1.2;}
.pf-sub{font-size:.78rem;color:var(--muted);margin-top:2px;}
.pf-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:12px;}
.pf-grid div{background:#F6F8FD;border-radius:10px;padding:7px 9px;}
.pf-grid span{display:block;font-size:.66rem;color:var(--muted);font-weight:700;}
.pf-grid b{font-size:.92rem;color:var(--text);font-feature-settings:"tnum";}
.pf-chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;}

/* ---- 상담 요청 ---- */
.req{border-left:4px solid var(--warn);background:#FFFBEB;border-radius:10px;padding:10px 12px;margin-bottom:8px;}
.req.urgent{border-left-color:var(--danger);background:#FEF2F2;}
.req-t{font-weight:800;font-size:.86rem;color:var(--text);}
.req-s{font-size:.78rem;color:#475569;margin-top:3px;line-height:1.5;}
.req-empty{font-size:.82rem;color:var(--muted);padding:6px 2px;}

/* ---- 달력 ---- */
.cal-month{text-align:center;font-weight:800;font-size:.95rem;color:var(--text);padding-top:6px;}
.cal-head{display:grid;grid-template-columns:repeat(7,1fr);text-align:center;font-size:.66rem;color:var(--muted);font-weight:800;margin:6px 0 4px;}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;}
.cal-day{height:38px;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:9px;
  font-size:.8rem;color:var(--text);font-feature-settings:"tnum";}
.cal-day.other{color:#B8C2D6;}
.cal-day.today{box-shadow:inset 0 0 0 1.5px var(--primary);}
.cal-day.sel{background:var(--primary);color:#fff;font-weight:800;}
.dots{display:flex;gap:2px;height:5px;margin-top:2px;}
.dot{width:5px;height:5px;border-radius:50%;}
.dot-conf{background:#4F6BD3;} .dot-req{background:#F5A524;} .dot-urg{background:#E5484D;} .dot-done{background:#B8C2D6;}
.cal-day.sel .dot{background:#fff;}
.cal-legend{display:flex;gap:10px;flex-wrap:wrap;font-size:.68rem;color:var(--muted);margin-top:8px;}
.cal-legend i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;}

/* ---- 진료 기록 표 ---- */
.rec-wrap{max-height:250px;overflow:auto;}
.rec{width:100%;border-collapse:collapse;font-size:.8rem;}
.rec th{text-align:left;font-size:.66rem;color:var(--muted);padding:6px 4px;border-bottom:1px solid var(--line);font-weight:800;letter-spacing:.05em;}
.rec td{padding:8px 4px;border-bottom:1px solid #EEF2F8;color:#334155;vertical-align:top;}
.rec td.d{font-feature-settings:"tnum";white-space:nowrap;color:var(--text);font-weight:600;}

/* ---- 융합 진단 / 통계 ---- */
.fusion-top{display:flex;gap:16px;align-items:center;}
.fusion-gauge{flex:0 0 230px;}
.fusion-info{flex:1;min-width:0;}
.fusion-label{font-weight:800;font-size:1.02rem;line-height:1.35;color:var(--text);margin:4px 0 6px;}
.comment{background:#F8FAFF;border-radius:10px;padding:12px 14px;font-size:.86rem;line-height:1.7;color:#1E293B;margin:10px 0 12px;}
.stat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;}
.stat{background:#F6F8FD;border-radius:10px;padding:8px 10px;}
.stat span{display:block;font-size:.66rem;color:var(--muted);font-weight:700;}
.stat b{font-size:1.12rem;color:var(--text);font-feature-settings:"tnum";}
.leg{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.72rem;color:#475569;margin-top:6px;}
.leg i{display:inline-block;width:12px;height:3px;border-radius:2px;margin-right:5px;vertical-align:middle;}
.mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 12px;}
.mini-title{font-size:.72rem;font-weight:800;color:#475569;margin-bottom:2px;}
.factor{display:flex;align-items:center;gap:8px;margin:7px 0;font-size:.8rem;color:var(--text);}
.f-name{flex:0 0 40%;line-height:1.3;}
.f-bar{flex:1;height:8px;background:#EEF2FA;border-radius:999px;overflow:hidden;}
.f-bar i{display:block;height:100%;border-radius:999px;}
.f-pct{flex:0 0 36px;text-align:right;font-weight:800;font-size:.78rem;font-feature-settings:"tnum";}
.perf{width:100%;border-collapse:collapse;font-size:.78rem;margin-top:8px;}
.perf th{text-align:right;font-size:.66rem;color:var(--muted);padding:5px 4px;border-bottom:1px solid var(--line);font-weight:800;}
.perf th:first-child, .perf td:first-child{text-align:left;}
.perf td{text-align:right;padding:6px 4px;border-bottom:1px solid #EEF2F8;color:#334155;font-feature-settings:"tnum";}
.perf tr.hl td{font-weight:800;color:var(--text);background:#F6F8FD;}
.perf tr.avg td{font-weight:700;color:#2F3F8F;background:#EEF2FF;}
.drow b.mono{white-space:nowrap;}
.st-key-fusion_mods button[aria-pressed="true"]{background:var(--primary) !important;border-color:var(--primary) !important;}
.st-key-fusion_mods button[aria-pressed="true"] *{color:#fff !important;}
.st-key-fusion_mods button[aria-pressed="false"]{background:#fff !important;border-style:dashed !important;}
.st-key-fusion_mods button[aria-pressed="false"] *{color:#94A3B8 !important;}
.case-nav{display:flex;align-items:center;justify-content:center;gap:10px;height:40px;background:#fff;
  border:1px solid var(--line);border-radius:10px;font-size:.95rem;}
.foot{font-size:.68rem;color:#94A3B8;margin-top:6px;}
.stack{display:flex;height:14px;border-radius:999px;overflow:hidden;background:#EEF2FA;margin:6px 0 8px;}
.stack span{display:block;height:100%;}

/* ---- 버튼 / 입력 위젯 ---- */
.stButton > button, [data-testid="stBaseButton-secondary"]{border-radius:10px;border:1px solid var(--line);background:#fff;
  color:var(--text);font-weight:600;min-height:38px;}
.stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover{border-color:var(--primary);color:var(--primary);}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"]{background:var(--primary);color:#fff;border:none;
  box-shadow:0 2px 6px rgba(79,107,211,.25);}
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover{background:var(--primary-dark);color:#fff;}
.stButton > button p, [data-testid^="stBaseButton"] p{color:inherit !important;}
.stButton > button[kind="primary"] p, [data-testid="stBaseButton-primary"] p{color:#fff !important;}
textarea, [data-baseweb="textarea"], [data-baseweb="base-input"]{background:#fff !important;color:var(--text) !important;border-radius:10px !important;}
[data-testid="stTextArea"] textarea{border:1px solid var(--line) !important;font-size:.86rem;line-height:1.6;}
[data-testid="stDateInput"] input, [data-baseweb="input"] input{background:#fff !important;color:var(--text) !important;}
[data-testid="stFileUploaderDropzone"]{background:#F8FAFF !important;border:1.5px dashed #C3CFEE !important;border-radius:12px !important;}
[data-testid="stFileUploaderDropzone"] *{color:#475569 !important;}
[data-testid="stFileUploaderDropzone"] button{background:#fff !important;border:1px solid var(--line) !important;color:var(--text) !important;}
[data-testid="stFileUploaderFile"] *{color:var(--text) !important;}
.stApp [data-testid="stExpander"]{background:#fff !important;border:1px solid var(--line) !important;border-radius:12px !important;}
.stApp [data-testid="stExpander"] *{color:var(--text) !important;}
.stApp [data-testid="stAlert"] *{color:#1E293B !important;}
"""
st.markdown("<style>" + DOC_CSS + "</style>", unsafe_allow_html=True)


# 밝은 테마가 적용되지 않았을 때를 대비해, 환자용 앱과 같은 방식으로 한 번 더 확인해요
def apply_light_theme_runtime():
    try:
        for k, v in {"base": "light", "primaryColor": "#4F6BD3", "backgroundColor": "#F4F6FB",
                     "secondaryBackgroundColor": "#FFFFFF", "textColor": "#0F172A"}.items():
            st._config.set_option(f"theme.{k}", v)
    except Exception:
        pass


if st.get_option("theme.base") != "light" or st.session_state.get("theme_pending"):
    if not st.session_state.get("theme_pending"):
        apply_light_theme_runtime()
        st.session_state.theme_pending = True
    st.warning("화면 색 설정을 적용했어요. 브라우저를 새로고침(F5) 해 주세요. 새로고침해도 이 안내가 계속 나오면 "
               "`.streamlit/config.toml`이 `streamlit run`을 실행한 폴더에 있는지 확인해 주세요.",
               icon=":material/palette:")


# =====================================================================
# 의료진 로그인 화면 (시연용): 실제 진료 시스템처럼 보이되, ID·비밀번호가 미리 입력돼 있어 '로그인'만 누르면 들어가요.
# 표시 내용과 켜기/끄기는 관리자 페이지(/admin)의 시연 설정에서 바꿔요. 실제 인증은 하지 않아요.
# =====================================================================
SETTINGS = load_settings()
if SETTINGS["doctor_login"] and not st.session_state.get("doctor_ok"):
    st.markdown("""<style>
    .login-brand{display:flex;align-items:center;gap:12px;margin-bottom:6px;}
    .login-logo{width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,#4F6BD3,#2F3F8F);
      color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.4rem;}
    .login-title{font-weight:800;font-size:1.25rem;color:#0F172A;line-height:1.2;}
    .login-sub{font-size:.8rem;color:#64748B;}
    .login-foot{font-size:.72rem;color:#94A3B8;margin-top:10px;text-align:center;}
    </style>""", unsafe_allow_html=True)
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
    _l, _c, _r = st.columns([1, 1.1, 1])
    with _c:
        with st.container(key="card_login"):
            st.markdown("<div class='login-brand'><div class='login-logo'>🩺</div><div>"
                        "<div class='login-title'>마음이 CDSS</div>"
                        f"<div class='login-sub'>{html.escape(SETTINGS['doctor_dept'])} 임상 의사결정 지원 시스템</div></div></div>",
                        unsafe_allow_html=True)
            with st.form("doctor_login"):
                st.text_input("의료진 ID", value=SETTINGS["doctor_id"])
                st.text_input("비밀번호", value="demo-password", type="password")
                if st.form_submit_button("로그인", type="primary", use_container_width=True):
                    st.session_state.doctor_ok = True
                    st.rerun()
            st.markdown("<div class='login-foot'>시연용 계정이 입력되어 있습니다 · 로그인을 눌러 주세요</div>",
                        unsafe_allow_html=True)
    st.stop()


def logout():
    st.session_state.doctor_ok = False

# =====================================================================
# [연동] 환자용 플랫폼(마음이)과 공유하는 폴더
#  - 환자용 앱과 같은 폴더를 가리켜야 해요. 기본값: 내 계정 폴더의 maeumi_shared
#  - 다른 위치를 쓰려면 환경변수 MAEUMI_SHARED_DIR 에 경로를 지정
# =====================================================================
SHARED_DIR = os.environ.get("MAEUMI_SHARED_DIR") or os.path.join(os.path.expanduser("~"), "maeumi_shared")
os.makedirs(SHARED_DIR, exist_ok=True)
REQ_FILE = os.path.join(SHARED_DIR, "consultation_req.txt")


def _path(name):
    return os.path.join(SHARED_DIR, name)


def read_json(name, default):
    try:
        with open(_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(name, data):
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_patients():
    """환자 앱을 사용한 모든 환자 [(환자 ID, 프로필)], 최근에 사용한 순서"""
    profiles = read_json("patient_profile.json", {})
    if not isinstance(profiles, dict):
        return []
    return sorted(profiles.items(), key=lambda kv: kv[1].get("updated", ""), reverse=True)


def link_signature():
    """환자 앱이 쓰는 파일의 상태. 바뀌면 화면을 새로 고쳐요. (프로필의 '최근 사용 시각'만 바뀐 경우는 제외)"""
    parts = []
    for name in ("consultation_req.txt", "alerts.json", "appointments.json", "checkins.json", "bio_report.json"):
        try:
            stt = os.stat(_path(name))
            parts.append((name, int(stt.st_mtime * 1000), stt.st_size))
        except OSError:
            parts.append((name, 0, 0))
    profiles = read_json("patient_profile.json", {})
    if isinstance(profiles, dict):
        parts.append(sorted((k, json.dumps({f: v for f, v in p.items() if f != "updated"}, sort_keys=True, ensure_ascii=False))
                            for k, p in profiles.items()))
    return str(parts)


def confirm_appointment(req, pid):
    """환자가 요청한 상담을 수락 -> 환자 앱에 '확정'으로 표시. 요청 줄로 어느 환자의 예약인지 찾아요."""
    appts = read_json("appointments.json", [])
    open_ = [a for a in appts if a.get("status") != "confirmed"]
    match = next((a for a in open_ if a.get("req_line") == req["line"]), None)
    if match is None:
        match = next((a for a in open_ if a.get("date") == req["date"] and a.get("time") == req["time"]
                      and (not pid or a.get("patient_id") == pid)), None)
    if match:
        match["status"] = "confirmed"
        match["confirmed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        write_json("appointments.json", appts)
    return match


def add_doctor_appointment(date_str, time_str, kind, pid, pname):
    """의료진이 직접 등록한 일정 -> 환자 앱의 '내 예약'에 표시"""
    appts = read_json("appointments.json", [])
    appts.append({"id": str(uuid.uuid4())[:8], "patient_id": pid, "patient_name": pname, "date": date_str, "time": time_str,
                  "kind": kind, "source": "의료진 등록", "priority": "normal", "status": "confirmed",
                  "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    write_json("appointments.json", appts)


def ack_alert(alert_id):
    """긴급 위험 알림 확인 -> 환자 앱에 '의료진이 알림을 확인했어요' 표시"""
    alerts = read_json("alerts.json", [])
    for a in alerts:
        if a.get("id") == alert_id:
            a["status"] = "acknowledged"
            a["ack_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_json("alerts.json", alerts)


# =====================================================================
# 근거 모델: analysis/train_evidence.py가 데이터 4종에서 계산한 연관성·계수·검증 결과를 읽어요.
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_PATH = os.path.join(BASE_DIR, "model_evidence.json")
DEMO_DIR = os.path.join(BASE_DIR, "demo_data")
MOD_ORDER = ["eeg", "metabolites", "cytokine", "cortisol"]


@st.cache_data(show_spinner=False)
def load_evidence(path, mtime):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


try:
    EVIDENCE = load_evidence(EVIDENCE_PATH, os.path.getmtime(EVIDENCE_PATH))
except (OSError, ValueError):
    st.error("model_evidence.json을 읽지 못했습니다. analysis/train_evidence.py를 먼저 실행해 주세요.")
    st.stop()
MODS = EVIDENCE["modalities"]
MODEL_PERF = {MODS[k]["name"]: MODS[k]["perf"] for k in MOD_ORDER if MODS[k].get("perf")}
PERF_COLORS = {"EEG": "#7C93E8", "Metabolites": "#2F9E8F", "Cortisol": "#9A7FD1"}

LOGIT_LIMIT = math.log(99)      # 표시 범위 1~99%: 학습 범위를 벗어난 값이 극단적인 확률을 만들지 않게 제한
COLUMN_ALIASES = {"cortisol_level": "Cortisol", "tnf_alpha": "TNF-α", "tnf-alpha": "TNF-α"}


def logit_to_pct(v):
    return 100.0 / (1.0 + math.exp(-max(min(float(v), LOGIT_LIMIT), -LOGIT_LIMIT)))


def patient_values(df):
    """업로드한 표의 첫 행에서 숫자 값만 {컬럼명: 값}으로 꺼내요."""
    row, values = df.iloc[0], {}
    for col in df.columns:
        num = pd.to_numeric(row[col], errors="coerce")
        if pd.notna(num):
            name = str(col).strip().lstrip("﻿")
            values[COLUMN_ALIASES.get(name.lower(), name)] = float(num)
    return values


def score_modality(mid, values):
    """모달리티 하나를 계산해요. 필요한 값이 빠지면 임의로 채우지 않고 (None, 빠진 항목)을 돌려줘요."""
    m, mdl = MODS[mid], MODS[mid]["model"]
    missing = [f for f in mdl["features"] if f not in values]
    if missing:
        return None, missing
    x = np.array([values[f] for f in mdl["features"]], dtype=float)
    ci = None
    if mdl["type"] == "gaussian_lr":
        mu1, sd1, mu0, sd0 = (np.array(mdl[k], dtype=float) for k in ("mu_mdd", "sd_mdd", "mu_ctrl", "sd_ctrl"))
        z = (x - mu0) / sd0
        range_z = np.minimum(np.abs(z), np.abs((x - mu1) / sd1))
        llr = (np.log(sd0 / sd1) - 0.5 * ((x - mu1) / sd1) ** 2 + 0.5 * z ** 2)
        contrib = llr / len(llr)
        logit = float(contrib.sum())
    else:
        if mdl["transform"] == "log2p1":
            x = np.log2(np.clip(x, 0, None) + 1)
        z = (x - np.array(mdl["mean"], dtype=float)) / np.array(mdl["scale"], dtype=float)
        range_z = np.abs(z)
        contrib = np.array(mdl["coef"], dtype=float) * z
        logit = float(mdl["intercept"] + contrib.sum())
        draws = np.array(mdl["boot"], dtype=float)
        boot_p = 100.0 / (1.0 + np.exp(-np.clip(draws[:, 0] + draws[:, 1:] @ z, -LOGIT_LIMIT, LOGIT_LIMIT)))
        ci = [float(np.percentile(boot_p, 2.5)), float(np.percentile(boot_p, 97.5))]

    prob = round(logit_to_pct(logit), 1)
    order = np.argsort(-np.abs(contrib))
    top = [(mdl["labels"][i], float(contrib[i])) for i in order]
    details = [(lab, f"{'MDD' if c >= 0 else '건강대조군'} 쪽 {abs(c):.2f}") for lab, c in top[:3]]
    outside = int((range_z > 4).sum())
    perf = m.get("perf")
    if m["tier"] == "simulation":
        basis = "시뮬레이션 자료로 만든 시연값이에요"
    elif perf:
        basis = f"근거: {m['n_mdd'] + m['n_control']}명의 자료로 학습, 검증 AUC {perf['auc']:.2f}"
    else:
        basis = "근거: 논문 요약통계 (개인 단위 정확도 검증 없음)"
    parts = [f"95% 구간 {ci[0]:.0f}–{ci[1]:.0f}%"] if ci else ["구간 산출 불가"]
    parts.append(f"AUC {perf['auc']:.2f}" if perf else "AUC 산출 불가")
    parts.append(m["tier_label"])
    if outside:
        parts.append(f"학습 범위 밖 값 {outside}개")
    return {"id": mid, "name": m["name"], "prob": prob, "logit": logit, "ci": ci, "top": top, "details": details,
            "basis": basis, "note": " · ".join(parts)}, []

# =====================================================================
# HTML / SVG 생성 함수 (그래프는 라이브러리 없이 직접 그려서 어떤 환경에서도 선명하게 보여요)
# =====================================================================
def esc(x):
    return html.escape(str(x))


def md(s):
    """HTML 문자열을 화면에 표시 (들여쓰기·빈 줄이 마크다운으로 해석되지 않게 정리)"""
    st.markdown("\n".join(ln.strip() for ln in s.splitlines() if ln.strip()), unsafe_allow_html=True)


def card(key):
    try:
        return st.container(key=f"card_{key}")
    except TypeError:       # 구버전 Streamlit
        return st.container(border=True)


CHIP_BY_WORD = {"고위험": "danger", "소실": "danger", "주의": "warn", "경계": "warn", "저하": "warn",
                "항진": "warn", "특이소견": "warn", "정상": "ok"}


def detail_val(v):
    if v in CHIP_BY_WORD:
        return f"<span class='chip chip-{CHIP_BY_WORD[v]}'>{esc(v)}</span>"
    return f"<b class='mono'>{esc(v)}</b>"


def gauge_svg(p, bands, color, ready=True, label="MDD 확률", big=False):
    """반원 게이지. bands: [(시작, 끝, 색)], p: 0~100"""
    cx, cy, r = 90, 92, 70
    def pt(v, rr=r):
        a = math.radians(180 - v * 1.8)
        return cx + rr * math.cos(a), cy - rr * math.sin(a)
    def arc(v0, v1, rr=r):
        x0, y0 = pt(v0, rr); x1, y1 = pt(v1, rr)
        return f"M{x0:.2f} {y0:.2f} A{rr} {rr} 0 0 1 {x1:.2f} {y1:.2f}"
    out = ['<svg viewBox="0 0 180 122" xmlns="http://www.w3.org/2000/svg">']
    for lo, hi, col in bands:
        out.append(f'<path d="{arc(lo, hi)}" fill="none" stroke="{col}" stroke-width="14"/>')
    for lo, hi, col in bands[1:]:
        x0, y0 = pt(lo, r - 12); x1, y1 = pt(lo, r + 9)
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#FFFFFF" stroke-width="2.5"/>')
    if ready:
        out.append(f'<path d="{arc(0, max(p, 0.4))}" pathLength="100" fill="none" stroke="{color}" stroke-width="14" '
                   f'stroke-linecap="round" style="stroke-dasharray:100 100;animation:sweep 1.1s ease-out;"/>')
        out.append(f'<text x="90" y="{86 if not big else 84}" text-anchor="middle" font-size="{28 if not big else 31}" '
                   f'font-weight="800" fill="#0F172A">{p:.1f}<tspan font-size="14" font-weight="700" fill="#64748B">%</tspan></text>')
    else:
        out.append('<text x="90" y="86" text-anchor="middle" font-size="26" font-weight="800" fill="#B8C2D6">--</text>')
    out.append(f'<text x="90" y="108" text-anchor="middle" font-size="10.5" font-weight="700" fill="#64748B" '
               f'letter-spacing=".5">{esc(label if ready else "측정 대기")}</text>')
    out.append('<text x="14" y="112" font-size="9" fill="#94A3B8">0</text>'
               '<text x="157" y="112" font-size="9" fill="#94A3B8">100</text></svg>')
    return "".join(out)


QUAD_BANDS = [(0, 50, "#DCF1EE"), (50, 100, "#FBE3E4")]
FUSION_BANDS = [(0, 40, "#DCF1EE"), (40, 65, "#FDF0D0"), (65, 100, "#FBE3E4")]


def quad_html(name, p, details, ready=True, note=""):
    if ready:
        danger = p >= 50
        chip = f"<span class='chip chip-{'danger' if danger else 'ok'}'>{'MDD 유사 패턴' if danger else '건강대조군 유사 패턴'}</span>"
        color = "#E5484D" if danger else "#2F9E8F"
        rows = "".join(f"<div class='drow'><span>{esc(k)}</span>{detail_val(v)}</div>" for k, v in details)
    else:
        chip = "<span class='chip chip-muted'>데이터 대기</span>"
        color = "#B8C2D6"
        rows = "".join(f"<div class='drow'><span>{esc(k)}</span><b class='mono' style='color:#B8C2D6;'>--</b></div>"
                       for k in details)
    return (f"<div class='quad'><div class='quad-head'><span class='quad-name'>{esc(name)}</span>{chip}</div>"
            f"<div class='quad-body'><div class='quad-gauge'>{gauge_svg(p, QUAD_BANDS, color, ready)}</div>"
            f"<div class='quad-detail'><div class='dhead'>모델 기여 · TOP 3</div>{rows}"
            f"<div class='foot'>{esc(note)}</div></div></div></div>")


TIER_CHIP = {"data": "ok", "summary": "warn", "simulation": "warn"}   # 참고용 데이터(요약통계·시뮬레이션)는 같은 표시


def fmt_q(row):
    q = row.get("q")
    if q is None:
        return row.get("q_reported", "-")
    return "&lt;.001" if q < .001 else f"{q:.3f}"


def evidence_html(mid):
    """지표별 MDD 연관성(상관 r, 효과크기 d, FDR q)과 자료의 한계를 보여주는 패널"""
    m = MODS[mid]
    n = f"MDD {m['n_mdd']} · 건강대조군 {m['n_control']}" if m.get("n_mdd") else "논문 보충표 · 군별 평균±SD"
    row = lambda a, cls="": (f"<tr class='{cls}'><td>{esc(a['label'])}</td><td>{a['r']:+.2f}</td><td>{a['d']:+.2f}</td><td>{fmt_q(a)}</td></tr>")
    rows = "".join(row(a) for a in m["associations"][:5])
    rows += "".join(row(a, "hl") for a in m.get("summary_markers", []) if a["feature"] in ("alpha_beta", "faa"))
    return (f"<div class='panel'><div class='panel-title'>{esc(m['label'])} <span class='panel-sub'>{esc(n)}</span> "
            f"<span class='chip chip-{TIER_CHIP[m['tier']]}'>{esc(m['tier_label'])}</span></div>"
            "<table class='perf'><thead><tr><th>지표</th><th>r</th><th>d</th><th>FDR q</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
            f"<div class='foot'>{m['n_fdr05']}/{m['n_tested']}개 지표 FDR&lt;.05 · {esc(m['limits'][0])}</div></div>")


def svg_line(xs, series, y0, y1, ticks, w=520, h=210, bands=None, hlines=None, tfmt=None, label_every=1, band_labels=None, mr=16):
    ml, mt, mb = 40, 12, 26
    pw, ph = w - ml - mr, h - mt - mb
    n = len(xs)
    X = lambda i: ml + (pw * i / (n - 1) if n > 1 else pw / 2)
    Y = lambda v: mt + ph * (1 - (v - y0) / (y1 - y0))
    tfmt = tfmt or (lambda t: f"{t:g}")
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">']
    for lo, hi, col in (bands or []):
        o.append(f'<rect x="{ml}" y="{Y(hi):.1f}" width="{pw}" height="{Y(lo) - Y(hi):.1f}" fill="{col}"/>')
    for t in ticks:
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="#E3E9F4" stroke-width="1"/>')
        o.append(f'<text x="{ml - 7}" y="{Y(t) + 3.5:.1f}" text-anchor="end" font-size="10" fill="#64748B">{esc(tfmt(t))}</text>')
    for i, x in enumerate(xs):
        if i % label_every == 0 or i == n - 1:
            o.append(f'<text x="{X(i):.1f}" y="{h - 8}" text-anchor="middle" font-size="10" fill="#64748B">{esc(x)}</text>')
    for (lo, hi, txt) in (band_labels or []):
        o.append(f'<text x="{w - mr + 7}" y="{Y((lo + hi) / 2) + 3:.1f}" text-anchor="start" font-size="9.5" font-weight="600" fill="#94A3B8">{esc(txt)}</text>')
    for hl in (hlines or []):
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(hl["y"]):.1f}" y2="{Y(hl["y"]):.1f}" stroke="{hl.get("color", "#94A3B8")}" '
                 f'stroke-width="1.3" stroke-dasharray="4 4"/>')
        o.append(f'<text x="{w - mr - 3}" y="{Y(hl["y"]) - 4:.1f}" text-anchor="end" font-size="9.5" fill="{hl.get("color", "#64748B")}" font-weight="700">{esc(hl["label"])}</text>')
    for s in series:
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["values"]))
        if s.get("area"):
            o.append(f'<polygon points="{X(0):.1f},{Y(y0):.1f} {pts} {X(n - 1):.1f},{Y(y0):.1f}" fill="{s["color"]}" opacity=".10"/>')
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else ""
        o.append(f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" stroke-width="2.6" stroke-linejoin="round" '
                 f'stroke-linecap="round"{dash}/>')
        for i, v in enumerate(s["values"]):
            o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.6" fill="#fff" stroke="{s["color"]}" stroke-width="2.2"/>')
        lv = s["values"][-1]
        o.append(f'<text x="{X(n - 1):.1f}" y="{Y(lv) - 9:.1f}" text-anchor="end" font-size="10.5" font-weight="800" '
                 f'fill="{s["color"]}">{esc(s.get("last_fmt", "{:g}").format(lv))}</text>')
    o.append("</svg>")
    return "".join(o)


def svg_radar(labels, vals, thr, w=420, h=300):
    cx, cy, R = w / 2, h / 2 + 4, 102
    n = len(labels)
    ang = [math.radians(-90 + i * 360 / n) for i in range(n)]
    P = lambda i, v: (cx + R * v / 100 * math.cos(ang[i]), cy + R * v / 100 * math.sin(ang[i]))
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">']
    for ring in (25, 50, 75, 100):
        pts = " ".join(f"{P(i, ring)[0]:.1f},{P(i, ring)[1]:.1f}" for i in range(n))
        o.append(f'<polygon points="{pts}" fill="{"#F8FAFF" if ring == 100 else "none"}" stroke="#DCE3F1" stroke-width="1"/>')
        o.append(f'<text x="{cx + 3:.1f}" y="{cy - R * ring / 100 + 10:.1f}" font-size="8.5" fill="#A3AEC4">{ring}</text>')
    for i in range(n):
        x, y = P(i, 100)
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#DCE3F1" stroke-width="1"/>')
        lx, ly = cx + (R + 22) * math.cos(ang[i]), cy + (R + 16) * math.sin(ang[i])
        anchor = "middle" if abs(math.cos(ang[i])) < 0.3 else ("start" if math.cos(ang[i]) > 0 else "end")
        o.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="{anchor}" font-size="11.5" font-weight="800" fill="#334155">{esc(labels[i])}</text>')
    tp = " ".join(f"{P(i, thr[i])[0]:.1f},{P(i, thr[i])[1]:.1f}" for i in range(n))
    o.append(f'<polygon points="{tp}" fill="none" stroke="#E5484D" stroke-width="1.6" stroke-dasharray="5 4" opacity=".8"/>')
    vp = " ".join(f"{P(i, vals[i])[0]:.1f},{P(i, vals[i])[1]:.1f}" for i in range(n))
    o.append(f'<polygon points="{vp}" fill="#4F6BD3" fill-opacity=".20" stroke="#4F6BD3" stroke-width="2.6" stroke-linejoin="round"/>')
    for i in range(n):
        x, y = P(i, vals[i])
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#fff" stroke="#4F6BD3" stroke-width="2.4"/>')
    o.append("</svg>")
    return "".join(o)


def svg_roc(perf, w=440, h=262):
    ml, mr, mt, mb = 42, 14, 12, 40
    pw, ph = w - ml - mr, h - mt - mb
    X = lambda f: ml + pw * f
    Y = lambda t: mt + ph * (1 - t)
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;">']
    for t in (0, .25, .5, .75, 1):
        o.append(f'<line x1="{ml}" x2="{w - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="#E3E9F4"/>')
        o.append(f'<line y1="{mt}" y2="{h - mb}" x1="{X(t):.1f}" x2="{X(t):.1f}" stroke="#EEF2F8"/>')
        o.append(f'<text x="{ml - 6}" y="{Y(t) + 3.5:.1f}" text-anchor="end" font-size="10" fill="#64748B">{t:g}</text>')
        o.append(f'<text x="{X(t):.1f}" y="{h - mb + 15}" text-anchor="middle" font-size="10" fill="#64748B">{t:g}</text>')
    o.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(1)}" y2="{Y(1)}" stroke="#94A3B8" stroke-width="1.3" stroke-dasharray="5 4"/>')
    for name in perf:       # 교차검증에서 실제로 계산한 ROC 점
        pts = " ".join(f"{X(f):.1f},{Y(t):.1f}" for f, t in perf[name]["roc"])
        o.append(f'<polyline points="{pts}" fill="none" stroke="{PERF_COLORS[name]}" stroke-width="2.4" stroke-linejoin="round"/>')
    o.append(f'<text x="{ml + pw / 2:.1f}" y="{h - 6}" text-anchor="middle" font-size="10.5" font-weight="700" fill="#475569">1 - 특이도 (FPR)</text>')
    o.append(f'<text transform="translate(12 {mt + ph / 2:.1f}) rotate(-90)" text-anchor="middle" font-size="10.5" font-weight="700" '
             f'fill="#475569">민감도 (TPR)</text></svg>')
    return "".join(o)


def consent_chip(prof):
    c = (prof or {}).get("consent") or {}
    if not c:
        return "<span class='chip chip-muted'>동의 기록 없음</span>"
    return ("<span class='chip chip-ok'>연구 활용 동의</span>" if c.get("research")
            else "<span class='chip chip-muted'>연구 미동의</span>")


def profile_html(prof, care_chip, phq_chip):
    if prof:
        name = prof.get("name") or "-"
        age = f"만 {prof['age']}세" if prof.get("age") else "-"
        sex = prof.get("sex") or "-"
        h, w = prof.get("height_cm"), prof.get("weight_kg")
    else:
        return "<div class='req-empty'>연동된 환자가 없습니다. 환자 앱에서 이름을 입력하면 이곳에 나타납니다.</div>"
    bmi = f"{w / (h / 100) ** 2:.1f}" if (h and w) else "-"
    hs = f"{h} cm" if h else "-"
    ws = f"{w} kg" if w else "-"
    initial = esc(name[:1]) if name and name != "-" else "?"
    return (f"<div class='pf'><div class='pf-av'>{initial}</div><div><div class='pf-name'>{esc(name)}</div>"
            f"<div class='pf-sub'>{esc(age)} · {esc(sex)}</div></div></div>"
            f"<div class='pf-grid'><div><span>키</span><b>{hs}</b></div><div><span>몸무게</span><b>{ws}</b></div>"
            f"<div><span>BMI</span><b>{bmi}</b></div></div>"
            f"<div class='pf-chips'>{care_chip}{phq_chip}</div>")


def request_html(req, urgent=False, title=None):
    cls = "req urgent" if urgent else "req"
    title = title or ("긴급 위험 알림" if urgent else "환자 신청")
    return (f"<div class='{cls}'><div class='req-t'>{title}</div>"
            f"<div class='req-s'>{req}</div></div>")


STATUS_DOT = {"confirmed": "conf", "scheduled": "conf", "requested": "req", "urgent": "urg", "completed": "done"}
STATUS_CHIP = {"confirmed": ("확정", "info"), "scheduled": ("예정", "info"), "requested": ("수락 대기", "warn"),
               "urgent": ("긴급 · 수락 대기", "danger"), "completed": ("완료", "muted")}


def calendar_html(selected, events):
    by_day = defaultdict(list)
    for e in events:
        by_day[e["date"]].append(e["status"])
    today = date.today()
    cal = pycal.Calendar(firstweekday=6)
    cells = []
    for d in cal.itermonthdates(selected.year, selected.month):
        cls = ["cal-day"]
        if d.month != selected.month:
            cls.append("other")
        if d == today:
            cls.append("today")
        if d == selected:
            cls.append("sel")
        kinds = list(dict.fromkeys(by_day.get(d.isoformat(), [])))[:3]
        dots = "".join(f"<i class='dot dot-{STATUS_DOT[k]}'></i>" for k in kinds)
        cells.append(f"<div class='{' '.join(cls)}'>{d.day}<div class='dots'>{dots}</div></div>")
    head = "".join(f"<span>{w}</span>" for w in "일월화수목금토")
    legend = ("<div class='cal-legend'><span><i style='background:#4F6BD3'></i>확정·예정</span>"
              "<span><i style='background:#F5A524'></i>수락 대기</span><span><i style='background:#E5484D'></i>긴급</span>"
              "<span><i style='background:#B8C2D6'></i>완료</span></div>")
    return f"<div class='cal-head'>{head}</div><div class='cal-grid'>{''.join(cells)}</div>{legend}"


def records_html(events):
    if not events:
        return "<div class='req-empty'>기록 없음</div>"
    rows = ""
    for e in sorted(events, key=lambda x: (x["date"], x.get("time", "")), reverse=True):
        label, cls = STATUS_CHIP[e["status"]]
        when = e["date"] + (f" {e['time']}" if e.get("time") else "")
        rows += (f"<tr><td class='d'>{esc(when)}</td><td>{esc(e['kind'])}</td>"
                 f"<td><span class='chip chip-{cls}'>{label}</span></td></tr>")
    return (f"<div class='rec-wrap'><table class='rec'><thead><tr><th>일시</th><th>구분</th><th>상태</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div>")


def factor_bars(items, group_color, limit=8):
    top = [i for i in items if i.get("contribution", 0) > 0][:limit]
    if not top:
        return "<div class='empty'>반영된 신호 없음</div>"
    mx = max(i["share_pct"] for i in top) or 1
    return "".join(
        f"<div class='factor'><span class='f-name'>{esc(i['name'])}</span><span class='f-bar'>"
        f"<i style='width:{i['share_pct'] / mx * 100:.0f}%;background:{group_color.get(i['group'], '#4F6BD3')};'></i></span>"
        f"<span class='f-pct'>{i['share_pct']:.0f}%</span></div>" for i in top)


GROUP_COLOR = {"생활 리듬": "#4F6BD3", "몸의 신호": "#7C93E8", "생물학적 지표": "#2F3F8F", "마음 상태": "#F5A524"}


# =====================================================================
# 데이터 준비
# =====================================================================
# 이번 실행을 시작하는 시점의 공유 파일 상태 (화면 하단의 감시 기능이 비교해요)
st.session_state.link_sig = link_signature()

PATIENTS = list_patients()
if not PATIENTS and SETTINGS.get("auto_seed_demo"):      # 저장 공간이 비어 있으면 시연 환자 6명을 자동으로 만들어요
    try:
        if seed_demo_patients():
            PATIENTS = list_patients()
            st.session_state.link_sig = link_signature()
    except Exception:
        pass
PROFILES = dict(PATIENTS)
if st.session_state.get("sel_pid") not in PROFILES:       # 처음에는 가장 최근에 앱을 사용한 환자
    st.session_state.sel_pid = PATIENTS[0][0] if PATIENTS else None
linked_pid = st.session_state.sel_pid
linked_prof = PROFILES.get(linked_pid, {})
now = datetime.now()

if "calendar_events" not in st.session_state:       # 연동 환자가 없을 때만 보이는 화면 예시 일정
    st.session_state["calendar_events"] = [
        {"날짜": "2026-10-15", "구분": "초진 문진 및 생체데이터 수집 (예시)"},
        {"날짜": "2026-10-29", "구분": "2차 추적 관찰 및 처방 재조정 (예시)"},
    ]
if st.session_state.get("flash"):
    st.toast(st.session_state.pop("flash"), icon=":material/check_circle:")
if "sel_date" not in st.session_state:
    st.session_state.sel_date = date.today()
if "reg_type" not in st.session_state:
    st.session_state.reg_type = "대면 정기 진료"
if "seen_reqs" not in st.session_state:
    st.session_state.seen_reqs = None
if "seen_urgent" not in st.session_state:
    st.session_state.seen_urgent = None


def build_events(pid):
    """선택한 환자의 예약(대기·확정)과 의료진이 등록한 일정. 연동 환자가 없으면 이 화면에만 남는 일정"""
    today_iso = date.today().isoformat()
    events = []
    if not pid:
        for e in st.session_state["calendar_events"]:
            events.append({"date": e["날짜"], "time": "", "kind": e["구분"],
                           "status": "completed" if e["날짜"] < today_iso else "scheduled"})
    if pid:
        for a in read_json("appointments.json", []):
            if a.get("patient_id") != pid:
                continue
            if a.get("status") == "confirmed":
                status = "completed" if a.get("date", "") < today_iso else "confirmed"
            else:
                status = "urgent" if a.get("priority") == "urgent" else "requested"
            events.append({"date": a.get("date", ""), "time": a.get("time", ""),
                           "kind": a.get("kind") or "환자 지정 상담", "status": status})
    return events


def read_requests():
    out = []
    if os.path.exists(REQ_FILE):
        with open(REQ_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        for line in content.split("\n") if content else []:
            parts = line.split("|")
            if len(parts) == 3:
                out.append({"date": parts[0], "time": parts[1], "reason": parts[2], "line": line.strip()})
    return out


def select_patient(pid):
    st.session_state.sel_pid = pid


DX_OPTIONS = ["미기록", "MDD", "비MDD", "판단 보류"]


def save_dx(pid):
    """의사가 직접 판단한 임상 진단(AI 결과와 별개) → 연구 데이터의 정답 라벨"""
    dx_all_ = read_json(DX_FILE, {}) or {}
    choice = st.session_state.get(f"dx_{pid}", "미기록")
    hamd = st.session_state.get(f"hamd_{pid}")
    if choice == "미기록" and hamd is None:
        dx_all_.pop(pid, None)
    else:
        dx_all_[pid] = {"dx": choice, "hamd": None if hamd is None else int(hamd),
                        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "by": SETTINGS["doctor_name"]}
    write_json(DX_FILE, dx_all_)


def delete_lab(pid, rec_id):
    labs_ = read_json(LAB_FILE, {}) or {}
    labs_[pid] = [r for r in labs_.get(pid, []) if r.get("id") != rec_id]
    write_json(LAB_FILE, labs_)
    st.session_state.flash = "선택한 검사 기록을 삭제했습니다."


def open_research():
    st.session_state.go_research = True


def register_schedule(pid, pname):
    """신규 일정 등록: 선택한 환자에게 등록하고 결과를 알려요."""
    d, kind = str(st.session_state.sel_date), st.session_state.reg_type
    t = "" if st.session_state.get("reg_time", "시간 미정") == "시간 미정" else st.session_state.reg_time
    if pid:
        add_doctor_appointment(d, t, kind, pid, pname)
        st.session_state.flash = f"{pname}님 {d} {t} {kind} 일정을 등록했습니다. 환자 앱 '내 예약'에 표시됩니다."
    else:
        st.session_state["calendar_events"].append({"날짜": d, "구분": kind})
        st.session_state.flash = "연동된 환자가 없어 이 화면에만 기록했습니다."


def shift_month(delta):
    d = st.session_state.sel_date
    m = d.month - 1 + delta
    y, m = d.year + m // 12, m % 12 + 1
    st.session_state.sel_date = date(y, m, min(d.day, pycal.monthrange(y, m)[1]))


def set_reg_type(t):
    st.session_state.reg_type = t


current_requests = read_requests()
all_alerts = read_json("alerts.json", [])
all_checkins = sorted(read_json("checkins.json", []), key=lambda c: c.get("time", ""))
all_appts = read_json("appointments.json", [])
my_alerts = [a for a in all_alerts if linked_pid and a.get("patient_id") == linked_pid]
my_checkins = [c for c in all_checkins if linked_pid and c.get("patient_id") == linked_pid]
bio = read_json("bio_report.json", {}).get(linked_pid, {}) if linked_pid else {}
# 긴급 알림은 선택한 환자와 상관없이 모든 환자의 것을 보여줘요
urgent_alerts = [a for a in all_alerts if a.get("priority") == "urgent" and a.get("status") != "acknowledged"]
n_urgent = defaultdict(int)
for a in urgent_alerts:
    n_urgent[a.get("patient_id")] += 1
n_waiting = defaultdict(int)
for a in all_appts:
    if a.get("status") != "confirmed" and a.get("date", "") >= date.today().isoformat():
        n_waiting[a.get("patient_id")] += 1
last_phq = {c.get("patient_id"): c.get("total") for c in all_checkins}
labs_all = read_json(LAB_FILE, {}) or {}
dx_all = read_json(DX_FILE, {}) or {}
if st.session_state.pop("go_research", False):
    try:
        st.switch_page("research_app.py")
    except Exception:
        st.session_state.flash = "연구 모드는 streamlit_app.py로 실행했을 때 열 수 있어요."

# 새 상담 요청 / 긴급 알림이 오면 화면 우측 상단에 팝업(토스트)으로 알려요
req_keys = [f"{r['date']}|{r['time']}|{r['reason']}" for r in current_requests]
if st.session_state.seen_reqs is not None:
    fresh = [k for k in req_keys if k not in st.session_state.seen_reqs]
    if fresh:
        st.toast(f"새 상담 요청 {len(fresh)}건이 도착했습니다.", icon=":material/notifications_active:")
st.session_state.seen_reqs = set(req_keys) | (st.session_state.seen_reqs or set())
urg_ids = {a["id"] for a in urgent_alerts}
if st.session_state.seen_urgent is not None and (urg_ids - st.session_state.seen_urgent):
    st.toast("긴급 위험 알림이 도착했습니다.", icon=":material/emergency:")
st.session_state.seen_urgent = urg_ids | (st.session_state.seen_urgent or set())

# =====================================================================
# 화면: 메인 진단 창(7.8) / 우측 환자 관리 창(2.2)
# =====================================================================
main_col, right_col = st.columns([7.8, 2.2])

# ------------------------- 우측 패널 -------------------------
with right_col:
    # 로그인한 의료진 (시연용 계정)
    with card("account"):
        a1, a2 = st.columns([4, 1.3])
        a1.markdown(f"<div class='card-label' style='margin:0'>{esc(SETTINGS['doctor_dept'])}</div>"
                    f"<div style='font-weight:800;color:#0F172A;'>{esc(SETTINGS['doctor_name'])} 선생님</div>"
                    f"<div class='panel-sub'>ID {esc(SETTINGS['doctor_id'])}</div>", unsafe_allow_html=True)
        if SETTINGS["doctor_login"]:
            a2.button("", key="logout", on_click=logout, width="stretch", icon=":material/logout:", help="로그아웃")
        st.button("연구 모드 (바이오마커 탐색)", key="to_research", on_click=open_research, width="stretch",
                  icon=":material/science:")

    # 0) 환자 목록: 환자 앱을 사용한 모든 환자 중 한 명을 골라 살펴봐요
    with card("patients"):
        md(f"<div class='card-label'>환자 목록 · {len(PATIENTS)}명</div>")
        if not PATIENTS:
            md("<div class='req-empty'>환자 앱을 사용한 환자가 없습니다</div>")
        for pid, prof in PATIENTS:
            badges = []
            if n_urgent[pid]:
                badges.append(f"긴급 {n_urgent[pid]}")
            if n_waiting[pid]:
                badges.append(f"요청 {n_waiting[pid]}")
            if last_phq.get(pid) is not None:
                badges.append(f"PHQ {last_phq[pid]}")
            if labs_all.get(pid):
                badges.append(f"검사 {len(labs_all[pid])}")
            if prof.get("demo"):
                badges.append("시연")
            label = (prof.get("name") or pid) + (" · " + " · ".join(badges) if badges else "")
            st.button(label, key=f"pt_{pid}", on_click=select_patient, args=(pid,), width="stretch",
                      type="primary" if pid == linked_pid else "secondary",
                      icon=":material/emergency:" if n_urgent[pid] else ":material/person:")

    # 1) 환자 프로필
    step_label = {"crisis": ("긴급", "danger"), "doctor": ("상담 권고", "warn"), "self": ("경과 관찰", "info")}
    care_chip = "<span class='chip chip-muted'>위험 감지 없음</span>"
    if my_alerts:
        lab, cls = step_label.get(my_alerts[-1].get("care_step"), ("-", "muted"))
        care_chip = f"<span class='chip chip-{cls}'>위험 단계 · {lab}</span>"
    phq_chip = ""
    if my_checkins:
        phq_chip = f"<span class='chip chip-info'>PHQ-9 {my_checkins[-1]['total']}점</span>"
    if linked_pid:
        care_chip += consent_chip(linked_prof) + ("<span class='chip chip-warn'>시연 환자</span>" if linked_prof.get("demo") else "")
    with card("profile"):
        md(f"<div class='card-label'>환자 프로필</div>{profile_html(linked_prof, care_chip, phq_chip)}")
        if linked_pid:
            my_dx = dx_all.get(linked_pid, {})
            dkey, hkey = f"dx_{linked_pid}", f"hamd_{linked_pid}"
            if dkey not in st.session_state:
                st.session_state[dkey] = my_dx.get("dx", "미기록") if my_dx.get("dx") in DX_OPTIONS else "미기록"
            if hkey not in st.session_state:
                st.session_state[hkey] = my_dx.get("hamd")
            d1, d2 = st.columns([1.3, 1])
            d1.selectbox("임상 진단 (의사 판단)", DX_OPTIONS, key=dkey, on_change=save_dx, args=(linked_pid,))
            d2.number_input("HAM-D", min_value=0, max_value=52, step=1, key=hkey, on_change=save_dx, args=(linked_pid,),
                            placeholder="선택")
            md("<div class='foot'>AI 결과와 별개로 의사가 판단해 기록해요. 연구 활용에 동의한 환자는 가명으로 연구 데이터에 포함돼요.</div>")

    # 2) 실시간 상담 요청
    with card("requests"):
        md("<div class='card-label'>실시간 상담 요청</div>")
        for a in urgent_alerts[-3:]:
            who = esc(a.get("patient_name") or PROFILES.get(a.get("patient_id"), {}).get("name", ""))
            md(request_html(f"{esc(a.get('time', ''))}<br>{esc(a.get('trigger_message', ''))}", urgent=True,
                            title=f"긴급 위험 알림 · {who}"))
            if st.button("확인", key=f"ack_{a['id']}", use_container_width=True):
                ack_alert(a["id"])
                st.rerun()
        if current_requests:
            for idx, req in enumerate(current_requests):
                is_urg = "[긴급]" in req["reason"]
                md(request_html(f"일시 {esc(req['date'])} {esc(req['time'])}<br>사유 {esc(req['reason'])}", urgent=is_urg,
                                title="긴급 상담 신청" if is_urg else "환자 신청"))
                if st.button("상담 수락", key=f"acc_{idx}", use_container_width=True, type="primary"):
                    matched = confirm_appointment(req, linked_pid)
                    if matched:
                        st.session_state.flash = f"{matched.get('patient_name', '')}님 {req['date']} {req['time']} 상담을 확정했습니다."
                    else:
                        st.session_state["calendar_events"].append({"날짜": req["date"], "구분": f"환자 지정 상담 ({req['time']})"})
                    remain = [r for i, r in enumerate(current_requests) if i != idx]
                    with open(REQ_FILE, "w", encoding="utf-8") as f:
                        for r in remain:
                            f.write(f"{r['date']}|{r['time']}|{r['reason']}\n")
                    st.rerun()
        elif not urgent_alerts:
            md("<div class='req-empty'>대기 중인 요청 없음</div>")

    # 3) 진료 및 상담 일정 (달력) + 진료 기록
    events = build_events(linked_pid)
    with card("calendar"):
        md("<div class='card-label'>진료 및 상담 일정</div>")
        n1, n2, n3 = st.columns([1, 3, 1])
        n1.button(":material/chevron_left:", key="m_prev", on_click=shift_month, args=(-1,), use_container_width=True)
        n3.button(":material/chevron_right:", key="m_next", on_click=shift_month, args=(1,), use_container_width=True)
        n2.markdown(f"<div class='cal-month'>{st.session_state.sel_date.year}년 {st.session_state.sel_date.month}월</div>",
                    unsafe_allow_html=True)
        md(calendar_html(st.session_state.sel_date, events))
        st.date_input("일정 날짜 (여기서 날짜를 고르세요)", key="sel_date")
        with st.expander("신규 일정 등록", icon=":material/event:"):
            target = esc(linked_prof.get("name", "")) if linked_pid else "연동 환자 없음 (이 화면에만 기록)"
            md(f"<div class='req-empty'>대상 <b>{target}</b> · 날짜 <b>{st.session_state.sel_date}</b></div>")
            for t in ["대면 정기 진료", "화상 상담", "임상 평가"]:
                st.button(t, key=f"reg_{t}", on_click=set_reg_type, args=(t,), use_container_width=True,
                          type="primary" if st.session_state.reg_type == t else "secondary")
            st.selectbox("시간", ["시간 미정"] + [f"{h:02d}:00" for h in range(9, 18)], key="reg_time")
            st.button("등록", key="reg_go", use_container_width=True, type="primary", on_click=register_schedule,
                      args=(linked_pid, linked_prof.get("name", "")))
    with card("records"):
        md("<div class='card-label'>해당 환자 진료 기록</div>" + records_html(events))

    # 4) 환자 데이터 업로드 (가장 하단)
    with card("upload"):
        md("<div class='card-label'>환자 데이터 업로드</div>")
        uploaded_file = st.file_uploader("환자 파일 업로드", type=["csv", "xlsx"], label_visibility="collapsed",
                                         key=f"upload_{linked_pid}")     # 환자를 바꾸면 업로드도 새로 시작
        target_name = esc(linked_prof.get("name", "")) if linked_pid else "연동 환자 없음 (저장되지 않음)"
        md(f"<div class='req-empty'>올린 파일은 <b>{target_name}</b>의 검사 기록으로 저장돼요. 한 행이 검사 1회차예요.</div>")
        demo_path = os.path.join(DEMO_DIR, "demo_cases.csv")
        if os.path.exists(demo_path):
            with open(demo_path, "rb") as demo_file:
                st.download_button("시연 검사 파일 (6행 형식 예시)", demo_file.read(), file_name="demo_cases.csv",
                                   mime="text/csv", width="stretch", icon=":material/download:")

# ------------------------- 메인: 분석 데이터 -------------------------
patient_df, upload_failed = None, False
if uploaded_file is not None:
    try:
        uploaded_file.seek(0)
        patient_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    except Exception:
        patient_df, upload_failed = None, True


def case_info(df, i):
    """i번째 행의 이름과 구분 (선택 컬럼: 사례명/case_name, 구분/group). 이름이 없으면 빈 값"""
    row = df.iloc[i]
    get = lambda *cols: next((str(row[c]).strip() for c in cols if c in df.columns and pd.notna(row[c]) and str(row[c]).strip()), "")
    return get("사례명", "case_name", "name"), get("구분", "group", "label")


def df_records(df, start=0):
    """표의 각 행 → 검사 기록 (값은 숫자 컬럼만)"""
    out = []
    for i in range(len(df)):
        nm, grp = case_info(df, i)
        out.append({"id": uuid.uuid4().hex[:8], "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "label": nm or f"{start + i + 1}회차 검사", "group": grp, "file": getattr(uploaded_file, "name", ""),
                    "values": patient_values(df.iloc[[i]].reset_index(drop=True))})
    return out


def score_values(vals):
    """검사값을 4개 모달리티로 계산해요. 필요한 값이 빠진 모달리티는 계산하지 않아요(임의로 채우지 않음)."""
    res_, miss_ = {}, {}
    for mid in MOD_ORDER:
        r_, m_ = score_modality(mid, vals)
        if r_:
            res_[mid] = r_
        else:
            miss_[mid] = m_
    return res_, miss_


def fusion_score(res_, mods):
    """통합 규칙: 선택한 검사 로짓의 동일 가중 평균 (같은 환자의 4종 자료가 없어 가중치를 학습할 수 없어요)"""
    used = [res_[m] for m in MOD_ORDER if m in res_ and m in mods]
    if not used:
        return None, []
    return int(round(logit_to_pct(sum(r["logit"] for r in used) / len(used)))), used


# 통합에 포함할 검사 (기본값은 관리자 설정, 4개 모두). 버튼은 AI FUSION 카드에 있어요.
if "fusion_mods" not in st.session_state:
    st.session_state.fusion_mods = [m for m in SETTINGS["fusion_default"] if m in MOD_ORDER]
fusion_mods = st.session_state.fusion_mods or []

# 업로드한 파일은 선택한 환자의 검사 기록으로 저장해요(한 번만). 다음부터는 환자를 고르면 자동으로 불러와요.
if patient_df is not None and not patient_df.empty and linked_pid:
    save_sig = f"{linked_pid}:{getattr(uploaded_file, 'name', '')}:{getattr(uploaded_file, 'size', '')}:{len(patient_df)}"
    if st.session_state.get("saved_upload") != save_sig:
        labs_all = read_json(LAB_FILE, {}) or {}
        mine = labs_all.setdefault(linked_pid, [])
        mine.extend(df_records(patient_df, start=len(mine)))
        write_json(LAB_FILE, labs_all)
        st.session_state.saved_upload = save_sig
        st.toast(f"{linked_prof.get('name', '')}님의 검사 기록 {len(patient_df)}건을 저장했습니다.", icon=":material/save:")
if linked_pid:
    records = labs_all.get(linked_pid, [])
elif patient_df is not None and not patient_df.empty:
    records = df_records(patient_df)          # 연동 환자가 없으면 저장하지 않고 화면에만 보여줘요
else:
    records = []

# 같은 환자의 검사 회차를 넘겨 봐요. 새 기록이 생기면 가장 최근 회차를 보여줘요.
n_cases = len(records)
view_sig = f"{linked_pid}:{n_cases}"
if st.session_state.get("view_sig") != view_sig:
    st.session_state.view_sig = view_sig
    st.session_state.case_idx = max(n_cases - 1, 0)
case_idx = min(st.session_state.get("case_idx", 0), max(n_cases - 1, 0))


def move_case(step):
    st.session_state.case_idx = (st.session_state.get("case_idx", 0) + step) % max(n_cases, 1)


if n_cases:
    cur_rec = records[case_idx]
    results, missing_by_mod = score_values(cur_rec.get("values", {}))
    case_name, case_group = cur_rec.get("label", ""), cur_rec.get("group", "")
else:
    cur_rec = None
    results, missing_by_mod = {}, {m: MODS[m]["model"]["features"] for m in MOD_ORDER}
    case_name, case_group = "", ""
ready = bool(results)
total_risk, fusion_used = fusion_score(results, fusion_mods)
fusion_ready = bool(fusion_used)

if fusion_ready:
    if total_risk >= 65:
        fusion_label, fusion_cls, fusion_color = "MDD 유사 패턴 우세", "danger", "#E5484D"
    elif total_risk >= 40:
        fusion_label, fusion_cls, fusion_color = "경계 패턴", "warn", "#F5A524"
    else:
        fusion_label, fusion_cls, fusion_color = "건강대조군 유사 패턴 우세", "ok", "#2F9E8F"
    by_mod = ", ".join(f"{r['name']} {r['prob']:.0f}%" for r in fusion_used)
    pushers = sorted(((lab, c) for r in fusion_used for lab, c in r["top"] if c > 0), key=lambda x: -x[1])[:2]
    driver = (f"MDD 방향으로 가장 크게 기여한 지표는 {', '.join(lab for lab, _ in pushers)}입니다. " if pushers
              else "MDD 방향으로 기여한 지표는 없습니다. ")
    ai_comment = (f"규칙 기반 통합 점수는 {total_risk}%입니다({by_mod}). {driver}"
                  "이 점수의 정확도는 같은 환자에게서 4종을 모두 측정한 코호트로 검증되지 않았으므로 임상 판단의 참고자료로만 사용해 주세요.")

# ------------------------- 메인 패널 -------------------------
with main_col:
    link_chip = (f"<span class='chip chip-ok'>선택 환자</span><b>{esc((linked_prof or {}).get('name', ''))}</b>"
                 if linked_pid else "<span class='chip chip-muted'>연동 환자 없음</span>")
    data_chip = (f"<span class='chip chip-info'>분석 완료 {len(results)}/4</span>" if ready else "<span class='chip chip-muted'>데이터 대기</span>")
    md(f"<div class='strip'><div class='strip-l'>{link_chip}{data_chip}</div>"
       f"<div class='strip-r'>갱신 {now.strftime('%H:%M:%S')}</div></div>")
    if upload_failed:
        st.error("파일을 읽지 못했습니다. CSV 또는 XLSX 형식을 확인해 주세요.")

    head = "".join(f"<th>{MOD_LABEL[m]}</th>" for m in MOD_ORDER)
    mods_note = f"통합 점수는 지금 선택한 검사({', '.join(MOD_LABEL[m] for m in fusion_mods) or '없음'})로 계산해요."

    def score_row(vals):
        res_i, _ = score_values(vals)
        fus_i, _ = fusion_score(res_i, fusion_mods)
        probs_i = [res_i[m]["prob"] if m in res_i else np.nan for m in MOD_ORDER]
        return probs_i, fus_i

    def cells_html(probs_i, fus_i):
        return ("".join("<td>-</td>" if np.isnan(p) else f"<td>{p:.0f}%</td>" for p in probs_i)
                + f"<td><b>{'-' if fus_i is None else f'{fus_i}%'}</b></td>")

    # 검사 회차 넘기기 (같은 환자의 경과)
    if n_cases:
        p1, p2, p3, p4 = st.columns([1, 6, 1, 1.4])
        p1.button(":material/chevron_left:", key="case_prev", on_click=move_case, args=(-1,), width="stretch", disabled=n_cases < 2)
        p3.button(":material/chevron_right:", key="case_next", on_click=move_case, args=(1,), width="stretch", disabled=n_cases < 2)
        grp_chip = (f" <span class='chip chip-{'danger' if 'MDD' in case_group.upper() else 'ok'}'>{esc(case_group)}</span>"
                    if case_group else "")
        p2.markdown(f"<div class='case-nav'><span class='panel-sub'>검사 {case_idx + 1} / {n_cases}</span> "
                    f"<b>{esc(case_name)}</b><span class='panel-sub'>{esc(cur_rec.get('date', ''))}</span>{grp_chip}</div>",
                    unsafe_allow_html=True)
        if linked_pid:
            p4.button("기록 삭제", key="del_lab", on_click=delete_lab, args=(linked_pid, cur_rec.get("id")), width="stretch",
                      icon=":material/delete:")
        if n_cases > 1:
            rows_html = ""
            for i, rec in enumerate(records):
                probs_i, fus_i = score_row(rec.get("values", {}))
                rows_html += (f"<tr class='{'hl' if i == case_idx else ''}'><td>{esc(rec.get('label', ''))}</td>"
                              f"<td>{esc(rec.get('date', ''))}</td>{cells_html(probs_i, fus_i)}</tr>")
            with st.expander(f"검사 회차 비교 ({n_cases}건)", icon=":material/timeline:"):
                md(f"<table class='perf'><thead><tr><th>회차</th><th>날짜</th>{head}<th>통합</th></tr></thead>"
                   f"<tbody>{rows_html}</tbody></table><div class='foot'>{mods_note}</div>")

    # 환자 간 비교 (각 환자의 가장 최근 검사, 의사가 기록한 임상 진단별 평균)
    lab_patients = [(pid, prof) for pid, prof in PATIENTS if labs_all.get(pid)]
    if len(lab_patients) >= 2:
        rows_html, by_dx = "", defaultdict(list)
        for pid, prof in lab_patients:
            probs_i, fus_i = score_row(labs_all[pid][-1].get("values", {}))
            dxv = (dx_all.get(pid) or {}).get("dx", "미기록")
            research = "동의" if ((prof.get("consent") or {}).get("research")) else "-"
            rows_html += (f"<tr class='{'hl' if pid == linked_pid else ''}'><td>{esc(prof.get('name', pid))}</td><td>{esc(dxv)}</td>"
                          f"<td>{research}</td>{cells_html(probs_i, fus_i)}</tr>")
            if dxv in ("MDD", "비MDD"):
                by_dx[dxv].append(probs_i + [np.nan if fus_i is None else fus_i])
        for dxv in ("MDD", "비MDD"):
            if by_dx.get(dxv):
                arr_ = np.array(by_dx[dxv], dtype=float)
                means = [np.nan if np.isnan(c).all() else float(np.nanmean(c)) for c in arr_.T]
                rows_html += (f"<tr class='avg'><td>{dxv} 평균</td><td>{len(by_dx[dxv])}명</td><td></td>"
                              + "".join(f"<td>{'-' if np.isnan(v) else f'{v:.0f}%'}</td>" for v in means) + "</tr>")
        with st.expander(f"환자 간 비교 ({len(lab_patients)}명 · 최근 검사 기준)", icon=":material/compare:"):
            md(f"<table class='perf'><thead><tr><th>환자</th><th>임상 진단</th><th>연구</th>{head}<th>통합</th></tr></thead>"
               f"<tbody>{rows_html}</tbody></table><div class='foot'>임상 진단은 의사가 프로필 카드에서 기록한 값이에요. {mods_note}</div>")

    if records and len(results) < 4:
        lack = ", ".join(f"{MODS[k]['name']} ({', '.join(v[:3])}{' 외' if len(v) > 3 else ''})" for k, v in missing_by_mod.items())
        st.warning(f"필요한 컬럼이 없어 계산하지 않은 항목이 있습니다: {lack}. 형식은 시연 CSV를 참고해 주세요.")

    # 십자선 기준 4분할: 좌상 EEG / 우상 Metabolites / 좌하 Cytokine / 우하 Cortisol
    q1, q2 = st.columns(2)
    q3, q4 = st.columns(2)
    for col, mid in zip([q1, q2, q3, q4], MOD_ORDER):
        r_mod = results.get(mid)
        if r_mod:
            col.markdown(quad_html(r_mod["name"], r_mod["prob"], r_mod["details"], note=r_mod["note"]), unsafe_allow_html=True)
        else:
            wait_note = MODS[mid]["tier_label"] if not records else f"필요 항목 {len(missing_by_mod[mid])}개 미입력"
            col.markdown(quad_html(MODS[mid]["name"], 0, MODS[mid]["model"]["labels"][:3], ready=False, note=wait_note), unsafe_allow_html=True)

    # 융합 진단
    md("<div class='sec-label'>MULTI-MODAL FUSION</div>")
    f1, f2 = st.columns([1, 1.15])
    with f1:
        if ready:
            probs = [r["prob"] for r in results.values()]
            mean_p = float(np.mean(probs))
            sd_text = f"{float(np.std(probs, ddof=1)):.1f}" if len(probs) > 1 else "-"
            n_high = sum(p >= 50 for p in probs)
            radar_vals = [results[m]["prob"] if m in results else 0 for m in MOD_ORDER]
            md(f"""<div class='panel'><div class='panel-title'>Biomarker Risk Profile <span class='panel-sub'>모달리티별 MDD 패턴 확률 (%)</span></div>
                {svg_radar(["EEG", "Metabolites", "Cytokine", "Cortisol"], radar_vals, [50, 50, 50, 50])}
                <div class='leg'><span><i style='background:#4F6BD3;height:4px'></i>환자</span>
                <span><i style='background:#E5484D;height:2px'></i>기준선 50%</span></div>
                <div class='stat-row'><div class='stat'><span>MDD 유사 패턴</span><b>{n_high} / {len(probs)}</b></div>
                <div class='stat'><span>모달리티 평균</span><b>{mean_p:.1f}%</b></div>
                <div class='stat'><span>모달리티 간 편차 (SD)</span><b>{sd_text}</b></div></div></div>""")
        else:
            md("<div class='panel'><div class='panel-title'>Biomarker Risk Profile</div><div class='empty'>측정 대기 중</div></div>")
    with f2:
        with card("fusion"):
            md("<div class='card-label'>AI FUSION DIAGNOSIS &amp; PRESCRIPTIONS</div>")
            st.pills("통합에 포함할 검사", list(MOD_ORDER), format_func=lambda m: MOD_LABEL[m], selection_mode="multi",
                     key="fusion_mods")
            if ready and not fusion_ready:
                md("<div class='req-empty'>통합에 포함할 검사를 하나 이상 선택해 주세요.</div>")
            if fusion_ready:
                md(f"""<div class='fusion-top'><div class='fusion-gauge'>{gauge_svg(total_risk, FUSION_BANDS, fusion_color, True, '통합 점수', True)}</div>
                    <div class='fusion-info'><span class='chip chip-{fusion_cls}'>통합 참고치</span>
                    <div class='fusion-label'>{fusion_label}</div>
                    <div class='panel-sub'>{len(fusion_used)}개 검사 규칙 기반 통합 · 정확도 미검증</div></div></div>
                    <div class='comment' style='border-left:4px solid {fusion_color};'><b>분석 요약</b><br>{esc(ai_comment)}</div>
                    <div class='card-label'>처방 및 환자 연동 소견</div>""")
                doctor_memo = st.text_area(
                    "처방 및 환자 연동 소견", key="doctor_memo", label_visibility="collapsed", height=130,
                    value="1. 생체 시계 정상화를 위한 수면 루틴 지도\n2. 항염증 식이요법 및 주 3회 유산소 운동 권고\n3. 마음이 앱으로 PHQ-9 체크인과 생활 기록 지속",
                )
                if st.button("진단 결과 확정 및 환자 플랫폼 전송", use_container_width=True, type="primary"):
                    if linked_pid:
                        def modality(res):
                            return {"id": res["id"], "name": res["name"], "probability": res["prob"], "ci95": res["ci"],
                                    "judgement": "MDD 유사 패턴" if res["prob"] >= 50 else "건강대조군 유사 패턴", "basis": res["basis"],
                                    "details": [{"item": k, "value": v} for k, v in res["details"]]}
                        report = {
                            "report_id": str(uuid.uuid4())[:8], "sent": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "patient_id": linked_pid, "patient_name": (linked_prof or {}).get("name", ""),
                            "case": {"name": case_name, "group": case_group},
                            "modalities": [modality(results[m]) for m in MOD_ORDER if m in results],
                            "fusion": {"probability": total_risk, "label": fusion_label, "comment": ai_comment,
                                       "included": [r["id"] for r in fusion_used], "validated": False},
                            "doctor_memo": doctor_memo,
                        }
                        reports = read_json("diagnosis_report.json", {})
                        if not isinstance(reports, dict):
                            reports = {}
                        reports.setdefault(linked_pid, []).append(report)
                        write_json("diagnosis_report.json", reports)
                        st.success("환자용 앱으로 진단 리포트 전송 완료")
                    else:
                        st.warning("연동된 환자가 없어 전송하지 못했습니다.")
            else:
                md(f"""<div class='fusion-top'><div class='fusion-gauge'>{gauge_svg(0, FUSION_BANDS, '#B8C2D6', False, '통합 점수', True)}</div>
                    <div class='fusion-info'><span class='chip chip-muted'>분석 대기</span>
                    </div></div>""")

    # 임상 추이 (환자 앱 연동 데이터)
    md("<div class='sec-label'>CLINICAL TRENDS</div>")
    t1, t2 = st.columns(2)
    with t1:
        if my_checkins:
            xs = [c["time"][5:10].replace("-", "/") for c in my_checkins]
            ys = [c["total"] for c in my_checkins]
            tint = ["#E6F5F2", "#F1F6E4", "#FFF4D9", "#FDE9DC", "#FBE3E4"]
            edges = [0, 5, 10, 15, 20, 27]
            bands = [(edges[i], edges[i + 1], tint[i]) for i in range(5)]
            blabels = [(edges[i], edges[i + 1], t) for i, t in enumerate(["거의 없음", "가벼움", "중간", "다소 심함", "심함"])]
            svg = svg_line(xs, [{"values": ys, "color": "#2F3F8F", "area": False, "last_fmt": "{:g}점"}], 0, 27,
                           [0, 5, 10, 15, 20, 27], bands=bands, band_labels=blabels, h=230, mr=70)
            delta = f"{ys[-1] - ys[0]:+d}점" if len(ys) > 1 else "-"
            last_c = my_checkins[-1]
            band_name = next((t for lo, hi, t in blabels if lo <= ys[-1] < hi), "심함")
            nine = last_c.get("item9", 0)
            nine_html = f"<b style='color:#B91C1C'>응답 있음</b>" if nine else "<b>없음</b>"
            n_demo = sum(1 for c in my_checkins if c.get("demo"))
            demo_chip = f" <span class='chip chip-warn'>가상 기록 {n_demo}건 포함</span>" if n_demo else ""
            md(f"""<div class='panel'><div class='panel-title'>PHQ-9 추이 <span class='panel-sub'>총점 0–27 · 최근 {len(ys)}회{demo_chip}</span></div>{svg}
                <div class='stat-row'><div class='stat'><span>최근 점수</span><b>{ys[-1]}점 · {band_name}</b></div>
                <div class='stat'><span>첫 기록 대비</span><b>{delta}</b></div>
                <div class='stat'><span>9번 문항 (자해 생각)</span>{nine_html}</div></div></div>""")
        else:
            md("<div class='panel'><div class='panel-title'>PHQ-9 추이</div><div class='empty'>환자 앱 기록 없음</div></div>")
    with t2:
        ser = bio.get("series")
        if ser:
            dts = [d[-5:] for d in ser["dates"]]
            sleep = svg_line(dts, [{"values": ser["sleep_hours"], "color": "#4F6BD3", "area": True, "last_fmt": "{:.1f}h"}],
                             3, 9, [4, 6, 8], w=250, h=130, label_every=3,
                             hlines=[{"y": 7, "label": "권장 7h", "color": "#94A3B8"}])
            steps = svg_line(dts, [{"values": ser["steps"], "color": "#2F9E8F", "area": True, "last_fmt": "{:,.0f}"}],
                             0, 7000, [0, 3500, 7000], w=250, h=130, label_every=3, tfmt=lambda t: f"{t / 1000:g}k")
            rhr = svg_line(dts, [{"values": ser["resting_hr"], "color": "#E5484D", "area": True, "last_fmt": "{:g}"}],
                           60, 85, [65, 75, 85], w=250, h=130, label_every=3)
            hrv = svg_line(dts, [{"values": ser["hrv_rmssd"], "color": "#9A7FD1", "area": True, "last_fmt": "{:g}ms"}],
                           20, 55, [25, 40, 55], w=250, h=130, label_every=3,
                           hlines=[{"y": bio.get("hrv_rmssd", {}).get("baseline_ms", 45), "label": "기준선", "color": "#94A3B8"}])
            md(f"""<div class='panel'><div class='panel-title'>생활 지표 7일 <span class='chip chip-warn'>시연용 가상 웨어러블 데이터</span></div>
                <div class='mini-grid'><div><div class='mini-title'>수면 시간</div>{sleep}</div>
                <div><div class='mini-title'>걸음 수</div>{steps}</div>
                <div><div class='mini-title'>안정시 심박 (bpm)</div>{rhr}</div>
                <div><div class='mini-title'>심박변이도 RMSSD</div>{hrv}</div></div></div>""")
        else:
            md("<div class='panel'><div class='panel-title'>생활 지표 7일</div><div class='empty'>환자 앱 연동 데이터 없음</div></div>")

    # 신호 기여도 + 모델 성능
    md("<div class='sec-label'>EXPLAINABILITY &amp; MODEL PERFORMANCE</div>")
    e1, e2 = st.columns(2)
    with e1:
        risk = bio.get("risk_signal")
        if risk:
            lvl_cls = {"안정": "info", "살펴보는 중": "warn", "함께 살펴볼 단계": "danger"}.get(risk.get("level"), "muted")
            grp = defaultdict(float)
            for f_ in risk.get("factors", []):
                grp[f_["group"]] += f_.get("share_pct", 0)
            stack = "".join(f"<span style='width:{v:.1f}%;background:{GROUP_COLOR.get(g_, '#4F6BD3')};'></span>"
                            for g_, v in sorted(grp.items(), key=lambda x: -x[1]))
            glab = "".join(f"<span><i style='background:{GROUP_COLOR.get(g_, '#4F6BD3')};height:8px;width:8px;border-radius:50%'></i>{esc(g_)} {v:.0f}%</span>"
                           for g_, v in sorted(grp.items(), key=lambda x: -x[1]))
            md(f"""<div class='panel'><div class='panel-title'>주요 위험 신호 기여도 <span class='chip chip-warn'>시연용 가상 모델 · 가상 데이터</span></div>
                <div><span class='chip chip-{lvl_cls}'>{esc(risk.get('level', ''))}</span>
                <span class='panel-sub'> 신호 점수 {risk.get('score', 0)}</span></div>
                <div class='stack'>{stack}</div><div class='leg' style='margin:0 0 10px;'>{glab}</div>
                {factor_bars(risk.get('factors', []), GROUP_COLOR)}
</div>""")
        else:
            md("<div class='panel'><div class='panel-title'>주요 위험 신호 기여도</div><div class='empty'>환자 앱 연동 데이터 없음</div></div>")
    with e2:
        leg = "".join(f"<span><i style='background:{PERF_COLORS[k]};'></i>{k}</span>" for k in MODEL_PERF)
        rows = "".join(
            f"<tr><td>{k}{' (시뮬레이션)' if k == 'Cortisol' else ''}</td><td>{v['auc']:.2f} ({v['auc_ci95'][0]:.2f}–{v['auc_ci95'][1]:.2f})</td>"
            f"<td>{v['sensitivity_at_spec80'] * 100:.1f}%</td></tr>"
            for k, v in MODEL_PERF.items())
        md(f"""<div class='panel'><div class='panel-title'>모델 성능 <span class='panel-sub'>ROC · 층화 5겹 교차검증 10회</span></div>
            {svg_roc(MODEL_PERF)}<div class='leg'>{leg}</div>
            <table class='perf'><thead><tr><th>모델</th><th>AUC (95% 구간)</th><th>민감도 (특이도 80%)</th></tr></thead><tbody>{rows}</tbody></table>
            <div class='foot'>Cytokine은 개인별 자료가 없어 AUC 산출 불가. 통합 점수는 같은 환자의 4종 자료가 없어 검증 불가.</div></div>""")

    # 근거: 지표별 MDD 연관성
    md("<div class='sec-label'>EVIDENCE · BIOMARKER–MDD ASSOCIATION</div>")
    ev1, ev2 = st.columns(2)
    ev3, ev4 = st.columns(2)
    for col, mid in zip([ev1, ev2, ev3, ev4], MOD_ORDER):
        with col:
            md(evidence_html(mid))
    md(f"<div class='foot'>r: MDD와의 점이연 상관(Cytokine은 d에서 환산한 추정치) · d: Cohen 효과크기 · 양수는 MDD에서 높음 · {esc(EVIDENCE['disclaimer'])}</div>")


# =====================================================================
# 실시간 연동: 2초마다 공유 파일을 확인해서, 환자 앱이 상담 신청·위험 알림·체크인을 남기면 새로고침 없이 화면을 갱신해요
# (추가 패키지 없이 Streamlit 기본 기능만 사용)
# =====================================================================
@st.fragment(run_every=2)
def link_watcher():
    if link_signature() != st.session_state.get("link_sig"):
        st.rerun(scope="app")


link_watcher()
