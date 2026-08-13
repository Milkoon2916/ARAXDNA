"""
Gemini API 호출 담당.
선생님이 등록한 개인 키(복호화된 상태로 db.get_teacher_gemini_key에서 넘어옴)로
서버가 직접 Gemini를 호출함 (예전처럼 브라우저가 직접 호출하는 BYOK 방식이 아니라,
키를 서버 DB에 저장하기로 했으므로 서버가 대신 호출하는 구조로 바뀜).
"""
import asyncio
import json
import random

import httpx
from fastapi import HTTPException

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Gemini 쪽 일시적 과부하/타임아웃(주로 503, 간헐적으로 500)은 잠깐 후 재시도하면
# 대부분 성공함. 4개 자료를 asyncio.gather로 동시에 쏘다 보니 순간적으로 겹쳐서
# 503이 뜨는 경우가 흔해서, 실패해도 바로 포기하지 않고 몇 번 재시도함.
RETRYABLE_STATUS_CODES = {500, 503, 504}
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.5


async def call_gemini_json(api_key: str, model: str, system_prompt: str, user_message: str) -> dict:
    """Gemini를 호출하고, 응답을 JSON으로 파싱해서 dict로 돌려줌.
    JSON 강제 출력 모드(response_mime_type)를 써서 마크다운 펜스 등이 안 섞이게 함."""
    url = GEMINI_ENDPOINT.format(model=model)
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "maxOutputTokens": 60000,
        },
    }

    resp = None
    async with httpx.AsyncClient(timeout=120) as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.post(url, params={"key": api_key}, json=payload)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == MAX_RETRIES:
                    raise HTTPException(status_code=502, detail="Gemini 호출이 계속 실패했어요. 잠시 후 다시 시도해주세요.")
                await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 0.5))
                continue

            if resp.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_RETRIES:
                break
            await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 0.5))

    if resp.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Gemini 요청 한도(무료 등급)에 걸렸어요. 잠시 후 다시 시도해주세요.",
        )
    if resp.status_code == 401 or resp.status_code == 403:
        raise HTTPException(status_code=400, detail="등록된 Gemini API 키가 유효하지 않아요. 키 설정을 다시 확인해주세요.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini 호출 중 오류가 발생했어요 ({resp.status_code}).")

    data = resp.json()
    try:
        candidate = data["candidates"][0]
        finish_reason = candidate.get("finishReason")
        text = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        finish_reason = data.get("candidates", [{}])[0].get("finishReason") if data.get("candidates") else None
        if finish_reason == "MAX_TOKENS":
            raise HTTPException(
                status_code=502,
                detail="지문이 너무 길거나 선택한 항목이 많아서 응답이 도중에 잘렸어요. 단계를 줄이거나 지문을 나눠서 다시 시도해주세요.",
            )
        raise HTTPException(status_code=502, detail="Gemini 응답 형식이 예상과 달라요.")

    if finish_reason == "MAX_TOKENS":
        raise HTTPException(
            status_code=502,
            detail="지문이 너무 길거나 선택한 항목이 많아서 응답이 도중에 잘렸어요. 단계를 줄이거나 지문을 나눠서 다시 시도해주세요.",
        )

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Gemini가 유효한 JSON을 반환하지 않았어요. 다시 시도해주세요.")

    if not parsed or (isinstance(parsed, dict) and not any(parsed.values())):
        raise HTTPException(status_code=502, detail="Gemini가 빈 결과를 반환했어요. 다시 시도해주세요.")

    return parsed
