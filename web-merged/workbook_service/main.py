from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

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
    """
    이그잼포유(EXAM4YOU) 규격 10단계 워크북 데이터 패키지 응답 API
    """
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
