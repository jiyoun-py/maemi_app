# 환자용 플랫폼(마음이) ↔ 의사용 플랫폼 연동 가이드

두 앱은 **같은 공유 폴더의 파일**을 읽고 써서 연결돼요. 서버나 DB 없이 동작하는 시연용 구조예요.

## 1. 실행 방법

**한 번에 실행 (권장, Streamlit Cloud와 같은 구조):** `streamlit run streamlit_app.py` → 환자용 `/`, 의사용 `/doctor`. 배포는 `DEPLOY.md`를 보세요.

또는 두 앱을 각각 다른 터미널에서 실행해요. 포트만 다르게 하면 돼요.

```
# 환자용 (maeumi_app 폴더)
streamlit run app.py

# 의사용 (의사용 폴더)
streamlit run doctor_app.py --server.port 8502
```

- 두 앱은 **같은 공유 폴더**를 써야 해요. 기본값은 `내 계정 폴더\maeumi_shared`(예: `C:\Users\이름\maeumi_shared`)이고, 같은 컴퓨터·같은 Windows 계정에서 실행하면 따로 설정할 게 없어요.
- 다른 위치를 쓰려면 두 앱을 실행하기 전에 환경변수를 지정해요. (PowerShell)
  ```
  $env:MAEUMI_SHARED_DIR = "D:\maeumi_shared"
  ```
- 컴퓨터 두 대로 시연한다면 OneDrive/구글 드라이브처럼 동기화되는 폴더를 지정하면 돼요. 다만 동기화 지연(수 초~수십 초)이 있어요.

## 2. 데이터 흐름

| 방향 | 내용 | 파일 | 의사용 화면에서 |
|---|---|---|---|
| 환자 → 의사 | 상담 요청 | `consultation_req.txt` | 우측 "실시간 상담 요청"에 요청 표시, "상담 수락" |
| 환자 → 의사 | 환자 정보(이름·만 나이·성별·키·몸무게) | `patient_profile.json` | "환자 프로필" |
| 환자 → 의사 | 긴급 위험 알림 | `alerts.json` | "실시간 상담 요청" 안에 긴급 알림 + "확인" 버튼 |
| 환자 → 의사 | 위험 단계, PHQ-9, 수면 중간점, HRV, 주요 신호 | `alerts.json`, `checkins.json`, `bio_report.json` | "환자 앱 모니터링" |
| 의사 → 환자 | 상담 수락 | 요청 줄 삭제 + `appointments.json`(status) | 환자 앱 "내 예약"이 **확정**으로 바뀜 + 알림 |
| 의사 → 환자 | 의료진이 직접 등록한 일정 | `appointments.json` | 환자 앱 "내 예약"에 표시 + 알림 |
| 의사 → 환자 | 긴급 알림 확인 | `alerts.json`(status=acknowledged) | 환자 앱에 "담당 의료진이 알림을 확인했어요" |
| 의사 → 환자 | 진단 결과 확정 및 전송 | `diagnosis_report.json` | 환자 앱 "내 상태 > 소견" + 마음이가 소견을 반영해 대화 |

환자 앱은 4초마다 공유 파일을 확인해서, 의사용에서 무언가 바뀌면 화면을 자동으로 새로 고쳐요.

## 3. 파일 형식

### consultation_req.txt (한 줄에 요청 하나)
```
2026-11-08|10:00|[긴급] 장수정 · 위기 신호 감지(대화)
```
`날짜|시간|사유` 3칸이에요. 기존 의사용 코드의 파싱(`len(parts) == 3`)과 그대로 호환돼요. 사유 안의 `|`와 줄바꿈은 환자 앱이 미리 지워요. 칸을 늘리면 기존 코드가 요청을 무시하니 3칸을 유지해 주세요.

### patient_profile.json (환자 앱이 쓰고 의사용이 읽음)
```json
{ "P-ab12cd": { "name": "장수정", "age": 22, "sex": "여성",
                "height_cm": 165, "weight_kg": 52, "updated": "2026-11-08 10:00:00" } }
```
의사용 "환자 목록"은 `updated`가 최근인 순서로 정렬돼요. 환자가 입력하지 않은 항목은 `null`이에요.

### appointments.json
```json
{ "id": "a1b2c3d4", "patient_id": "P-ab12cd", "date": "2026-11-08", "time": "10:00",
  "status": "requested", "priority": "urgent", "reason": "...", "source": "마음이 대화" }
```
- 환자 앱이 `status: "requested"`로 만들고, 의사용이 수락하면 `"confirmed"`로 바꿔요.
- 의사용이 직접 등록한 일정은 `time: ""`, `source: "의료진 등록"`, `status: "confirmed"`예요.

### alerts.json (환자 앱이 쓰고, 의사용이 `status`만 변경)
주요 필드: `id`, `patient_id`, `time`, `level`(low/medium/high), `care_step`(crisis/doctor/self), `priority`(urgent/normal/routine), `trigger_message`, `status`(unread/digest/acknowledged), `recommended_action`.
- `priority: "urgent"`이고 `status`가 `acknowledged`가 아니면 긴급 알림으로 표시해요.

### checkins.json
PHQ-9 기록: `patient_id`, `time`, `total`(0~27), `severity`, `item9`(9번 문항 점수), `answers`(9개).

### bio_report.json
`circadian`(수면 중간점·이동·규칙성), `hrv_rmssd`(기준선 대비 변화), `biomarkers`(지표별 z값·상태), `risk_signal`(관심 단계, 요인별 기여도). 시연용 가상 데이터예요.

### diagnosis_report.json (의사용이 쓰고 환자 앱이 읽음)
```json
{ "P-ab12cd": [ {
  "report_id": "e5f6g7h8", "sent": "2026-11-08 10:30:00",
  "patient_id": "P-ab12cd", "patient_name": "장수정",
  "modalities": [ { "id": "eeg", "name": "EEG", "probability": 65.0, "judgement": "고위험",
                    "details": [ {"item": "Alpha/Beta Ratio", "value": "1.10"} ] } ],
  "fusion": { "probability": 57, "label": "중등도 우울 위험군", "comment": "..." },
  "doctor_memo": "1. 생체 시계 정상화를 위한 수면 루틴 지도 ..." } ] }
```
`id`는 `eeg`, `metabolites`, `cytokine`, `cortisol` 4가지를 써 주세요. 환자 앱에는 의사 소견(`doctor_memo`)이 먼저 보이고, 종합 확률은 "의료진과 함께 더 자세히 살펴볼 필요가 있어요" 같은 순화된 문구로 표시돼요.

## 4. 의사용 플랫폼 디자인 개편 (doctor_app.py)

기존 요구서(탭 없이 한 화면, 십자 4분할, 우측 환자 관리 창, 제목·안내 문구 없음)는 그대로 지키고, 환자용과 같은 블루 톤의 의료기관 프로그램 모양으로 다듬었어요. 진단 확률과 분석 요약은 `model_evidence.json`의 근거 모델로 계산해요.

**우측 패널 (위에서 아래)**: 환자 프로필(이름·만 나이·성별·키·몸무게, BMI, 위험 단계·PHQ-9 칩) → 실시간 상담 요청(새 요청이 오면 화면에 팝업 알림) → 진료 및 상담 일정(월 달력, 일정 표시 점) → 해당 환자 진료 기록 → 환자 데이터 업로드(가장 하단)

**메인 패널**
- 십자선 4분할: 좌상 EEG, 우상 Metabolites, 좌하 Cytokine, 우하 Cortisol. 각 칸에 MDD 확률 게이지와 세부 항목 TOP 3
- 융합 진단: 4개 바이오마커 레이더 차트, 통합 확률 게이지, 고위험 판정 수·평균·편차 통계, AI 임상 소견, 처방 소견 입력, 전송 버튼
- 임상 추이(환자 앱 연동): PHQ-9 추이(구간 색 띠), 수면·걸음·안정시 심박·HRV 7일 추이
- 설명 가능성과 모델 성능: 위험 신호 요인별 기여도(그룹별 비중), ROC 곡선과 AUC·민감도 표

그래프는 외부 라이브러리 없이 직접 그린 SVG라서 어떤 환경에서도 선명하게 보여요.

**연동 관련 변경 (환자 앱과 데이터 주고받기)**
- 공유 폴더 설정과 읽기·쓰기 함수 (파일 상단, `[연동]` 표시)
- 상담 수락 시 `confirm_appointment()`, 일정 등록 시 `add_doctor_appointment()`, 긴급 알림 확인 시 `ack_alert()`
- "진단 결과 확정 및 환자 플랫폼 전송"이 `diagnosis_report.json`에 저장
- AI 소견 문장에 섞여 있던 `[cite: n]` 표시 제거

**근거 모델은 `model_evidence.json`에서 읽어요.** `analysis/train_evidence.py`가 데이터 4종에서 지표별 연관성(r, d, FDR q), 모델 계수, 교차검증 AUC와 ROC 점을 계산해 저장해요. 데이터를 바꾸면 이 스크립트를 다시 실행하면 돼요. (`scikit-learn`, `scipy`, `openpyxl` 필요)

- 환자 파일은 **첫 행 1명**을 읽고, 모델에 필요한 컬럼이 모두 있는 모달리티만 계산해요. 빠진 값은 채우지 않아요. 형식은 `demo_data/`의 시연 CSV를 참고해요.
- 통합 점수는 학습이 아닌 규칙(로짓 동일 가중 평균)이고 정확도가 검증되지 않았어요. 같은 환자의 4종 자료가 없기 때문이에요.
- 시뮬레이션 코르티솔은 통합에서 기본 제외돼요. 업로드 카드의 토글로 포함할 수 있어요.

**`bio_report.json`에 `series`(7일 추이)가 추가**되어서, 환자 앱도 최신 버전(`app.py`)을 써야 의사용 추이 그래프가 나와요.

## 5. 알아둘 점

- **여러 환자를 볼 수 있어요.** 의사용 우측 상단 "환자 목록"에 환자 앱을 사용한 모든 환자가 최근 순으로 나오고, 누르면 그 환자의 프로필·일정·추이·업로드·소견 전송 대상이 바뀌어요. 긴급 알림과 상담 요청은 선택과 상관없이 모든 환자의 것이 보여요. 환자 ID는 이름에서 만들어서, 같은 이름은 같은 환자로 봐요. 실제 서비스라면 로그인과 환자 식별이 필요해요.
- **의사용도 새로고침 없이 갱신돼요.** 2초마다 공유 파일을 확인해서 바뀌었을 때만 화면을 다시 그려요. (추가 패키지 불필요)
- 공유 폴더의 파일은 암호화되지 않은 일반 파일이에요. 시연용 구조이고, 실제 서비스에서는 DB, 접근 권한, 개인정보 동의가 필요해요.
- 환자 앱 사이드바(개발용)에 "의사용 플랫폼 연동 시연" 버튼이 있어서, 의사용 앱 없이도 수락·소견 도착 화면을 점검할 수 있어요.
- 의사용에서 요청을 수락하면 환자 앱의 "내 예약"이 **확정**으로 바뀌고 알림이 떠요. 환자 앱이 열려 있으면 4초 안에 자동으로 반영돼요.
