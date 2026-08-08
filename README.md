# 영어 학습자료 제작소 (통합판)

지문분석기 / 워크북 메이커 / O/X 리딩 워크북 / 단어장 퀴즈를 하나의 FastAPI 서버로 합친 버전입니다.

## 폴더 구조

```
app/
  main.py              앱 진입점, 모든 라우터 연결
  models.py            DB 테이블 정의 (teachers, word_lists, words, students,
                        quiz_results, passages, materials)
  db.py                DB 조회/저장 로직 (정원 제한 체크 포함)
  limits.py            용량 제한값 (단어장 100개, 단어 5000개, 학생 100명)
  auth.py              PIN 해시, JWT, Gemini 키 암호화
  routes_auth.py        회원가입/로그인/로그아웃/내정보
  routes_words.py       단어장·단어·학생 관리, 결과 보기 (로그인 필요)
  routes_public.py      학생용 (링크+코드, 로그인 불필요)
  routes_generate.py    지문분석/워크북/OX 생성 (로그인 필요, 선생님 개인 Gemini 키 사용)
  prompts.py            3개 도구의 Gemini 시스템 프롬프트
  analysis_schema.py    지문분석 결과의 JSON 스키마 (기존 프로젝트에서 이식)
  llm.py                Gemini API 실제 호출
```

## 실행 전 환경변수

```
JWT_SECRET=<openssl rand -hex 32 로 생성한 랜덤 값>
FERNET_KEY=<python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```
두 값 다 한 번 정하면 이후 계속 같은 값을 써야 해요. 바뀌면 기존 로그인 세션과
저장된 Gemini 키가 전부 무효가 됩니다.

## 로컬 실행

```bash
pip install -r requirements.txt
export JWT_SECRET=...
export FERNET_KEY=...
uvicorn app.main:app --reload --port 8000
```

## 인증 흐름

1. `POST /auth/signup` — 이름 + PIN + Gemini API 키로 선생님 계정 생성
2. `POST /auth/login` — 이름 + PIN으로 로그인, 세션 쿠키 발급 (httpOnly, secure, 30일)
3. 이후 `/api/*` 요청은 이 쿠키로 자동 인증됨 (로그인한 선생님 소속 데이터만 조회/수정)
4. 학생은 `/public/quiz/{access_code}/...` 경로로 로그인 없이 접속 (기존 방식 그대로)

## 아직 안 된 것 (다음에 이어서 할 것들)

- **프론트엔드**: 지금은 API(백엔드)만 완성된 상태예요. 기존 React(단어장)/정적 HTML(워크북·OX·지문분석) 화면을
  이 API에 맞게 새로 연결하는 작업이 필요해요.
- **PDF 렌더링**: 기존 워크북 사이트의 WeasyPrint 렌더링(`render.py`)을 아직 이 통합판에 옮기지 않았어요.
  지문분석/워크북 결과를 PDF로 만드는 부분은 기존 `render.py`를 그대로 가져와 붙이면 됩니다.
- **워크북/OX 프롬프트 검수**: `prompts.py`의 워크북·OX 시스템 프롬프트는 지금까지 대화에서 정리된
  스펙을 바탕으로 새로 작성한 것이라, 기존에 실제 쓰던 프롬프트와 결과물이 다를 수 있어요.
  한 번 실제로 돌려보고 결과 품질을 확인해야 해요.
- **Gemini 실제 호출 테스트**: 개발 환경 네트워크 제약으로 이번엔 API 형식만 맞춰뒀고 실제 호출은
  못 해봤어요. 배포 후 첫 호출에서 정상 동작하는지 확인 필요.
- **Render 배포 설정** (Dockerfile, render.yaml): 아직 안 만들었어요.
