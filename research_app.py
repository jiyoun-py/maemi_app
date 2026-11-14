"""연구 모드 (/research): 의사 연구자용 바이오마커 탐색 작업 화면.

데이터셋
- 국민건강영양조사 2024 (공공 코호트): analysis/research_checkup.py가 계산한 research_evidence.json
- 기관 연구 데이터: 연구 활용 동의 + 임상 진단 + 검사 기록이 있는 환자만 가명 코드로 (maeumi_common.research_dataset)
"""
import html
import json
import math
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from maeumi_common import BASE_DIR, load_settings, research_dataset

st.set_page_config(page_title="Research · 마음이 CDSS", page_icon="🔬", layout="wide")
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
.stApp, .stApp p, .stApp label, .stApp li, .stApp button, .stApp input{font-family:'Pretendard','Noto Sans KR','Malgun Gothic',sans-serif !important;}
.stApp{background:#F4F6FB;}
header[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer{display:none !important;}
.block-container, [data-testid="stMainBlockContainer"]{max-width:1560px !important;padding:1.4rem 1.6rem 3rem !important;}
.stApp [data-testid="stMarkdownContainer"] p{color:#0F172A;}
[class*="st-key-panel_"]{background:#fff;border:1px solid #E2E8F3;border-radius:14px;padding:14px 16px;box-shadow:0 1px 3px rgba(15,23,42,.05);margin-bottom:12px;}
.top{display:flex;justify-content:space-between;align-items:center;background:#fff;border:1px solid #E2E8F3;border-radius:12px;
  padding:10px 16px;margin-bottom:14px;}
.top-l{display:flex;align-items:center;gap:12px;} .logo{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#4F6BD3,#2F3F8F);
  color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.1rem;}
.top-t{font-weight:800;font-size:1.05rem;color:#0F172A;line-height:1.2;} .top-s{font-size:.74rem;color:#64748B;}
.top-r{font-size:.8rem;color:#475569;text-align:right;}
.lbl{font-size:.68rem;font-weight:800;letter-spacing:.07em;color:#64748B;margin-bottom:6px;text-transform:uppercase;}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:.8rem;color:#334155;} .kv span{color:#64748B;}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px;}
.kpi{background:#fff;border:1px solid #E2E8F3;border-radius:12px;padding:10px 14px;}
.kpi span{display:block;font-size:.7rem;color:#64748B;font-weight:700;} .kpi b{font-size:1.3rem;color:#0F172A;} .kpi small{color:#64748B;font-size:.72rem;margin-left:4px;}
.warnbar{background:#FFF7E6;border:1px solid #FDE2A7;border-radius:10px;padding:9px 12px;font-size:.84rem;color:#7C4A03;margin-bottom:10px;}
.foot{font-size:.72rem;color:#94A3B8;margin-top:6px;}
[data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid #E2E8F3;}
[data-baseweb="tab"]{font-weight:700;}
</style>""", unsafe_allow_html=True)
esc = html.escape
SET = load_settings()


def load(name):
    try:
        with open(os.path.join(BASE_DIR, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def back_to_cdss():
    st.session_state.go_cdss = True


if st.session_state.pop("go_cdss", False):
    try:
        st.switch_page("doctor_app.py")
    except Exception:
        pass

RE = load("research_evidence.json")
ME = load("model_evidence.json")
FONT = dict(family="Pretendard, Malgun Gothic, sans-serif")
TIERS = ["유망 후보", "검토 필요", "근거 약함"]
TIER_COLOR = {"유망 후보": "#E5484D", "검토 필요": "#F5A524", "근거 약함": "#94A3B8"}
MIN_PER_GROUP = 30

# ---------------------------------------------------------------- 상단 바
t1, t2 = st.columns([5, 1.2])
t1.markdown(f"<div class='top'><div class='top-l'><div class='logo'>🔬</div><div><div class='top-t'>Biomarker Research Workspace</div>"
            f"<div class='top-s'>마음이 CDSS · 우울증 바이오마커 탐색</div></div></div>"
            f"<div class='top-r'>{esc(SET['doctor_dept'])} · <b>{esc(SET['doctor_name'])}</b><br>ID {esc(SET['doctor_id'])}</div></div>",
            unsafe_allow_html=True)
t2.button("CDSS로 돌아가기", on_click=back_to_cdss, width="stretch", icon=":material/arrow_back:")

left, main = st.columns([1.05, 3.6])

# ---------------------------------------------------------------- 왼쪽: 데이터셋 · 분석 조건 · 필터
rows, excl = research_dataset()
n_mdd = sum(r["dx"] == "MDD" for r in rows)
n_non = sum(r["dx"] == "비MDD" for r in rows)
with left:
    with st.container(key="panel_dataset"):
        st.markdown("<div class='lbl'>데이터셋</div>", unsafe_allow_html=True)
        ds = st.radio("데이터셋", ["국민건강영양조사 2024", "기관 연구 데이터"], label_visibility="collapsed", key="rs_ds",
                      captions=[f"공공 코호트 · n={RE['n']:,}" if RE else "결과 파일 없음",
                                f"동의·가명 · n={len(rows)} (MDD {n_mdd} · 비MDD {n_non})"])
    if ds == "국민건강영양조사 2024" and RE:
        with st.container(key="panel_cond"):
            st.markdown("<div class='lbl'>분석 조건</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kv'><span>결과 변수</span><b>PHQ-9 ≥ 10</b><span>대상</span><b>만 19세 이상</b>"
                        f"<span>사례 / 전체</span><b>{RE['n_pos']} / {RE['n']:,} ({RE['prevalence'] * 100:.1f}%)</b>"
                        f"<span>보정</span><b>나이, 성별</b><span>다중검정</span><b>BH-FDR</b>"
                        f"<span>안정성</span><b>부트스트랩 100회 · L1</b><span>계산</span><b>{esc(RE['generated'][:16].replace('T', ' '))}</b></div>",
                        unsafe_allow_html=True)
        V_all = pd.DataFrame(RE["variables"])
        with st.container(key="panel_filter"):
            st.markdown("<div class='lbl'>필터</div>", unsafe_allow_html=True)
            q_thr = st.select_slider("FDR 기준 (q)", options=[0.01, 0.05, 0.1, 0.2], value=0.05, key="rs_q")
            min_stab = st.slider("최소 선택 안정성", 0.0, 1.0, 0.0, 0.05, key="rs_stab")
            groups = st.multiselect("항목 분류", sorted(V_all["group"].unique()), key="rs_groups", placeholder="전체")
            tiers = st.multiselect("판정", TIERS, default=TIERS, key="rs_tiers")
            query = st.text_input("항목 검색", key="rs_query", placeholder="예: 혈당, CRP")

# ---------------------------------------------------------------- 기관 연구 데이터
if ds == "기관 연구 데이터":
    with main:
        ready = n_mdd >= MIN_PER_GROUP and n_non >= MIN_PER_GROUP
        st.markdown(
            "<div class='kpis'>"
            f"<div class='kpi'><span>연구 코호트</span><b>{len(rows)}</b><small>명</small></div>"
            f"<div class='kpi'><span>MDD</span><b>{n_mdd}</b><small>/ {MIN_PER_GROUP}</small></div>"
            f"<div class='kpi'><span>비MDD</span><b>{n_non}</b><small>/ {MIN_PER_GROUP}</small></div>"
            f"<div class='kpi'><span>제외 · 연구 미동의</span><b>{excl['no_consent']}</b><small>명</small></div>"
            f"<div class='kpi'><span>제외 · 진단/검사 없음</span><b>{excl['no_dx'] + excl['no_lab']}</b><small>명</small></div></div>",
            unsafe_allow_html=True)
        if not ready:
            st.markdown(f"<div class='warnbar'>분석 실행 조건: 그룹별 {MIN_PER_GROUP}명 이상 "
                        f"(현재 MDD {n_mdd} · 비MDD {n_non}). 조건을 충족하면 공공 코호트와 같은 파이프라인으로 분석합니다.</div>",
                        unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.progress(min(n_mdd / MIN_PER_GROUP, 1.0), text=f"MDD {n_mdd}/{MIN_PER_GROUP}")
        c2.progress(min(n_non / MIN_PER_GROUP, 1.0), text=f"비MDD {n_non}/{MIN_PER_GROUP}")
        st.button("분석 실행", type="primary", disabled=not ready, icon=":material/play_arrow:",
                  help=None if ready else f"그룹별 {MIN_PER_GROUP}명 이상 필요")
        with st.container(key="panel_cohort"):
            st.markdown("<div class='lbl'>연구 코호트 (가명)</div>", unsafe_allow_html=True)
            if rows:
                cohort = pd.DataFrame([{"가명 코드": r["code"], "임상 진단": r["dx"], "HAM-D": r["hamd"], "나이대": r["age_group"],
                                        "성별": r["sex"], "검사 횟수": r["n_labs"], "출처": "시연" if r["demo"] else "진료"} for r in rows])
                st.dataframe(cohort, hide_index=True, width="stretch")
                st.download_button("코호트 내보내기 (CSV)", cohort.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="research_cohort.csv", mime="text/csv", icon=":material/download:")
            else:
                st.caption("포함 조건(연구 활용 동의 · 임상 진단 · 검사 기록)을 충족한 환자가 없습니다.")
            st.markdown("<div class='foot'>포함 조건: 연구 활용 동의 + 임상 진단(MDD/비MDD) + 검사 기록 1회 이상. 이름·대화 내용 제외, 가명 코드 사용.</div>",
                        unsafe_allow_html=True)
    st.stop()

if not RE:
    with main:
        st.error("research_evidence.json이 없습니다. analysis/research_checkup.py를 실행해 주세요.")
    st.stop()

# ---------------------------------------------------------------- 공공 코호트 결과
V = V_all.copy()
V["sig"] = V["q"] < q_thr
mask = V["stability"] >= min_stab
if groups:
    mask &= V["group"].isin(groups)
if tiers:
    mask &= V["tier"].isin(tiers)
if query.strip():
    mask &= V["label"].str.contains(query.strip(), case=False, regex=False)
F = V[mask]

with main:
    a = RE["auc"]
    st.markdown(
        "<div class='kpis'>"
        f"<div class='kpi'><span>탐색 항목</span><b>{len(V)}</b><small>필터 후 {len(F)}</small></div>"
        f"<div class='kpi'><span>유의 (q &lt; {q_thr:g})</span><b>{int(V['sig'].sum())}</b><small>개</small></div>"
        f"<div class='kpi'><span>유망 후보</span><b>{int((V['tier'] == '유망 후보').sum())}</b><small>개</small></div>"
        f"<div class='kpi'><span>예측 AUC</span><b>{a['full_mean']:.3f}</b><small>±{a['full_sd']:.3f}</small></div>"
        f"<div class='kpi'><span>기준 모델 AUC</span><b>{a['base_mean']:.3f}</b><small>나이·성별</small></div></div>",
        unsafe_allow_html=True)
    tab_res, tab_forest, tab_n, tab_model, tab_precise, tab_method = st.tabs(
        ["탐색 결과", "후보 비교", "표본 크기 분석", "예측 모델", "정밀 검사 지표", "방법 · 제한점"])

    # ---- 탐색 결과: 볼케이노 + 표
    with tab_res:
        fig = go.Figure()
        for tier in TIERS:
            sub = V[V["tier"] == tier]
            on = sub.index.isin(F.index)
            fig.add_trace(go.Scatter(
                x=sub["or"], y=-sub["q"].clip(lower=1e-12).map(math.log10), mode="markers+text", name=tier,
                marker=dict(size=9 + 14 * sub["stability"], color=TIER_COLOR[tier], opacity=[1 if o else .18 for o in on],
                            line=dict(width=1, color="#fff")),
                text=[lbl if (tier == "유망 후보" and o) else "" for lbl, o in zip(sub["label"], on)], textposition="top center",
                customdata=sub[["label", "or_lo", "or_hi", "q", "stability", "n"]].to_numpy(),
                hovertemplate="<b>%{customdata[0]}</b><br>OR %{x:.2f} (%{customdata[1]:.2f}–%{customdata[2]:.2f})"
                              "<br>q %{customdata[3]:.4f} · 안정성 %{customdata[4]:.0%} · n %{customdata[5]}<extra></extra>"))
        fig.add_hline(y=-math.log10(q_thr), line_dash="dot", line_color="#64748B", annotation_text=f"q = {q_thr:g}")
        fig.add_vline(x=1, line_color="#CBD5E1")
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff", font=FONT,
                          xaxis=dict(title="Odds ratio per 1 SD (age·sex adjusted)", type="log", gridcolor="#EEF2F8"),
                          yaxis=dict(title="-log10 FDR q", gridcolor="#EEF2F8"), legend=dict(orientation="h", y=1.06))
        st.plotly_chart(fig, width="stretch")
        sort_by = st.radio("정렬", ["FDR q", "오즈비 효과 크기", "선택 안정성"], horizontal=True, key="rs_sort")
        if sort_by == "FDR q":
            F = F.sort_values("q")
        elif sort_by == "오즈비 효과 크기":
            F = F.assign(_e=(F["or"].map(math.log)).abs()).sort_values("_e", ascending=False)
        else:
            F = F.sort_values("stability", ascending=False)
        table = pd.DataFrame({
            "항목": F["label"], "분류": F["group"], "판정": F["tier"], "OR": F["or"].round(2),
            "95% CI": [f"{lo:.2f}–{hi:.2f}" for lo, hi in zip(F["or_lo"], F["or_hi"])],
            "q": F["q"].round(4), "안정성": F["stability"], "사례군 평균": F["mean_pos"], "대조군 평균": F["mean_neg"],
            "단위": F["unit"], "n": F["n"]})
        st.dataframe(table, hide_index=True, width="stretch", height=380,
                     column_config={"안정성": st.column_config.ProgressColumn("안정성", min_value=0, max_value=1, format="%.2f"),
                                    "q": st.column_config.NumberColumn("FDR q", format="%.4f")})
        st.download_button("결과 내보내기 (CSV)", table.to_csv(index=False).encode("utf-8-sig"), file_name="biomarker_screening.csv",
                           mime="text/csv", icon=":material/download:")

    # ---- 후보 비교: 포레스트 플롯 + 항목 상세
    with tab_forest:
        Fs = F.sort_values("or")
        ff = go.Figure()
        ff.add_trace(go.Scatter(x=Fs["or"], y=Fs["label"], mode="markers",
                                marker=dict(size=10, color=[TIER_COLOR[t] for t in Fs["tier"]]),
                                error_x=dict(type="data", symmetric=False, array=Fs["or_hi"] - Fs["or"], arrayminus=Fs["or"] - Fs["or_lo"],
                                             color="#94A3B8", thickness=1.5),
                                customdata=Fs[["q", "stability"]].to_numpy(),
                                hovertemplate="%{y}<br>OR %{x:.2f}<br>q %{customdata[0]:.4f} · 안정성 %{customdata[1]:.0%}<extra></extra>"))
        ff.add_vline(x=1, line_color="#64748B", line_dash="dot")
        ff.update_layout(height=max(320, 26 * len(Fs) + 80), margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff",
                         paper_bgcolor="#fff", font=FONT, showlegend=False,
                         xaxis=dict(title="Odds ratio (95% CI)", type="log", gridcolor="#EEF2F8"), yaxis=dict(gridcolor="#F3F5FA"))
        st.plotly_chart(ff, width="stretch")
        if len(F):
            pick = st.selectbox("항목 상세", F["label"].tolist(), key="rs_pick")
            r = F[F["label"] == pick].iloc[0]
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("OR (1 SD)", f"{r['or']:.2f}", f"{r['or_lo']:.2f}–{r['or_hi']:.2f}", delta_color="off")
            m2.metric("FDR q", "<0.001" if r["q"] < 0.001 else f"{r['q']:.3f}")
            m3.metric("선택 안정성", f"{r['stability']:.0%}")
            m4.metric("사례군 / 대조군 평균", f"{r['mean_pos']:g} / {r['mean_neg']:g}", r["unit"] or None, delta_color="off")
            m5.metric("분석 인원", f"{r['n']:,}", f"사례 {r['n_pos']}", delta_color="off")
            st.caption(f"분류 {r['group']} · 판정 {r['tier']} · {'로그 변환 후 표준화' if r['log'] else '표준화'} · 나이·성별 보정 로지스틱 회귀")

    # ---- 표본 크기 분석
    with tab_n:
        G = pd.DataFrame(RE["growth"])
        g1, g2 = st.columns(2)
        f1 = go.Figure(go.Bar(x=G["n"].map(lambda n: f"{n:,}"), y=G["discoveries_mean"], marker_color="#4F6BD3",
                              error_y=dict(type="data", array=G["discoveries_sd"], visible=True),
                              text=G["discoveries_mean"].map(lambda v: f"{v:.1f}"), textposition="outside"))
        f1.update_layout(title=f"유의 항목 수 (q < 0.05)", height=340, margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="#fff",
                         paper_bgcolor="#fff", font=FONT, xaxis=dict(title="표본 수"), yaxis=dict(gridcolor="#EEF2F8"))
        g1.plotly_chart(f1, width="stretch")
        f2 = go.Figure(go.Scatter(x=G["n"], y=G["auc_mean"], mode="lines+markers", line=dict(color="#2F9E8F", width=3),
                                  error_y=dict(type="data", array=G["auc_sd"], visible=True)))
        f2.add_hline(y=0.5, line_dash="dot", line_color="#94A3B8")
        f2.update_layout(title="교차검증 AUC", height=340, margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff",
                         font=FONT, xaxis=dict(title="표본 수", gridcolor="#EEF2F8"), yaxis=dict(range=[0.45, 0.75], gridcolor="#EEF2F8"))
        g2.plotly_chart(f2, width="stretch")
        st.dataframe(pd.DataFrame({"표본 수": G["n"], "사례 수(추정)": G["n_pos"], "반복": G["reps"],
                                   "유의 항목 평균": G["discoveries_mean"].round(1), "SD": G["discoveries_sd"].round(1),
                                   "AUC 평균": G["auc_mean"].round(3), "AUC SD": G["auc_sd"].round(3)}),
                     hide_index=True, width="stretch")
        st.caption("층화 무작위 부분표본(사례 비율 유지)으로 연관성 분석과 5겹 교차검증을 반복했습니다. 전체 표본은 1회.")

    # ---- 예측 모델
    with tab_model:
        p1, p2, p3 = st.columns(3)
        p1.metric("검진 항목 + 나이·성별", f"{a['full_mean']:.3f}", f"{a['full_mean'] - a['base_mean']:+.3f} vs 기준", delta_color="normal")
        p2.metric("기준 모델 (나이·성별)", f"{a['base_mean']:.3f}", f"±{a['base_sd']:.3f}", delta_color="off")
        p3.metric("사례 비율", f"{RE['prevalence'] * 100:.1f}%", f"{RE['n_pos']} / {RE['n']:,}", delta_color="off")
        st.markdown(f"<div class='kv' style='margin-top:8px'><span>모델</span><b>{esc(RE['method']['model'])}</b>"
                    f"<span>입력</span><b>검진 항목 {len(V)}개 + 나이, 성별 (정신건강 설문 항목 제외)</b>"
                    f"<span>평가</span><b>AUC 평균 ± SD (5회 반복)</b></div>", unsafe_allow_html=True)

    # ---- 정밀 검사 지표 (CDSS 모델 데이터)
    with tab_precise:
        if ME:
            q1, q2 = st.columns(2)
            for col, mid, used in ((q1, "eeg", 10), (q2, "metabolites", 5)):
                m = ME["modalities"][mid]
                col.markdown(f"<div class='lbl'>{esc(m['label'])} · n={m['n_mdd'] + m['n_control']}</div>", unsafe_allow_html=True)
                c_a, c_b, c_c = col.columns(3)
                c_a.metric("검사 지표", f"{m['n_tested']:,}")
                c_b.metric("FDR < 0.05", m["n_fdr05"])
                c_c.metric("CDSS 모델 사용", used)
                col.dataframe(pd.DataFrame([{"지표": r["label"], "r": round(r["r"], 3), "d": round(r["d"], 2),
                                             "FDR q": "<0.001" if r["q"] < 0.001 else f"{r['q']:.3f}"} for r in m["associations"]]),
                              hide_index=True, width="stretch")

    # ---- 방법 · 제한점
    with tab_method:
        mm = RE["method"]
        st.markdown(f"<div class='kv'><span>자료</span><b>{esc(RE['source'])}</b><span>대상</span><b>{esc(RE['population'])}</b>"
                    f"<span>결과 변수</span><b>{esc(RE['label'])}</b><span>연관성</span><b>{esc(mm['assoc'])}</b>"
                    f"<span>안정성</span><b>{esc(mm['stability'])}</b><span>판정</span><b>{esc(mm['tier'])}</b>"
                    f"<span>예측 모델</span><b>{esc(mm['model'])}</b></div>", unsafe_allow_html=True)
        st.markdown("<div class='lbl' style='margin-top:14px'>제한점</div>" + "".join(f"<div style='font-size:.85rem;color:#334155'>· {esc(t)}</div>"
                    for t in RE["limits"]), unsafe_allow_html=True)
        st.caption(f"출처 표기: {RE['source']}. 재현: analysis/research_checkup.py")
