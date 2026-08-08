import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="All-in-One Educational Service")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# static 경로 마운트 검증
workbook_static = os.path.join(BASE_DIR, "workbook_service", "static")
voca_static = os.path.join(BASE_DIR, "voca_service", "static")
all_in_one_dir = os.path.join(BASE_DIR, "all-in-one")

if os.path.exists(workbook_static):
    app.mount("/workbook/static", StaticFiles(directory=workbook_static), name="workbook_static")

if os.path.exists(voca_static):
    app.mount("/static", StaticFiles(directory=voca_static), name="voca_static")

if os.path.exists(all_in_one_dir):
    app.mount("/all-in-one", StaticFiles(directory=all_in_one_dir), name="all_in_one")

# 루트 (/) 경로 진입 시 워크북/통합 메인 페이지 연결
@app.get("/")
async def read_root():
    # 1순위: workbook_service/static/index.html
    wb_index = os.path.join(workbook_static, "index.html")
    if os.path.exists(wb_index):
        return FileResponse(wb_index)
    
    # 2순위: all-in-one/index.html
    aio_index = os.path.join(all_in_one_dir, "index.html")
    if os.path.exists(aio_index):
        return FileResponse(aio_index)

    return {"status": "online", "message": "Service is running properly."}
