"""마음이 통합 실행 파일: 환자용(app.py)과 의사용(doctor_app.py)을 한 앱의 두 페이지로 실행해요.

- 환자용: 기본 주소 (예: https://<앱이름>.streamlit.app/)
- 의사용: /doctor 주소 (예: https://<앱이름>.streamlit.app/doctor)
- 두 페이지가 같은 서버에서 돌기 때문에 공유 폴더(maeumi_shared)를 함께 써요. Streamlit Cloud에서도 연동이 그대로 동작해요.

실행: streamlit run streamlit_app.py
"""
import streamlit as st

patient = st.Page("app.py", title="마음이", icon="💙", default=True)
doctor = st.Page("doctor_app.py", title="의료진 CDSS", icon="🩺", url_path="doctor")
page = st.navigation([patient, doctor], position="hidden")   # 메뉴를 숨겨서 환자 화면에 의사용 링크가 보이지 않게 해요

# 두 앱이 같은 이름의 세션 값(sel_date 등)을 다르게 쓰므로, 같은 브라우저 창에서 페이지가 바뀌면 세션을 비워요
if st.session_state.get("_active_page") != page.url_path:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["_active_page"] = page.url_path

page.run()
