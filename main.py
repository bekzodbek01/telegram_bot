import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER
from jinja2 import Environment, FileSystemLoader, select_autoescape

from db import (
    init_db, add_staff, delete_staff, list_staff,
    get_stats, all_staff_with_stats, vote_staff,
    delete_staff_month_votes, delete_all_votes_for_staff
)
from utils_qr import make_qr_for_staff
from export_excel import (
    export_excel,
    export_one_staff_excel,
    export_month_excel
)


ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SenBaholash_bot")
SECRET_KEY = os.getenv("FASTAPI_SECRET", "my_super_secret_12345")

app = FastAPI(title="SenBaholash Admin", docs_url="/docs", redoc_url=None)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    same_site="lax",
    https_only=False,
)

# Static + Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def is_authed(request: Request) -> bool:
    return bool(request.session.get("auth", False))


@app.on_event("startup")
def _startup():
    init_db()


# ------------------ LOGIN ------------------
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if not is_authed(request):
        tpl = templates.get_template("login.html")
        return tpl.render(error=None)
    return RedirectResponse(url="/admin/staffs", status_code=HTTP_303_SEE_OTHER)


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        request.session["auth"] = True
        return RedirectResponse(url="/admin/staffs", status_code=HTTP_303_SEE_OTHER)

    tpl = templates.get_template("login.html")
    return HTMLResponse(tpl.render(error="Login yoki parol xato!"))


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)


# ------------------ STAFF LIST ------------------
@app.get("/admin/staffs", response_class=HTMLResponse)
async def staff_list(request: Request):
    if not is_authed(request):
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    rows = all_staff_with_stats()
    tpl = templates.get_template("staff_list.html")
    return tpl.render(rows=rows)


# ------------------ STAFF ADD ------------------
@app.post("/admin/staff")
async def staff_add(
    request: Request,
    staff_id: int = Form(...),
    name: str = Form(...),
    position: str = Form(...),
    region: str = Form(...)
):
    if not is_authed(request):
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    add_staff(staff_id, name, position, region)
    return RedirectResponse(url="/admin/staffs", status_code=HTTP_303_SEE_OTHER)


# ------------------ STAFF DELETE ------------------
@app.post("/admin/staff/{staff_id}/delete")
async def staff_delete(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    delete_staff(staff_id)
    return RedirectResponse(url="/admin/staffs", status_code=HTTP_303_SEE_OTHER)


# ------------------ STAFF DETAIL PAGE ------------------
@app.get("/admin/staff/{staff_id}", response_class=HTMLResponse)
async def staff_detail(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    staff_info = None
    for sid, name, pos, reg in list_staff():
        if sid == staff_id:
            staff_info = {"name": name, "position": pos, "region": reg}
            break

    stats = get_stats(staff_id)
    now = datetime.now()

    tpl = templates.get_template("staff_detail.html")
    return tpl.render(
        staff_id=staff_id,
        name=staff_info["name"] if staff_info else "-",
        position=staff_info["position"] if staff_info else "-",
        region=staff_info["region"] if staff_info else "-",
        stats=stats,
        bot_username=BOT_USERNAME,
        now_year=now.year,
        now_month=now.month,
    )


# ------------------ MONTH RESET (FORM orqali) ------------------
@app.post("/admin/staff/{staff_id}/reset/month")
async def reset_month_form(
    request: Request,
    staff_id: int,
    month: int = Form(...),
    year: int = Form(...)
):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    delete_staff_month_votes(staff_id, year, month)
    return RedirectResponse(f"/admin/staff/{staff_id}", 303)


# ------------------ FULL RESET (ALL VOTES) ------------------
@app.post("/admin/staff/{staff_id}/reset/all")
async def reset_all_votes(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    delete_all_votes_for_staff(staff_id)
    return RedirectResponse(f"/admin/staff/{staff_id}", 303)


# ------------------ STAFF QR ------------------
@app.get("/admin/staff/{staff_id}/qr")
async def staff_qr(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename, _ = make_qr_for_staff(staff_id, BOT_USERNAME)
    return FileResponse(filename, media_type="image/png", filename=os.path.basename(filename))


# ------------------ STAFF EXCEL ------------------
@app.get("/admin/staff/{staff_id}/excel")
async def staff_excel_one(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename = export_one_staff_excel(staff_id)
    return FileResponse(filename, filename=os.path.basename(filename))


# ------------------ EXPORT ALL STAFF EXCEL ------------------
@app.get("/admin/export/excel")
async def staff_excel(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename = export_excel()
    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(filename)
    )


# ------------------ EXPORT MONTH/YEAR EXCEL ------------------
@app.get("/admin/export/excel/month")
async def export_month(request: Request, year: int, month: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename = export_month_excel(year, month)
    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(filename)
    )


# ------------------ DEMO VOTE ------------------
@app.get("/vote/{staff_id}/{kind}")
async def vote_demo(staff_id: int, kind: str):
    if kind not in {"like", "dislike", "neutral"}:
        return {"ok": False, "error": "Invalid vote kind"}

    vote_staff(staff_id, kind)
    return {"ok": True, "staff_id": staff_id, "vote": kind}


# ------------------ FULL RESET (ALL STAFF & ALL VOTES) ------------------
from db import delete_all_votes

@app.delete("/admin/reset-votes")
async def reset_votes(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    delete_all_votes()
    return {"message": "Barcha ovozlar o‘chirildi (xodimlar qolgan holda)!"}
