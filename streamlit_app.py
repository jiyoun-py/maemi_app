"""마음이 통합 실행 파일: 환자용·의사용·연구·관리자 화면을 한 앱의 페이지로 실행해요.

- 환자용: 기본 주소 (예: https://<앱이름>.streamlit.app/)
- 의사용: /doctor 주소 (예: https://<앱이름>.streamlit.app/doctor)
- 연구 모드: /research (의사용 화면의 '연구 모드' 버튼)
- 관리자: /admin 주소 (메뉴에 없음, Secrets의 ADMIN_CODE 입력 필요)
- 모든 페이지가 같은 서버에서 돌기 때문에 공유 폴더(maeumi_shared)를 함께 써요.

실행: streamlit run streamlit_app.py
"""
import streamlit as st

patient = st.Page("app.py", title="마음이", icon="💙", default=True)
doctor = st.Page("doctor_app.py", title="의료진 CDSS", icon="🩺", url_path="doctor")
research = st.Page("research_app.py", title="연구 모드", icon="🔬", url_path="research")
admin = st.Page("admin_app.py", title="관리자", icon="🛠️", url_path="admin")     # 숨겨진 관리자 페이지 (ADMIN_CODE 필요)
page = st.navigation([patient, doctor, research, admin], position="hidden")   # 메뉴를 숨겨서 환자 화면에 다른 페이지 링크가 보이지 않게 해요

# 환자 화면과 의료진 화면이 같은 이름의 세션 값(sel_date 등)을 다르게 쓰므로, 같은 브라우저 창에서 화면 묶음이 바뀌면 세션을 비워요.
# 의료진 화면 ↔ 연구 모드는 같은 묶음이라 로그인 상태가 유지돼요.
GROUP = {"": "patient", "doctor": "staff", "research": "staff", "admin": "admin"}
group = GROUP.get(page.url_path, page.url_path)
if st.session_state.get("_active_group") != group:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["_active_group"] = group

page.run()
