"""
Gemini API 호출 담당.
선생님이 등록한 개인 키(복호화된 상태로 db.get_teacher_gemini_key에서 넘어옴)로
서버가 직접 Gemini를 호출함 (예전처럼 브라우저가 직접 호출하는 BYOK 방식이 아니라,
키를 서버 DB에 저장하기로 했으므로 서버가 대신 호출하는 구조로 바뀜).
"""
import asyncio
import json

import httpx
from fastapi import HTTPException

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# 503(모델 과부하)/429(요청 한도)는 순간적인 상태일 때가 많아서, 바로 에러를 던지지 않고
# 짧게 재시도한다. 지문분석에서 503이 자주 보고됐던 것도 대부분 이 케이스였음.
_RETRY_STATUS_CODES = {429, 503}
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = [1.5, 3.5]  # 1차 실패 후 1.5초, 2차 실패 후 3.5초 대기


async def call_gemini_json(
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    max_output_tokens: int = 16000,
) -> dict:
    """Gemini를 호출하고, 응답을 JSON으로 파싱해서 dict로 돌려줌.
    JSON 강제 출력 모드(response_mime_type)를 써서 마크다운 펜스 등이 안 섞이게 함.

    지문분석에서 502/503이 자주 나던 원인:
    1) maxOutputTokens가 60000으로 지나치게 커서 응답 생성이 오래 걸렸고,
       Render 등 배포 플랫폼의 프록시가 자체 타임아웃(보통 ~100초)으로 연결을
       먼저 끊어버려 우리 앱의 에러 처리가 실행되기도 전에 502/503이 발생했음.
       -> 기본값을 16000으로 낮춤(지문 분석 결과 크기면 충분히 여유 있음).
    2) httpx 타임아웃 시(ReadTimeout 등) 예외를 잡지 않아서 처리되지 않은 예외가
       그대로 터져 나갔음 -> 아래에서 명시적으로 잡아서 504로 변환.
    3) Gemini가 "모델 과부하(503)"를 순간적으로 반환하는 경우가 꽤 있는데, 예전엔
       바로 에러를 사용자에게 보여줬음 -> 짧은 대기 후 최대 3회까지 자동 재시도하도록 변경.
    """
    url = GEMINI_ENDPOINT.format(model=model)
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "maxOutputTokens": max_output_tokens,
        },
    }

    resp = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, params={"key": api_key}, json=payload)
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Gemini 응답이 90초 안에 오지 않았어요. 지문이 너무 길면 나눠서 시도해보세요.",
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Gemini에 연결하지 못했어요: {e}")

        if resp.status_code in _RETRY_STATUS_CODES and attempt < _MAX_ATTEMPTS - 1:
            await asyncio.sleep(_BACKOFF_SECONDS[attempt])
            continue
        break

    if resp.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Gemini 요청 한도(무료 등급)에 걸렸어요. 잠시 후 다시 시도해주세요.",
        )
    if resp.status_code == 401 or resp.status_code == 403:
        raise HTTPException(status_code=400, detail="등록된 Gemini API 키가 유효하지 않아요. 키 설정을 다시 확인해주세요.")
    if resp.status_code == 503:
        raise HTTPException(
            status_code=503,
            detail="Gemini 서버가 일시적으로 과부하 상태예요 (재시도 3회 실패). 잠시 후 다시 시도해주세요.",
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini 호출 중 오류가 발생했어요 ({resp.status_code}).")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail="Gemini 응답 형식이 예상과 달라요.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Gemini가 유효한 JSON을 반환하지 않았어요. 다시 시도해주세요.")
