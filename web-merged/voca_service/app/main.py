import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="All-in-One Educational Service")

# 동적 파일/디렉토리 탐색 함수
def find_path(rel_path: str) -> Optional[str]:
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = [
        os.path.join(cur_dir, rel_path),
        os.path.join(cur_dir, "..", rel_path),
        os.path.join(cur_dir, "..", "..", rel_path),
        os.path.join(cwd, rel_path),
        os.path.join(cwd, "web-merged", rel_path),
    ]
    for path in candidates:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None

# Static 마운트
wb_static_path = find_path("workbook_service/static")
if wb_static_path:
    app.mount("/static", StaticFiles(directory=wb_static_path), name="static")
    app.mount("/workbook/static", StaticFiles(directory=wb_static_path), name="workbook_static")

# 루트 (/) 경로 접속 처리
@app.get("/")
async def read_root():
    index_path = find_path("workbook_service/static/index.html")
    if index_path:
        return FileResponse(index_path)
    return {"status": "ok", "message": "Workbook service backend running"}

# 10단계 워크북 API
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
