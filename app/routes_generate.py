"""
지문분석 / 워크북 / OX / 목표어법 문제 생성 라우트, 그리고 이 4개를 한 번에 만드는 통합 라우트.
로그인한 선생님만 접근 가능, 본인이 등록한 개인 Gemini 키로 서버가 대신 호출함.
"""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .auth import get_current_teacher_id
from .db import get_db
from .llm import call_gemini_json
from .docx_render import render_grammar_quiz_docx
from .pdf_render import render_analysis_pdf, render_ox_pdf, render_workbook_pdf
from .prompts import (
    ALL_WORKBOOK_STEPS,
    ANALYSIS_MODEL,
    GRAMMAR_QUIZ_MODEL,
    GRAMMAR_QUIZ_SYSTEM_PROMPT,
    OX_MODEL,
    OX_SYSTEM_PROMPT,
    WORKBOOK_MODEL,
    build_workbook_system_prompt,
    build_analysis_prompt,
    build_analysis_user_message,
    build_grammar_quiz_user_message,
    build_ox_user_message,
    build_workbook_user_message,
)

router = APIRouter(prefix="/api", tags=["generate"])

ALL_MATERIAL_KEYS = ["analysis", "workbook", "ox", "grammar_quiz"]


class GenerateRequest(BaseModel):
    passage_text: str
    title: str | None = None
    target_grammar: str | None = None  # 지문분석/목표어법 전용, 나머지는 무시됨
    materials: list[str] | None = None  # generate-all에서 어떤 자료를 만들지 선택 (기본: 전체)
    workbook_steps: list[str] | None = None  # 워크북에서 어떤 단계를 만들지 선택 (기본: 전체)


async def _get_teacher_gemini(teacher_id: int, db):
    teacher = db.get_teacher(teacher_id)
    if not teacher or not teacher.gemini_api_key_encrypted:
        raise HTTPException(status_code=400, detail="Gemini API 키가 등록되어 있지 않아요. 먼저 'AI 키 설정'에서 등록해주세요.")
    from .auth import decrypt_api_key
    return decrypt_api_key(teacher.gemini_api_key_encrypted), teacher.gemini_model


@router.post("/passage-analysis")
async def generate_analysis(
    body: GenerateRequest,
    teacher_id: int = Depends(get_current_teacher_id),
    db=Depends(get_db),
):
    api_key, model = await _get_teacher_gemini(teacher_id, db)
    passage = db.create_passage(teacher_id, body.passage_text, body.title)

    system_prompt = build_analysis_prompt()
    user_message = build_analysis_user_message(body.passage_text, body.target_grammar)
    result = await call_gemini_json(api_key, model or ANALYSIS_MODEL, system_prompt, user_message)

    material = db.create_material(passage.id, "analysis", json.dumps(result, ensure_ascii=False))
    return {"passage_id": passage.id, "material_id": material.id, "result": result}


@router.post("/workbook")
async def generate_workbook(
    body: GenerateRequest,
    teacher_id: int = Depends(get_current_teacher_id),
    db=Depends(get_db),
):
    api_key, model = await _get_teacher_gemini(teacher_id, db)
    passage = db.create_passage(teacher_id, body.passage_text, body.title)

    user_message = build_workbook_user_message(body.passage_text)
    steps_for_prompt = body.workbook_steps or ALL_WORKBOOK_STEPS
    system_prompt = build_workbook_system_prompt(steps_for_prompt)
    result = await call_gemini_json(api_key, model or WORKBOOK_MODEL, system_prompt, user_message)
    result["_selected_steps"] = steps_for_prompt

    material = db.create_material(passage.id, "workbook", json.dumps(result, ensure_ascii=False))
    return {"passage_id": passage.id, "material_id": material.id, "result": result}


@router.post("/ox")
async def generate_ox(
    body: GenerateRequest,
    teacher_id: int = Depends(get_current_teacher_id),
    db=Depends(get_db),
):
    api_key, model = await _get_teacher_gemini(teacher_id, db)
    passage = db.create_passage(teacher_id, body.passage_text, body.title)

    user_message = build_ox_user_message(body.passage_text)
    result = await call_gemini_json(api_key, model or OX_MODEL, OX_SYSTEM_PROMPT, user_message)

    material = db.create_material(passage.id, "ox", json.dumps(result, ensure_ascii=False))
    return {"passage_id": passage.id, "material_id": material.id, "result": result}


@router.post("/grammar-quiz")
async def generate_grammar_quiz(
    body: GenerateRequest,
    teacher_id: int = Depends(get_current_teacher_id),
    db=Depends(get_db),
):
    api_key, model = await _get_teacher_gemini(teacher_id, db)
    passage = db.create_passage(teacher_id, body.passage_text, body.title)

    user_message = build_grammar_quiz_user_message(body.passage_text, body.target_grammar)
    result = await call_gemini_json(api_key, model or GRAMMAR_QUIZ_MODEL, GRAMMAR_QUIZ_SYSTEM_PROMPT, user_message)

    material = db.create_material(passage.id, "grammar_quiz", json.dumps(result, ensure_ascii=False))
    return {"passage_id": passage.id, "material_id": material.id, "result": result}


@router.post("/generate-all")
async def generate_all(
    body: GenerateRequest,
    teacher_id: int = Depends(get_current_teacher_id),
    db=Depends(get_db),
):
    """지문 하나로 선택된 자료(지문분석/워크북/OX/목표어법 문제)를 한 번에 생성.
    Gemini 호출들을 동시에(asyncio.gather) 보내서 기다리는 시간을 줄임.
    materials가 없으면 4개 전부, 있으면 그 목록에 있는 것만 생성."""
    selected = [k for k in (body.materials or ALL_MATERIAL_KEYS) if k in ALL_MATERIAL_KEYS]
    if not selected:
        raise HTTPException(status_code=400, detail="생성할 자료를 하나 이상 선택해주세요.")

    api_key, model = await _get_teacher_gemini(teacher_id, db)
    passage = db.create_passage(teacher_id, body.passage_text, body.title)

    workbook_steps = body.workbook_steps or ALL_WORKBOOK_STEPS

    calls = {}
    if "analysis" in selected:
        calls["analysis"] = call_gemini_json(
            api_key, model or ANALYSIS_MODEL, build_analysis_prompt(),
            build_analysis_user_message(body.passage_text, body.target_grammar),
        )
    if "workbook" in selected:
        calls["workbook"] = call_gemini_json(
            api_key, model or WORKBOOK_MODEL, build_workbook_system_prompt(workbook_steps),
            build_workbook_user_message(body.passage_text),
        )
    if "ox" in selected:
        calls["ox"] = call_gemini_json(
            api_key, model or OX_MODEL, OX_SYSTEM_PROMPT,
            build_ox_user_message(body.passage_text),
        )
    if "grammar_quiz" in selected:
        calls["grammar_quiz"] = call_gemini_json(
            api_key, model or GRAMMAR_QUIZ_MODEL, GRAMMAR_QUIZ_SYSTEM_PROMPT,
            build_grammar_quiz_user_message(body.passage_text, body.target_grammar),
        )

    keys = list(calls.keys())
    results = await asyncio.gather(*calls.values(), return_exceptions=True)

    materials = {}
    errors = {}
    for key, res in zip(keys, results):
        if isinstance(res, Exception):
            detail = res.detail if isinstance(res, HTTPException) else str(res)
            errors[key] = detail
            continue
        if key == "workbook":
            res["_selected_steps"] = workbook_steps
        material = db.create_material(passage.id, key, json.dumps(res, ensure_ascii=False))
        materials[key] = {"material_id": material.id, "result": res}

    return {"passage_id": passage.id, "materials": materials, "errors": errors}


@router.get("/passages/{passage_id}/materials")
def get_materials(passage_id: int, teacher_id: int = Depends(get_current_teacher_id), db=Depends(get_db)):
    passage = db.get_passage(passage_id, teacher_id)
    if not passage:
        raise HTTPException(status_code=404, detail="지문을 찾을 수 없어요.")
    rows = db.list_materials(passage_id)
    return [{"id": r.id, "type": r.type, "content": json.loads(r.content), "pdf_path": r.pdf_path} for r in rows]


@router.get("/materials/{material_id}/pdf")
def download_material_pdf(material_id: int, teacher_id: int = Depends(get_current_teacher_id), db=Depends(get_db)):
    material = db.get_material(material_id, teacher_id)
    if not material:
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없어요.")

    content = json.loads(material.content)
    passage = db.get_passage(material.passage_id, teacher_id)
    title = (passage.title if passage else None) or "학습자료"

    if material.type == "analysis":
        pdf_bytes = render_analysis_pdf(content, title=title)
    elif material.type == "workbook":
        steps = content.pop("_selected_steps", None)
        pdf_bytes = render_workbook_pdf(content, title=title, steps=steps)
    elif material.type == "ox":
        pdf_bytes = render_ox_pdf(content, title=title)
    else:
        raise HTTPException(status_code=400, detail="이 자료 유형은 아직 PDF 다운로드를 지원하지 않아요.")

    filename = f"{title}_{material.type}.pdf"
    from urllib.parse import quote
    encoded_filename = quote(filename)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"material.pdf\"; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/materials/{material_id}/docx")
def download_material_docx(material_id: int, teacher_id: int = Depends(get_current_teacher_id), db=Depends(get_db)):
    """편집 가능한 워드(.docx)로 다운로드. 지금은 목표어법 문제(문법 테스트)만 지원."""
    material = db.get_material(material_id, teacher_id)
    if not material:
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없어요.")

    content = json.loads(material.content)
    passage = db.get_passage(material.passage_id, teacher_id)
    title = (passage.title if passage else None) or "학습자료"

    if material.type == "grammar_quiz":
        docx_bytes = render_grammar_quiz_docx(content, title=f"{title} 문법 테스트")
    else:
        raise HTTPException(status_code=400, detail="이 자료 유형은 아직 워드 다운로드를 지원하지 않아요.")

    filename = f"{title}_문법테스트.docx"
    from urllib.parse import quote
    encoded_filename = quote(filename)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=\"material.docx\"; filename*=UTF-8''{encoded_filename}"},
    )
