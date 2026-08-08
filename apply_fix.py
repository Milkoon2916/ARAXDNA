import os

# 덮어씌울 전체 파일 데이터 세트
FILES = {
    # 1. 루트 및 모든 모듈의 main.py (Render의 모든 실행 경로에 대응)
    "main.py": '''import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="EXAM4YOU Workbook Service")

def find_target_path(target_rel_path: str) -> Optional[str]:
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    candidates = [
        os.path.join(cwd, target_rel_path),
        os.path.join(cur_dir, target_rel_path),
        os.path.join(cwd, "web-merged", target_rel_path),
        os.path.join(cur_dir, "web-merged", target_rel_path),
        os.path.join(cur_dir, "..", target_rel_path),
        os.path.join(cur_dir, "..", "..", target_rel_path),
    ]
    for candidate in candidates:
        abs_path = os.path.abspath(candidate)
        if os.path.exists(abs_path):
            return abs_path
    return None

wb_static = find_target_path("workbook_service/static") or find_target_path("static")
if wb_static:
    app.mount("/static", StaticFiles(directory=wb_static), name="static")
    app.mount("/workbook/static", StaticFiles(directory=wb_static), name="workbook_static")

@app.get("/")
async def read_root():
    index_html = find_target_path("workbook_service/static/index.html") or find_target_path("static/index.html")
    if index_html and os.path.isfile(index_html):
        return FileResponse(index_html)
    return {"status": "ok", "message": "Workbook service backend running"}

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
''',

    # 2. CSS 스타일시트 (나눔고딕 및 이그잼포유 양식)
    "web-merged/voca_service/static/style.css": '''@import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');

* {
    box-sizing: border-box;
    font-family: 'Nanum Gothic', '나눔고딕', sans-serif !important;
}

body {
    margin: 0;
    padding: 0;
    background-color: #f8f9fa;
    color: #212529;
    font-size: 14px;
    line-height: 1.6;
}

.workbook-page {
    width: 210mm;
    min-height: 297mm;
    padding: 15mm 15mm 20mm 15mm;
    margin: 20px auto;
    background: #ffffff;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
    position: relative;
    page-break-after: always;
}

.workbook-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #1a365d;
    padding-bottom: 8px;
    margin-bottom: 15px;
}

.workbook-header .header-left {
    font-size: 11px;
    color: #4a5568;
    font-weight: bold;
}

.workbook-header .header-center {
    text-align: center;
    font-size: 16px;
    font-weight: 800;
    color: #1a365d;
}

.workbook-header .header-right {
    font-size: 11px;
    color: #4a5568;
    font-weight: bold;
}

.workbook-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 15px;
}

.workbook-table th, .workbook-table td {
    border: 1px solid #cbd5e0;
    padding: 8px 10px;
    vertical-align: top;
    font-size: 13px;
}

.workbook-table td.en-cell {
    width: 50%;
    background-color: #ffffff;
}

.workbook-table td.ko-cell {
    width: 50%;
    background-color: #f7fafc;
}

.sentence-item {
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.7;
}

.sentence-item .num {
    font-weight: bold;
    color: #2b6cb0;
    margin-right: 4px;
}

.answer-space {
    border-bottom: 1px solid #cbd5e0;
    height: 28px;
    margin-top: 4px;
    margin-bottom: 8px;
}

.workbook-footer {
    position: absolute;
    bottom: 10mm;
    left: 15mm;
    right: 15mm;
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 800;
    color: #a0aec0;
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
}

@media print {
    body { background: none; }
    .workbook-page {
        box-shadow: none;
        margin: 0;
        width: 100%;
        min-height: 100vh;
    }
}
''',

    # 3. JS 렌더러 (10단계 전체 구현)
    "web-merged/workbook_service/static/workbook-renderer.js": '''class Exam4YouWorkbookRenderer {
    constructor(containerId, metadata) {
        this.container = document.getElementById(containerId);
        this.metadata = metadata || {
            revision: "2022 개정",
            publisher: "NE능률(오선영)",
            subject: "공통영어2",
            lesson: "Lesson 1"
        };
    }

    createHeader(stepTitle) {
        return `
            <div class="workbook-header">
                <div class="header-left">${this.metadata.revision} | ${this.metadata.publisher} ${this.metadata.subject}</div>
                <div class="header-center">${this.metadata.lesson}<br><strong>${stepTitle}</strong></div>
                <div class="header-right">교과서 본문</div>
            </div>
        `;
    }

    createFooter(pageNo) {
        return `
            <div class="workbook-footer">
                <span>-${pageNo}-</span>
                <span>EXAM4YOU</span>
            </div>
        `;
    }

    renderAll(workbookData) {
        this.container.innerHTML = "";
        let pageCount = 1;
        this.container.appendChild(this.renderStep1(workbookData, pageCount++));
        this.container.appendChild(this.renderStep2(workbookData, pageCount++));
        this.container.appendChild(this.renderStep3(workbookData, pageCount++));
        this.container.appendChild(this.renderStep4(workbookData, pageCount++));
        this.container.appendChild(this.renderStep5(workbookData, pageCount++));
        this.container.appendChild(this.renderStep6(workbookData, pageCount++));
        this.container.appendChild(this.renderStep7(workbookData, pageCount++));
        this.container.appendChild(this.renderStep8(workbookData, pageCount++));
        this.container.appendChild(this.renderStep9(workbookData, pageCount++));
        this.container.appendChild(this.renderStep10(workbookData, pageCount++));
        this.container.appendChild(this.renderAnswerKey(workbookData, pageCount++));
    }

    renderStep1(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let rowsHtml = data.sentences.map((s, idx) => `
            <tr>
                <td class="en-cell"><span class="num">${idx + 1}</span> ${s.en}</td>
                <td class="ko-cell">${s.ko}</td>
            </tr>
        `).join("");
        page.innerHTML = `
            ${this.createHeader("본문 해석지 (워크북 1)")}
            <p style="font-size:12px; color:#4a5568;">▶ 영문과 해석을 읽으며 문장의 의미를 파악해 보세요.</p>
            <table class="workbook-table"><tbody>${rowsHtml}</tbody></table>
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    renderStep2(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p><strong>${idx + 1}.</strong> ${s.en}</p>
                <p style="color:#2d3748;">${s.ko_blank || s.ko}</p>
            </div>
        `).join("");
        page.innerHTML = `${this.createHeader("빈칸 연습(우리말) (워크북 2)")}<p style="font-size:12px; color:#4a5568;">▶ 영문을 보고 우리말 해석을 완성하시오.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep3(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p style="color:#2d3748;"><strong>${idx + 1}.</strong> ${s.ko}</p>
                <p>${s.en_blank || s.en}</p>
            </div>
        `).join("");
        page.innerHTML = `${this.createHeader("빈칸 연습(영문) (워크북 3)")}<p style="font-size:12px; color:#4a5568;">▶ 우리말 해석을 보고 영문을 완성하시오.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep4(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item"><p><strong>${idx + 1}.</strong> ${s.en}</p><div class="answer-space"></div></div>
        `).join("");
        page.innerHTML = `${this.createHeader("해석 연습 (워크북 4)")}<p style="font-size:12px; color:#4a5568;">▶ 영어 문장을 읽고 우리말 해석을 쓰시오.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep5(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item"><p style="color:#4a5568; font-size:12px;">${idx + 1}. ${s.ko}</p><p>${s.verb_practice || s.en}</p></div>
        `).join("");
        page.innerHTML = `${this.createHeader("동사형 연습 (워크북 5)")}<p style="font-size:12px; color:#4a5568;">▶ 괄호 안에 주어진 단어를 알맞게 고쳐 쓰세요.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep6(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item"><p style="color:#4a5568; font-size:12px;">${idx + 1}. ${s.ko}</p><p>${s.grammar_choice || s.en}</p></div>
        `).join("");
        page.innerHTML = `${this.createHeader("어법 선택형 연습 (워크북 6)")}<p style="font-size:12px; color:#4a5568;">▶ 괄호 안에서 어법상 알맞은 것을 골라 보세요.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep7(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let paragraphHtml = (data.paragraphs || []).map((p, idx) => `
            <div class="sentence-item" style="margin-bottom:20px;">
                <p><strong>[문맥/어법 어색한 곳 찾기 ${idx + 1}]</strong></p>
                <p style="background:#f7fafc; padding:10px; border:1px solid #e2e8f0;">${p.text}</p>
                <p style="font-size:12px; color:#718096;">(1) ______________ → ______________</p>
                <p style="font-size:12px; color:#718096;">(2) ______________ → ______________</p>
                <p style="font-size:12px; color:#718096;">(3) ______________ → ______________</p>
            </div>
        `).join("");
        page.innerHTML = `${this.createHeader("어색한 곳 찾기 연습 (워크북 7)")}<p style="font-size:12px; color:#4a5568;">▶ 다음 글의 밑줄 친 부분 중 어색한 것을 찾아 고쳐 쓰시오.</p>${paragraphHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep8(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item"><p><strong>${idx + 1}.</strong> ${s.ko}</p><p style="color:#2b6cb0;">${s.scramble || s.en}</p><div class="answer-space"></div></div>
        `).join("");
        page.innerHTML = `${this.createHeader("순서배열 연습 (워크북 8)")}<p style="font-size:12px; color:#4a5568;">▶ 다음 우리말과 같은 뜻이 되도록 주어진 단어 및 어구를 알맞게 배열해 보세요.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep9(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item"><p><strong>${idx + 1}.</strong> ${s.ko}</p><p style="font-size:12px; color:#718096;">[제시어]: ${(s.keywords || []).join(", ")}</p><div class="answer-space"></div></div>
        `).join("");
        page.innerHTML = `${this.createHeader("영작 연습 (워크북 9)")}<p style="font-size:12px; color:#4a5568;">▶ 다음 우리말과 같은 뜻이 되도록 주어진 단어를 순서대로 사용하여 영작해 보세요.</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderStep10(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item"><p><span class="num">${idx + 1}</span> ${s.check_item || s.grammar_choice || s.en}</p><p style="font-size:12px; color:#4a5568; text-align:right;">${s.ko}</p></div>
        `).join("");
        page.innerHTML = `${this.createHeader("Check 종합점검 (워크북 10)")}<p style="font-size:12px; color:#4a5568;">▶ 어법&어휘 / 영작 / 빈칸 / 순서배열 종합 문제</p>${listHtml}${this.createFooter(pageNo)}`;
        return page;
    }

    renderAnswerKey(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        let answersHtml = data.sentences.map((s, idx) => `<p style="font-size:12px; margin-bottom:4px;"><strong>${idx + 1})</strong> ${s.en} / ${s.ko}</p>`).join("");
        page.innerHTML = `${this.createHeader("Answer Key")}<h3 style="text-align:center; margin-bottom:15px;">정답지 (Answer Key)</h3><div style="column-count: 2; column-gap: 20px;">${answersHtml}</div>${this.createFooter(pageNo)}`;
        return page;
    }
}
''',

    # 4. index.html 메인 UI
    "web-merged/workbook_service/static/index.html": '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>10단계 워크북 생성기</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/workbook/static/style.css">
</head>
<body>
    <div id="workbook-container"></div>
    <script src="/workbook/static/workbook-renderer.js"></script>
    <script src="/static/workbook-renderer.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            if (typeof Exam4YouWorkbookRenderer !== "undefined") {
                const renderer = new Exam4YouWorkbookRenderer("workbook-container");
                console.log("Renderer initialized successfully.");
            }
        });
    </script>
</body>
</html>
'''
}

# 모든 파일 경로로 main.py 복사 대상 확장
main_code = FILES["main.py"]
FILES["web-merged/main.py"] = main_code
FILES["web-merged/app/main.py"] = main_code
FILES["web-merged/voca_service/app/main.py"] = main_code
FILES["web-merged/workbook_service/main.py"] = main_code

def main():
    print("===== EXAM4YOU Workbook Service File Generator =====")
    for rel_path, content in FILES.items():
        dir_name = os.path.dirname(rel_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(rel_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Updated: {rel_path}")
    print("\nAll files have been generated and overwritten successfully!")

if __name__ == "__main__":
    main()
