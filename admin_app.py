"""숨겨진 관리자 페이지 (/admin). 메뉴에 보이지 않고, Secrets의 ADMIN_CODE를 입력해야 들어갈 수 있어요.

- 환자 기록 현황 · 백업 · 전체 리셋 · 환자별 삭제 · 복원
- 코드 수정 없이 바꾸는 시연 설정 (의료진 로그인 화면, 통합 기본 검사, 환자 앱 시연 도구 등)
"""
import hmac
import io
import json
import os
import zipfile
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from maeumi_common import (DATA_FILES, DEFAULT_SETTINGS, MOD_LABEL, SEEN_FILE, SETTINGS_NAME, get_secret,
                           load_settings, save_settings, shared_path)

load_dotenv()
st.set_page_config(page_title="관리자", page_icon="🛠️", layout="centered")
st.markdown("""<style>
.stApp{background:#F4F6FB;}
[data-testid="stToolbar"], #MainMenu, footer{display:none !important;}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:6px 0 4px;}
.stat-grid div{background:#fff;border:1px solid #E2E8F3;border-radius:12px;padding:10px 12px;}
.stat-grid span{display:block;font-size:.72rem;color:#64748B;font-weight:700;}
.stat-grid b{font-size:1.25rem;color:#0F172A;}
[data-testid="stTextInputRootElement"], [data-baseweb="input"]{border:1px solid #C7D2E5 !important;border-radius:8px !important;
  background:#fff !important;box-shadow:0 1px 2px rgba(15,23,42,.06);}
[data-testid="stTextInputRootElement"]:focus-within, [data-baseweb="input"]:focus-within{border-color:#4F6BD3 !important;}
</style>""", unsafe_allow_html=True)

st.markdown("## 🛠️ 관리자")

# ---------------- 관리자 코드 확인 ----------------
ADMIN_CODE = get_secret("ADMIN_CODE")
if not ADMIN_CODE:
    st.error("관리자 코드가 설정되지 않아 이 페이지를 열 수 없어요. "
             "Streamlit Cloud에서는 앱 설정의 Secrets에, 내 PC에서는 .env에 `ADMIN_CODE`를 추가해 주세요.")
    st.stop()
if not st.session_state.get("admin_ok"):
    with st.form("admin_login"):
        code = st.text_input("관리자 코드", type="password")
        if st.form_submit_button("들어가기", type="primary"):
            if hmac.compare_digest(code.encode("utf-8"), str(ADMIN_CODE).encode("utf-8")):
                st.session_state.admin_ok = True
                st.rerun()
            st.error("관리자 코드가 맞지 않아요.")
    st.stop()


# ---------------- 기록 읽기·쓰기 ----------------
def read_any(name):
    path = shared_path(name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        if name.endswith(".txt"):
            return [ln for ln in f.read().split("\n") if ln.strip()]
        try:
            return json.load(f)
        except ValueError:
            return None


def write_any(name, data):
    with open(shared_path(name), "w", encoding="utf-8") as f:
        if name.endswith(".txt"):
            f.write("".join(ln + "\n" for ln in data))
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)


def count(name):
    data = read_any(name)
    return len(data) if isinstance(data, (list, dict)) else 0


def flash(msg):
    st.session_state.admin_flash = msg


if st.session_state.get("admin_flash"):
    st.success(st.session_state.pop("admin_flash"))

profiles = read_any("patient_profile.json") or {}
pending = sum(1 for a in (read_any("appointments.json") or []) if a.get("status") != "confirmed")
st.markdown(
    "<div class='stat-grid'>"
    f"<div><span>등록 환자</span><b>{len(profiles)}</b></div>"
    f"<div><span>위험 알림</span><b>{count('alerts.json')}</b></div>"
    f"<div><span>수락 대기 상담</span><b>{pending}</b></div>"
    f"<div><span>PHQ-9 기록</span><b>{count('checkins.json')}</b></div>"
    f"<div><span>소견 받은 환자</span><b>{count('diagnosis_report.json')}</b></div>"
    f"<div><span>대기 중 요청 줄</span><b>{count('consultation_req.txt')}</b></div></div>",
    unsafe_allow_html=True)
st.caption("환자 기록은 리셋하기 전까지 유지돼요. 단, Streamlit Cloud는 앱 재시작·잠듦·재배포 때 저장 공간이 초기화되니 중요한 시점에는 백업을 받아 두세요.")

tab_data, tab_settings = st.tabs(["환자 기록", "시연 설정"])

# ---------------- 환자 기록: 백업 · 리셋 · 환자별 삭제 · 복원 ----------------
with tab_data:
    st.markdown("#### 백업")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in DATA_FILES + [SETTINGS_NAME]:
            if os.path.exists(shared_path(name)):
                z.write(shared_path(name), name)
        if os.path.exists(SEEN_FILE):
            z.write(SEEN_FILE, "seen_events.json")
    st.download_button("전체 기록 백업 받기 (.zip)", buf.getvalue(), icon=":material/download:",
                       file_name=f"maeumi_backup_{datetime.now():%Y%m%d_%H%M}.zip", mime="application/zip")

    st.markdown("#### 환자별 삭제")
    if profiles:
        pid = st.selectbox("삭제할 환자", list(profiles),
                           format_func=lambda k: f"{profiles[k].get('name', k)} ({k}) · 최근 {profiles[k].get('updated', '-')}")
        if st.button("이 환자 기록만 삭제", icon=":material/person_remove:"):
            removed_lines = {a.get("req_line") for a in (read_any("appointments.json") or []) if a.get("patient_id") == pid}
            for name in DATA_FILES:
                data = read_any(name)
                if data is None:
                    continue
                if name.endswith(".txt"):
                    write_any(name, [ln for ln in data if ln.strip() not in removed_lines])
                elif isinstance(data, dict):
                    data.pop(pid, None)
                    write_any(name, data)
                elif isinstance(data, list):
                    write_any(name, [x for x in data if not (isinstance(x, dict) and x.get("patient_id") == pid)])
            if os.path.exists(SEEN_FILE):
                with open(SEEN_FILE, "r", encoding="utf-8") as f:
                    seen = json.load(f)
                seen.pop(pid, None)
                with open(SEEN_FILE, "w", encoding="utf-8") as f:
                    json.dump(seen, f, ensure_ascii=False)
            flash(f"{profiles[pid].get('name', pid)} 환자의 기록을 삭제했어요.")
            st.rerun()
    else:
        st.caption("등록된 환자가 없어요.")

    st.markdown("#### 전체 리셋")
    st.caption("모든 환자의 프로필·알림·상담 요청·예약·PHQ-9·소견을 지워요. 시연 설정은 그대로 남아요. "
               "환자 앱을 열어 둔 사람이 다시 사용하면 그 환자는 다시 등록돼요.")
    sure = st.checkbox("모든 환자 기록을 지우는 것에 동의해요 (되돌리려면 백업 파일이 필요해요)")
    if st.button("전체 리셋", type="primary", disabled=not sure, icon=":material/restart_alt:"):
        for name in DATA_FILES:
            write_any(name, [] if name.endswith(".txt") else ({} if name in ("patient_profile.json", "garden.json",
                      "bio_report.json", "diagnosis_report.json") else []))
        if os.path.exists(SEEN_FILE):
            os.remove(SEEN_FILE)
        flash("모든 환자 기록을 리셋했어요.")
        st.rerun()

    st.markdown("#### 백업에서 복원")
    up = st.file_uploader("백업 파일 (.zip)", type=["zip"])
    if up is not None and st.button("이 백업으로 덮어쓰기", icon=":material/upload:"):
        try:
            with zipfile.ZipFile(up) as z:
                names = set(z.namelist())
                restored = []
                for name in DATA_FILES + [SETTINGS_NAME, "seen_events.json"]:
                    if name not in names:
                        continue
                    raw = z.read(name).decode("utf-8")
                    if name.endswith(".json"):
                        json.loads(raw)            # 형식이 깨진 파일은 쓰지 않아요
                    target = SEEN_FILE if name == "seen_events.json" else shared_path(name)
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(raw)
                    restored.append(name)
            flash(f"{len(restored)}개 파일을 복원했어요.")
            st.rerun()
        except (zipfile.BadZipFile, ValueError, UnicodeDecodeError):
            st.error("백업 파일을 읽지 못했어요. 이 페이지에서 받은 .zip 파일인지 확인해 주세요.")

# ---------------- 시연 설정 ----------------
with tab_settings:
    s = load_settings()
    with st.form("settings"):
        st.markdown("#### 의료진 화면")
        login = st.toggle("로그인 화면 보이기 (ID·비밀번호가 미리 입력된 상태로, 로그인 버튼만 누르면 들어가요)",
                          value=s["doctor_login"])
        c1, c2, c3 = st.columns(3)
        doc_id = c1.text_input("표시할 의료진 ID", value=s["doctor_id"])
        doc_name = c2.text_input("의료진 이름", value=s["doctor_name"])
        doc_dept = c3.text_input("진료과", value=s["doctor_dept"])
        fusion_default = st.multiselect("통합 점수에 기본으로 포함할 검사", list(MOD_LABEL), default=s["fusion_default"],
                                        format_func=lambda m: MOD_LABEL[m])
        st.markdown("#### 환자 앱")
        tools = st.toggle("사이드바 시연 도구 보이기 (다른 환자의 알림·기록이 보이고 지울 수 있어요. 공개 시연 중에는 끄세요)",
                          value=s["patient_tools"])
        risk = st.toggle("대화 아래 '위험도' 표시 보이기", value=s["show_risk_debug"])
        if st.form_submit_button("설정 저장", type="primary"):
            save_settings({"doctor_login": login, "doctor_id": doc_id.strip() or DEFAULT_SETTINGS["doctor_id"],
                           "doctor_name": doc_name.strip() or DEFAULT_SETTINGS["doctor_name"],
                           "doctor_dept": doc_dept.strip() or DEFAULT_SETTINGS["doctor_dept"],
                           "fusion_default": fusion_default, "patient_tools": tools, "show_risk_debug": risk})
            flash("설정을 저장했어요. 새로 여는 화면부터 적용돼요.")
            st.rerun()
    if st.button("설정을 기본값으로 되돌리기"):
        save_settings(DEFAULT_SETTINGS)
        flash("설정을 기본값으로 되돌렸어요.")
        st.rerun()
    st.caption("설정도 앱이 재시작되면 기본값으로 돌아가요. 기본값: 로그인 화면 켜짐 · 홍길동(doctor01) · 4개 검사 모두 포함 · "
               "환자 시연 도구 숨김 · 위험도 표시 켜짐")

st.divider()
st.markdown("💙 [환자용 화면으로](/) · 🩺 [의료진 화면으로](/doctor)")
