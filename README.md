# 영어 지문 구문분석 자동 생성기 — MVP (BYOK 구조)

`passage-analysis-pdf` 스킬을 웹 서비스로 옮긴 구현체입니다.
**BYOK(Bring Your Own Key)** 구조: 각 사용자가 자신의 Anthropic API 키로 브라우저에서
직접 Claude를 호출합니다. 서버는 API 키를 전혀 보관하지 않고, 분석이 끝난 JSON을
PDF로 렌더링하는 역할만 합니다. (참고: LLM 호출 비용 없이 렌더링만 하므로, 서버를
공개 배포해도 API 비용 위험이 없습니다.)

흐름: 브라우저에서 사용자 키로 Claude 직접 호출 → 분석 JSON 획득 → 서버 `/render`로
JSON만 전송(키는 안 감) → 서버가 PDF 생성 → 다운로드 링크 반환.

## 구조
```
app/
  main.py       FastAPI 앱 (GET /prompt-config, POST /render, GET /download/{job_id})
  prompt.py     format-guide.md 규칙을 옮긴 Claude 시스템 프롬프트 + 모델명
  schemas.py    Claude 응답을 검증하는 Pydantic 스키마
  render.py     JSON → Jinja2 HTML → WeasyPrint PDF
  templates/passage.html.j2   스킬의 assets/template.html을 Jinja2로 변환
static/index.html   실제 프론트엔드 -- API 키 입력(localStorage 저장),
                     브라우저에서 Claude 직접 호출, 결과를 서버 /render로 전송
test_mock.py   Claude API 없이 렌더링 파이프라인만 검증하는 스크립트
```

## 실행 방법 (서버는 API 키가 필요 없습니다)

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속 → 본인의 Anthropic API 키 입력 →
지문 붙여넣기 → 분석하기 → PDF 다운로드. 키는 브라우저 localStorage에만 저장되고
서버로는 전혀 전송되지 않습니다 (Claude 호출은 브라우저 → api.anthropic.com 직접).

`/render`만 직접 테스트하려면 (분석은 이미 끝났다고 가정):
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d @분석결과.json
```

## Claude API 없이 렌더링만 확인하기
```bash
python test_mock.py
```
`test_output.html`, `test_output.pdf`가 생성됩니다. (이미 실행해서 결과를 확인했습니다.)

## 배포 시 API 키 관련
서버 환경변수에 `ANTHROPIC_API_KEY`를 설정할 필요가 없습니다. 대신 각 사용자가
자신의 키를 사이트에서 직접 입력합니다. 즉 배포 시 별도 비밀 값 설정 없이
Dockerfile만으로 배포 가능합니다.

## 시스템 의존성
- **WeasyPrint**: Pango/Cairo/GDK-Pixbuf가 필요합니다. 이 환경(Ubuntu)에는 이미 있었지만,
  배포 서버(Docker 등)에는 `apt-get install libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0` 필요.
- **한글 폰트**: `fonts-noto-cjk` 패키지(Noto Sans/Serif CJK) 설치 필요 — 없으면 PDF에서 한글이 네모(□)로 깨집니다.

## 새 기능: 목표 어법 옵션
프론트엔드에서 "목표 어법"(예: "가정법 도치, 분사구문")을 입력하면, 그 문법이 나타나는
문장에 🎯 배지가 붙고 해당 어법을 설명하는 노트가 추가됩니다. 지정하지 않으면 기존과 동일하게
동작합니다.

## 지문 길이 제한
- **입력**: Claude Sonnet 5는 1M 토큰 컨텍스트 윈도우라 지문 길이 자체는 사실상 제약이 없습니다.
- **출력이 실제 병목**: 문장마다 태그·번역·노트를 촘촘히 생성하기 때문에, 진짜 제약은
  `max_tokens`(현재 20,000, 동기 API 한도는 128K)입니다. 수능 지문(8~12문장) 기준으로는 충분하지만,
  지문이 훨씬 길거나(15문장+) 여러 개를 한 번에 넣으면 `static/index.html`의 `cfg.max_tokens`
  또는 서버 `MAX_TOKENS`를 올려야 응답이 잘리지 않습니다.
- Sonnet 5는 기본적으로 adaptive thinking이 켜져 있어 thinking과 실제 응답 텍스트가 같은
  `max_tokens` 예산을 공유합니다. 응답이 자꾸 잘린다면 이 값을 먼저 의심하세요.

## 다음 단계 (로드맵 2~5단계)
1. **비동기화**: 지금은 `/analyze`가 요청 안에서 동기로 Claude를 호출합니다. 지문이 여러 개거나
   길면 타임아웃이 날 수 있으므로, Redis/RQ 또는 Celery로 작업 큐를 붙여야 합니다.
2. **파일 업로드**: PDF/DOCX 업로드 → 텍스트 추출 → 지문 자동 분할 (`pdfplumber`, `python-docx`)
3. **여러 지문 동시 처리**: `passage_text`를 `---` 구분자로 여러 개 받아 순차/제한 병렬 호출
4. **계정/과금**: 사용자 인증, 월 사용량 제한
5. **재시도 안정성 강화**: 지금은 JSON 파싱 실패 시 최대 3회 재시도하지만, 실패 사유 로깅과
   부분 실패(일부 문장만 이상한 경우) 처리는 아직 없습니다.

## 알려진 제약
- `MODEL = "claude-sonnet-4-6"`으로 고정되어 있습니다. 실제 배포 전 최신 모델명을 확인하세요.
- 지문이 매우 길면(15문장 초과) 한 번의 API 호출로 응답 토큰이 부족할 수 있어 `max_tokens`를
  늘리거나 문장 단위로 분할 호출하는 로직이 필요할 수 있습니다.
# aradna
