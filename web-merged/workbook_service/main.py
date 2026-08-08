import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "workbook_service_active"}

class SentenceData(BaseModel):
    id: int
    en: str
    ko: str
    verb_practice: str
    grammar_choice: str
    ko_blank: str
    en_blank: str
    scramble: str
    keywords: List[str]
    check_item: Optional[str] = None

class ParagraphData(BaseModel):
    text: str
    answers: List[str]

class WorkbookGenerateRequest(BaseModel):
    title: str
    publisher_info: Optional[str] = "2022 개정 | NE능률(오선영) 공통영어2"
    lesson: Optional[str] = "Lesson 1"
    sentences: List[SentenceData]
    paragraphs: Optional[List[ParagraphData]] = []

@app.post("/api/workbook/generate")
async def generate_workbook(request: WorkbookGenerateRequest):
    try:
        return {
            "status": "success",
            "metadata": {
                "title": request.title,
                "publisher": request.publisher_info,
                "lesson": request.lesson
            },
            "sentences": [s.dict() for s in request.sentences],
            "paragraphs": [p.dict() for p in request.paragraphs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
