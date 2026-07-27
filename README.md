# 영어 학습자료 제작소 (완전 통합판)

`WEB`(구문분석+OX), `WB`(단어시험지 워크북), `VOCA`(어휘 분석)를 **하나의 FastAPI 서버, 하나의 배포**로 합쳤습니다.
Render 하나에 올리면 도메인 하나에서 4개 도구가 전부 동작합니다.

## 주소 구조

| 경로 | 도구 |
|---|---|
| `/` | 허브 랜딩 페이지 |
| `/passage-analyzer/` | 구문분석 자동 생성기 (PDF) |
| `/comprehension/` | O/X 리딩 워크북 메이커 |
| `/combined/` | 지문 1번으로 구문분석+OX 동시 생성 |
| `/workbook/` | 단어시험지 워크북 생성기 (PDF) — 기존 WB 레포 |
| `/voca/` | ARA Vocab AI (단어장·단어시험·정답지) — 기존 VOCA 레포 |

## 어떻게 합쳤나

- `app/` (구문분석) 은 기존 WEB 그대로. 최상위 FastAPI 앱이자 허브 역할.
- `workbook_service/` = 기존 WB `app/` 폴더를 그대로 옮긴 것. FastAPI 앱 전체를
  `app.mount("/workbook", workbook_app)`로 서브 마운트했습니다.
- `voca_service/` = 기존 VOCA `app/` + `static/` 폴더를 그대로 옮긴 것. 마찬가지로
  `app.mount("/voca", voca_app)`.
- **서버 쪽 파이썬 코드는 로직을 하나도 바꾸지 않았습니다.** Starlette의 `Mount`가
  하위 앱의 내부 라우팅을 그대로 처리해주기 때문입니다.
- **프론트엔드(HTML/JS)에서 `/api/render-pdf`, `/static/...`, `action="/analyze"`
  처럼 절대경로(`/`로 시작)로 자기 자신을 호출하던 부분만 상대경로로 고쳤습니다.**
  서브 경로(`/workbook/`, `/voca/`)에 마운트되면 절대경로는 무조건 도메인 루트를
  가리켜서 깨지기 때문에 필요한 수정이었습니다. (예: `fetch("/api/render-pdf")` →
  `fetch("api/render-pdf")`)

## 로컬 실행

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` → 허브 랜딩 페이지에서 4개 도구 중 선택.

## 배포 (Render 기준)

1. 이 폴더 전체 내용으로 GitHub `WEB` 레포를 교체(또는 새 레포 생성)합니다.
2. Render 대시보드 → **New → Web Service** → 해당 레포 연결.
3. Runtime이 **Docker**로 자동 감지되는지 확인 (Dockerfile이 WeasyPrint 시스템
   의존성 + 한글 폰트까지 설치합니다).
4. 별도 환경변수 필요 없음. 4개 도구 모두 사용자가 자신의 API 키를 브라우저에서
   직접 입력하는 BYOK 구조라서, 서버에는 어떤 비밀 키도 두지 않습니다.
5. 배포 완료되면 `https://xxx.onrender.com` 하나의 주소에서 4개 도구가 모두 동작합니다.

## 확인 완료 (로컬 스모크 테스트)

- `GET /` → 200
- `GET /passage-analyzer/` → 200
- `GET /comprehension/` → 200
- `GET /workbook/` → 200 (내부 `fetch("api/render-pdf")` 상대경로 확인)
- `GET /voca/` → 200 (내부 `href="static/style.css"`, `action="analyze"` 상대경로 확인)

## 남은 선택 사항 (원하시면 다음 단계로 진행)

지금은 4개 도구가 **한 주소에서** 다 동작하지만, 각각 별도 폼입니다.
"지문 5개를 한 번에 넣으면 구문분석+OX+워크북+VOCA가 전부 자동 생성"되는 진짜
원클릭 버전을 원하시면, 4개 도구가 각각 브라우저에서 Gemini/OpenAI를 호출하는
프론트엔드 JS 로직(`workbook-generator.js`, VOCA의 분석 프롬프트 등)을 하나의
공통 입력 폼에서 순서대로 호출하도록 새 오케스트레이션 페이지를 만들어야 합니다.
필요하시면 이어서 만들어 드릴게요.
