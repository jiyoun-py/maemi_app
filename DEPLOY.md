# Streamlit Cloud 배포 안내

환자용과 의사용이 **한 앱의 두 페이지**로 실행돼요. (`streamlit_app.py`가 시작 파일)

| 화면 | 주소 |
|---|---|
| 환자용 (마음이) | `https://<앱이름>.streamlit.app/` |
| 의사용 (CDSS) | `https://<앱이름>.streamlit.app/doctor` (비밀번호 필요) |

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
     DOCTOR_PASSWORD = "의료진 화면 비밀번호"
     ```
6. **Deploy** → 몇 분 뒤 링크가 열려요.

## 4. 알아둘 점
- **데이터는 임시예요.** 앱이 잠들거나 다시 시작되면 상담 요청·체크인 같은 공유 데이터가 초기화돼요. 발표 직전에 시연 흐름을 한 번 실행해 두세요.
- **며칠 접속이 없으면 앱이 잠들어요.** 발표 전에 링크를 미리 열어 깨워 두세요.
- **모든 방문자가 같은 데이터를 써요.** 같은 이름을 입력하면 같은 환자로 연결되니, 시연에는 가명을 쓰세요. (이름이 주소 `?name=`에 들어가요)
- **API 비용:** 링크를 아는 누구나 마음이와 대화할 수 있고, 그 비용은 팀 API 키로 나가요. Anthropic 콘솔에서 사용 한도를 정해 두세요.
- 환자 화면 사이드바의 "시연용" 버튼은 방문자에게도 보여요.
- 코드를 고친 뒤에는 `make_deploy_folder.py`를 다시 실행하고 바뀐 파일을 GitHub에 다시 올리면, Streamlit Cloud가 자동으로 새 버전을 반영해요.
