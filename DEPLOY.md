# Streamlit Cloud 배포 안내

환자용·의사용·연구 모드·관리자가 **한 앱의 네 페이지**로 실행돼요. (`streamlit_app.py`가 시작 파일)

| 화면 | 주소 |
|---|---|
| 환자용 (마음이) | `https://<앱이름>.streamlit.app/` (처음 들어오면 동의 화면: 필수 + 연구 활용 선택) |
| 의사용 (CDSS) | `https://<앱이름>.streamlit.app/doctor` (시연용 계정이 입력된 로그인 화면 → 로그인 클릭) |
| 연구 모드 | `https://<앱이름>.streamlit.app/research` (의사용 화면의 '연구 모드' 버튼) |
| 관리자 (숨김) | `https://<앱이름>.streamlit.app/admin` (Secrets의 `ADMIN_CODE` 입력) |

- **시연 환자 6명:** 저장 공간이 비어 있으면 의료진 화면을 열 때 예시환자 A~F(MDD 3 · 비MDD 3)가 자동으로 만들어져요. 관리자 페이지의 버튼으로도 만들 수 있어요.
- **검사 기록은 환자별로 저장돼요.** 환자를 고르고 파일을 한 번 올리면 다음부터 자동으로 불러와요. 같은 환자에게 또 올리면 다음 회차로 쌓여요.
- **연구 모드:** 국민건강영양조사 2024로 계산한 건강검진 기반 바이오마커 후보(`research_evidence.json`, `analysis/research_checkup.py`)와, 연구 활용에 동의한 환자만 가명으로 모은 기관 데이터 현황을 보여줘요.

관리자 페이지에서 할 수 있는 일: 환자 기록 현황, 시연 환자 만들기, 백업·복원, 환자별 삭제, 전체 리셋, 시연 설정
(의료진 로그인 화면·표시 이름, 통합 점수 기본 검사, 환자 앱 사이드바 시연 도구, 위험도 표시, 시연 환자 자동 생성)

내 PC에서 같은 구조로 실행하려면: `streamlit run streamlit_app.py` → 환자용 `http://localhost:8501`, 의사용 `http://localhost:8501/doctor`
(예전처럼 `app.py`, `doctor_app.py`를 따로 실행해도 돼요.)

## 1. 올릴 파일 모으기
```
venv\Scripts\python.exe make_deploy_folder.py
```
`deploy_upload` 폴더가 만들어져요. `.env`(API 키), `shared/`(환자 대화·기록), `venv`는 들어가지 않아요.

## 2. GitHub 저장소 만들기
1. github.com에 로그인 → 오른쪽 위 **+ → New repository**
2. 이름 예: `maeumi-app`, **Private** 선택 → Create repository
3. **uploading an existing file** 링크 → `deploy_upload` 폴더 **안의** 파일과 폴더를 모두 끌어다 놓기 → Commit changes
4. 목록에 `.streamlit/config.toml`이 없으면(숨김 폴더라 빠질 수 있어요): **Add file → Create new file** → 이름에 `.streamlit/config.toml` 입력 → `deploy_upload\.streamlit\config.toml` 내용을 붙여넣고 Commit
   - 빠져도 앱은 동작하지만, 처음 열 때 "새로고침(F5)" 안내가 한 번 나와요.

## 3. Streamlit Cloud에 배포
1. share.streamlit.io → **Continue with GitHub**로 로그인 (Private 저장소 접근 허용)
2. **Create app → Deploy a public app from GitHub**
3. Repository: 방금 만든 저장소 / Branch: `main` / Main file path: `streamlit_app.py`
4. App URL에 원하는 이름 입력 (예: `maeumi-demo`)
5. **Advanced settings**
   - Python version: **3.12**
   - Secrets에 아래 두 줄 입력 (값은 직접 채우기)
     ```
     ANTHROPIC_API_KEY = "여기에 API 키"
     ADMIN_CODE = "관리자 페이지 코드 (팀만 아는 값)"
     ```
     (예전의 `DOCTOR_PASSWORD`는 더 이상 쓰지 않아요. 남아 있어도 영향이 없어요.)
6. **Deploy** → 몇 분 뒤 링크가 열려요.

## 4. 알아둘 점
- **데이터는 임시예요.** 환자 기록은 관리자 페이지에서 리셋하기 전까지 유지되지만, 앱이 잠들거나 재시작·재배포되면 초기화돼요(관리자 설정도 기본값으로 돌아가요). 중요한 시점에는 관리자 페이지에서 백업을 받아 두세요.
- **며칠 접속이 없으면 앱이 잠들어요.** 발표 전에 링크를 미리 열어 깨워 두세요.
- **모든 방문자가 같은 데이터를 써요.** 같은 이름을 입력하면 같은 환자로 연결되니, 시연에는 가명을 쓰세요. (이름이 주소 `?name=`에 들어가요)
- **API 비용:** 링크를 아는 누구나 마음이와 대화할 수 있고, 그 비용은 팀 API 키로 나가요. Anthropic 콘솔에서 사용 한도를 정해 두세요.
- 환자 화면 사이드바의 시연 도구는 다른 환자의 기록이 보여서 기본으로 숨겨져 있어요. 필요하면 관리자 페이지에서 켜세요.
- 시연 사례 파일(`demo_data/demo_cases.csv`)은 실제 데이터의 MDD군·건강대조군에서 한 명씩 골라 조합한 **가상 조합 사례**예요. 모델이 학습한 사람들의 값이라 실제 새 환자보다 잘 맞혀 보여요.
- 코드를 고친 뒤에는 `make_deploy_folder.py`를 다시 실행하고 바뀐 파일을 GitHub에 다시 올리면, Streamlit Cloud가 자동으로 새 버전을 반영해요.
