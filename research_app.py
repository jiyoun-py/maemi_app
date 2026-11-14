"""연구 모드 (/research): 의사 연구자를 위한 바이오마커 탐색 화면.

- 기관 축적 현황: 연구 활용에 동의 + 임상 진단 + 검사 기록이 있는 환자만 가명 코드로 집계
- 건강검진 기반 탐색: 국민건강영양조사 2024로 미리 계산한 결과(research_evidence.json, analysis/research_checkup.py)
- 데이터 증가 시나리오, 2단계 선별 흐름, 정밀 검사 후보, 실제 적용 조건
"""
import html
import json
import math
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from maeumi_common import BASE_DIR, research_dataset

st.set_page_config(page_title="연구 모드 · 마음이 CDSS", page_icon="🔬", layout="wide")
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
.stApp, .stApp p, .stApp label, .stApp li, .stApp button{font-family:'Pretendard','Noto Sans KR','Malgun Gothic',sans-serif !important;}
.stApp{background:#F4F6FB;}
[data-testid="stToolbar"], #MainMenu, footer{display:none !important;}
header[data-testid="stHeader"]{display:none !important;}
.block-container, [data-testid="stMainBlockContainer"]{max-width:1400px !important;padding-top:2.2rem !important;}
.rs-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
.rs-title{font-size:1.6rem;font-weight:800;color:#0F172A;}
.rs-sub{color:#64748B;font-size:.9rem;}
.chip{display:inline-block;font-size:.74rem;font-weight:700;padding:3px 10px;border-radius:999px;margin-right:4px;}
.chip-warn{background:#FEF3C7;color:#92400E;} .chip-ok{background:#DFF3F0;color:#17695E;} .chip-info{background:#E8EEFF;color:#2F3F8F;}
.chip-muted{background:#EEF2F7;color:#475569;}
.sec{font-size:1.15rem;font-weight:800;color:#2F3F8F;margin:22px 0 4px;}
.sec-sub{color:#64748B;font-size:.86rem;margin-bottom:10px;}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:6px 0 10px;}
.kpi{background:#fff;border:1px solid #E2E8F3;border-radius:12px;padding:12px 14px;}
.kpi span{display:block;font-size:.74rem;color:#64748B;font-weight:700;} .kpi b{font-size:1.35rem;color:#0F172A;}
.kpi small{color:#64748B;font-size:.74rem;}
.box{background:#fff;border:1px solid #E2E8F3;border-radius:14px;padding:14px 16px;margin-bottom:10px;}
.note{background:#FFF7E6;border-left:4px solid #F5A524;border-radius:10px;padding:10px 14px;font-size:.88rem;color:#334155;margin:8px 0;}
.flow{display:flex;gap:8px;align-items:stretch;flex-wrap:wrap;}
.flow .st{flex:1;min-width:170px;background:#fff;border:1px solid #E2E8F3;border-radius:12px;padding:12px;}
.flow .st b{display:block;color:#2F3F8F;margin-bottom:4px;} .flow .st div{font-size:.84rem;color:#334155;}
.flow .ar{display:flex;align-items:center;color:#94A3B8;font-weight:800;}
.flow .now{border:2px solid #4F6BD3;}
.chk li{margin:4px 0;color:#334155;font-size:.9rem;}
.stApp [data-testid="stMarkdownContainer"] p{color:#0F172A;}
</style>""", unsafe_allow_html=True)
esc = html.escape


def load(name):
    try:
        with open(os.path.join(BASE_DIR, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


RE = load("research_evidence.json")
ME = load("model_evidence.json")

st.markdown("<div class='rs-head'><div><div class='rs-title'>🔬 연구 모드 · 바이오마커 탐색</div>"
            "<div class='rs-sub'>진료 중 쌓이는 데이터로 새로운 우울증 바이오마커 후보를 찾는 과정을 보여줘요.</div></div>"
            "<div><span class='chip chip-warn'>연구 시뮬레이션</span><span class='chip chip-info'>개인 식별 정보 없음</span></div></div>",
            unsafe_allow_html=True)
st.markdown("🩺 [의료진 화면으로 돌아가기](/doctor)")

# ---------------------------------------------------------------- 1. 기관 축적 현황
st.markdown("<div class='sec'>1. 우리 기관에 쌓인 연구 데이터</div>"
            "<div class='sec-sub'>연구 활용에 동의했고, 의사가 임상 진단을 기록했고, 검사 기록이 있는 환자만 가명 코드로 집계해요. "
            "이름·대화 내용은 포함하지 않아요.</div>", unsafe_allow_html=True)
rows, excl = research_dataset()
n_mdd = sum(r["dx"] == "MDD" for r in rows)
n_non = sum(r["dx"] == "비MDD" for r in rows)
TARGET = 30
st.markdown(
    "<div class='kpis'>"
    f"<div class='kpi'><span>연구 데이터</span><b>{len(rows)}명</b><small>가명 코드</small></div>"
    f"<div class='kpi'><span>MDD</span><b>{n_mdd}명</b><small>목표 {TARGET}명</small></div>"
    f"<div class='kpi'><span>비MDD</span><b>{n_non}명</b><small>목표 {TARGET}명</small></div>"
    f"<div class='kpi'><span>제외: 연구 미동의</span><b>{excl['no_consent']}명</b></div>"
    f"<div class='kpi'><span>제외: 진단·검사 없음</span><b>{excl['no_dx'] + excl['no_lab']}명</b></div></div>",
    unsafe_allow_html=True)
c1, c2 = st.columns(2)
c1.progress(min(n_mdd / TARGET, 1.0), text=f"MDD {n_mdd}/{TARGET}명")
c2.progress(min(n_non / TARGET, 1.0), text=f"비MDD {n_non}/{TARGET}명")
if rows:
    with st.expander(f"가명 연구 데이터 목록 ({len(rows)}명)"):
        st.dataframe(pd.DataFrame([{"가명 코드": r["code"], "임상 진단": r["dx"], "HAM-D": r["hamd"], "나이대": r["age_group"],
                                    "성별": r["sex"], "검사 횟수": r["n_labs"], "시연": "시연" if r["demo"] else ""} for r in rows]),
                     hide_index=True, width="stretch")
st.markdown("<div class='note'>그룹별 목표 인원이 모이면 같은 분석 과정으로 기관 데이터를 다시 계산해요. 지금은 인원이 적어서, "
            "아래에서 <b>국민건강영양조사 실제 자료</b>로 같은 과정을 미리 보여드려요.</div>", unsafe_allow_html=True)

if not RE:
    st.error("research_evidence.json이 없어요. analysis/research_checkup.py를 먼저 실행해 주세요.")
    st.stop()

# ---------------------------------------------------------------- 2. 건강검진 기반 탐색
V = pd.DataFrame(RE["variables"])
n_prom = int((V["tier"] == "유망 후보").sum())
st.markdown("<div class='sec'>2. 건강검진 항목으로 찾은 우울 증상 바이오마커 후보</div>"
            f"<div class='sec-sub'>{esc(RE['source'])} · {esc(RE['population'])} · 정답: {esc(RE['label'])}</div>",
            unsafe_allow_html=True)
a = RE["auc"]
st.markdown(
    "<div class='kpis'>"
    f"<div class='kpi'><span>분석 대상</span><b>{RE['n']:,}명</b></div>"
    f"<div class='kpi'><span>우울 증상 (PHQ-9 ≥ 10)</span><b>{RE['n_pos']}명</b><small>{RE['prevalence'] * 100:.1f}%</small></div>"
    f"<div class='kpi'><span>탐색한 검진 항목</span><b>{RE['n_vars']}개</b></div>"
    f"<div class='kpi'><span>유망 후보</span><b>{n_prom}개</b><small>보정 후 유의 + 안정적</small></div>"
    f"<div class='kpi'><span>예측 AUC</span><b>{a['full_mean']:.2f}</b><small>나이·성별만 {a['base_mean']:.2f}</small></div></div>",
    unsafe_allow_html=True)

TIER_COLOR = {"유망 후보": "#E5484D", "검토 필요": "#F5A524", "근거 약함": "#94A3B8"}
fig = go.Figure()
for tier, color in TIER_COLOR.items():
    sub = V[V["tier"] == tier]
    fig.add_trace(go.Scatter(
        x=sub["or"], y=-sub["q"].clip(lower=1e-12).map(math.log10), mode="markers+text",
        name=tier, marker=dict(size=10 + 14 * sub["stability"], color=color, line=dict(width=1, color="#fff")),
        text=[lbl if tier == "유망 후보" else "" for lbl in sub["label"]], textposition="top center", textfont=dict(size=12),
        customdata=sub[["label", "or_lo", "or_hi", "q", "stability"]].to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b><br>오즈비 %{x:.2f} (%{customdata[1]:.2f}–%{customdata[2]:.2f})"
                      "<br>FDR q %{customdata[3]:.4f}<br>선택 안정성 %{customdata[4]:.0%}<extra></extra>"))
fig.add_hline(y=-math.log10(0.05), line_dash="dot", line_color="#64748B", annotation_text="q = 0.05")
fig.add_vline(x=1, line_color="#CBD5E1")
fig.update_layout(height=470, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff",
                  xaxis=dict(title="오즈비 (1 표준편차 증가당, 1보다 크면 우울 증상과 함께 높음)", type="log", gridcolor="#EEF2F8"),
                  yaxis=dict(title="통계적 유의성 (-log10 q, 위로 갈수록 강함)", gridcolor="#EEF2F8"),
                  legend=dict(orientation="h", y=1.08), font=dict(family="Pretendard, Malgun Gothic, sans-serif"))
st.plotly_chart(fig, width="stretch")
st.caption("점 하나가 검진 항목 하나예요. 오른쪽 위로 갈수록 '높을수록 우울 증상과 관련', 왼쪽 위는 '낮을수록 관련'이에요. "
           "점이 클수록 데이터를 바꿔 다시 분석해도 꾸준히 선택된(선택 안정성이 높은) 항목이에요.")

tiers = st.multiselect("판정으로 거르기", list(TIER_COLOR), default=["유망 후보", "검토 필요"])
show = V[V["tier"].isin(tiers)]
table = pd.DataFrame({
    "검진 항목": show["label"], "분류": show["group"], "판정": show["tier"],
    "오즈비 (95% 구간)": [f"{r.or_:.2f} ({r.or_lo:.2f}–{r.or_hi:.2f})" for r in show.rename(columns={"or": "or_"}).itertuples()],
    "FDR q": show["q"].map(lambda q: "<0.001" if q < 0.001 else f"{q:.3f}"),
    "선택 안정성": show["stability"].map(lambda s: f"{s:.0%}"),
    "우울군 평균": show["mean_pos"], "비우울군 평균": show["mean_neg"], "단위": show["unit"], "분석 인원": show["n"]})
st.dataframe(table, hide_index=True, width="stretch")
st.download_button("후보 목록 CSV 내려받기", table.to_csv(index=False).encode("utf-8-sig"), file_name="biomarker_candidates.csv",
                   mime="text/csv", icon=":material/download:")
top = V[V["tier"] == "유망 후보"]
if len(top):
    ex = top.iloc[0]
    st.markdown(f"<div class='box'><b>읽는 법</b> · 예를 들어 '{esc(ex['label'])} 오즈비 {ex['or']:.2f}'는 나이·성별이 같을 때 "
                f"{esc(ex['label'])}가 1 표준편차 높으면 우울 증상(PHQ-9 ≥ 10)일 오즈가 {ex['or']:.2f}배라는 뜻이에요. "
                "<b>유망 후보</b>는 여러 항목을 함께 검사한 보정(FDR) 후에도 의미 있고, 다시 뽑아 분석해도 60% 이상 선택된 항목이에요. "
                "관련성일 뿐 원인은 아니며, 다음 단계에서 검증할 '가설'이에요.</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- 3. 데이터 증가 시나리오
st.markdown("<div class='sec'>3. 데이터가 쌓일수록 무엇이 달라질까</div>"
            "<div class='sec-sub'>같은 자료에서 일부 인원만 무작위로 뽑아 분석을 반복했어요(전체 제외 20회). 진료 데이터가 쌓이는 상황을 흉내 낸 거예요.</div>",
            unsafe_allow_html=True)
G = pd.DataFrame(RE["growth"])
g1, g2 = st.columns(2)
f1 = go.Figure(go.Bar(x=G["n"].map(lambda n: f"{n:,}명"), y=G["discoveries_mean"], marker_color="#4F6BD3",
                      error_y=dict(type="data", array=G["discoveries_sd"], visible=True),
                      text=G["discoveries_mean"].map(lambda v: f"{v:.1f}개"), textposition="outside"))
f1.update_layout(title="보정 후 의미 있는 후보 수", height=330, margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="#fff",
                 paper_bgcolor="#fff", yaxis=dict(gridcolor="#EEF2F8"), font=dict(family="Pretendard, Malgun Gothic, sans-serif"))
g1.plotly_chart(f1, width="stretch")
f2 = go.Figure(go.Scatter(x=G["n"], y=G["auc_mean"], mode="lines+markers+text", line=dict(color="#2F9E8F", width=3),
                          error_y=dict(type="data", array=G["auc_sd"], visible=True),
                          text=G["auc_mean"].map(lambda v: f"{v:.2f}"), textposition="top center"))
f2.add_hline(y=0.5, line_dash="dot", line_color="#94A3B8", annotation_text="우연 수준 0.5")
f2.update_layout(title="예측 AUC (교차검증)", height=330, margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="#fff",
                 paper_bgcolor="#fff", xaxis=dict(title="분석 인원", gridcolor="#EEF2F8"), yaxis=dict(range=[0.45, 0.75], gridcolor="#EEF2F8"),
                 font=dict(family="Pretendard, Malgun Gothic, sans-serif"))
g2.plotly_chart(f2, width="stretch")
first, last = G.iloc[0], G.iloc[-1]
st.markdown(f"<div class='box'>{int(first['n']):,}명일 때는 의미 있는 후보가 평균 {first['discoveries_mean']:.1f}개였지만, "
            f"{int(last['n']):,}명에서는 {last['discoveries_mean']:.0f}개로 늘었어요. 예측 AUC도 {first['auc_mean']:.2f} → {last['auc_mean']:.2f}로 올라요. "
            "<b>데이터가 쌓일수록 숨어 있던 작은 신호가 드러난다</b>는 것이 진료 데이터를 모으는 이유예요. "
            "다만 검진 수치만으로는 예측력이 크지 않아서, 정밀 바이오마커와 함께 쓰는 2단계 구조가 필요해요.</div>",
            unsafe_allow_html=True)

# ---------------------------------------------------------------- 4. 2단계 선별 흐름
st.markdown("<div class='sec'>4. 목표: 건강검진에서 시작하는 2단계 우울증 선별</div>", unsafe_allow_html=True)
st.markdown("""<div class='flow'>
<div class='st'><b>① 매년 건강검진</b><div>혈액·소변·신체계측 + PHQ-9 등 기본 설문</div></div><div class='ar'>→</div>
<div class='st'><b>② 1차 위험 신호</b><div>이 페이지의 후보 항목(예: 허리둘레·혈당·염증·마그네슘)으로 위험군 표시</div></div><div class='ar'>→</div>
<div class='st now'><b>③ 정밀 바이오마커 검사</b><div>EEG·대사체·사이토카인·코르티솔 — 마음이 CDSS 화면</div></div><div class='ar'>→</div>
<div class='st'><b>④ 진료와 일상 케어</b><div>의사 진단·처방, 환자 앱 마음이의 일상 관리</div></div><div class='ar'>→</div>
<div class='st'><b>⑤ 동의한 데이터 환류</b><div>가명 처리 후 연구 데이터로 쌓여 후보를 다시 검증</div></div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 5. 정밀 검사 후보
if ME:
    st.markdown("<div class='sec'>5. 정밀 검사에서 아직 쓰지 않은 후보</div>"
                "<div class='sec-sub'>지금 모델은 EEG 10개·대사체 5개 지표만 쓰지만, 보정 후에도 의미 있는 지표는 훨씬 많아요.</div>",
                unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    for col, mid, used in ((p1, "eeg", 10), (p2, "metabolites", 5)):
        m = ME["modalities"][mid]
        col.markdown(f"<div class='box'><b>{esc(m['label'])}</b> · 검사 지표 {m['n_tested']:,}개 중 보정 후 유의 "
                     f"<b>{m['n_fdr05']}개</b> · 모델 사용 {used}개 → <b>미사용 후보 {max(m['n_fdr05'] - used, 0)}개 이상</b></div>",
                     unsafe_allow_html=True)
        col.dataframe(pd.DataFrame([{"지표": r["label"], "상관 r": round(r["r"], 2), "효과크기 d": round(r["d"], 2),
                                     "FDR q": "<0.001" if r["q"] < 0.001 else f"{r['q']:.3f}"} for r in m["associations"][:8]]),
                      hide_index=True, width="stretch")

# ---------------------------------------------------------------- 6. 실제 적용 조건
st.markdown("<div class='sec'>6. 실제 의료기관에서 쓰려면</div>", unsafe_allow_html=True)
k1, k2 = st.columns(2)
k1.markdown("""<div class='box'><b>필요한 조건</b><ul class='chk'>
<li>✅ 환자의 <b>연구 활용 별도 동의</b> (이 앱: 선택 동의 · 언제든 철회)</li>
<li>✅ <b>가명 처리</b> — 이름·대화 제외, 가명 코드만 사용 (이 앱에서 구현)</li>
<li>⬜ <b>AI와 독립적인 진단 라벨</b> — 구조화 면담(SCID·MINI) 또는 전문의 합의</li>
<li>⬜ 같은 환자에게서 <b>여러 검사</b> 수집 → 통합 모델 학습·검증</li>
<li>⬜ 검사 방법 표준화 (장비·채혈 시각·분석 기관)</li>
<li>⬜ <b>IRB 심의</b>, 개인정보 보호 책임자 검토, 외부 기관 검증</li></ul></div>""", unsafe_allow_html=True)
k2.markdown("<div class='box'><b>이 분석의 한계</b><ul class='chk'>"
            + "".join(f"<li>{esc(t)}</li>" for t in RE["limits"])
            + "<li>건강검진 결과는 집단 수준의 관련성이며, 개인 진단에 쓸 수 없음</li></ul></div>", unsafe_allow_html=True)
st.caption(f"출처: {RE['source']}. 분석 방법: {RE['method']['assoc']}; {RE['method']['stability']}; {RE['method']['model']}. "
           f"계산 시각 {RE['generated']}.")
