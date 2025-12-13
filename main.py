import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import dotenv_values, set_key

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

# ===== ENV =====
ENV_PATH = ".env"
env_data = dotenv_values(ENV_PATH)

ADMIN_USER = env_data.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = env_data.get("ADMIN_PASSWORD", "admin123")
BOT_USERNAME = env_data.get("BOT_USERNAME", "SenBaholash_bot")

app = FastAPI(title="SenBaholash Admin", docs_url=None, redoc_url=None)

# ===== STATIC & TEMPLATES =====
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"])
)

# ===== AUTH (cookie) =====
def is_authed(request: Request) -> bool:
    return request.cookies.get("auth") == "true"

def auth_ok_redirect(path: str = "/admin/staffs"):
    res = RedirectResponse(path, status_code=303)
    # Istasang: httponly=True, samesite="lax"
    res.set_cookie("auth", "true")
    return res

def auth_clear_redirect():
    res = RedirectResponse("/", status_code=303)
    res.delete_cookie("auth")
    return res

# ===== STARTUP =====
@app.on_event("startup")
def _startup():
    init_db()

# ===== LOGIN =====
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if is_authed(request):
        return RedirectResponse("/admin/staffs", status_code=303)
    tpl = templates.get_template("login.html")
    return HTMLResponse(tpl.render(error=None))

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        return auth_ok_redirect()
    tpl = templates.get_template("login.html")
    return HTMLResponse(tpl.render(error="Login yoki parol xato!"))

@app.get("/logout")
async def logout(request: Request):
    return auth_clear_redirect()

# ===== CHANGE USERNAME & PASSWORD =====
@app.get("/admin/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    tpl = templates.get_template("change_password.html")
    return HTMLResponse(tpl.render(error=None, success=False, ADMIN_USER=ADMIN_USER))

@app.post("/admin/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_username: str = Form(...),
    new_password: str = Form(...)
):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    current_pw = dotenv_values(ENV_PATH).get("ADMIN_PASSWORD")
    if current_pw != old_password:
        tpl = templates.get_template("change_password.html")
        return HTMLResponse(tpl.render(error="Eski parol noto‘g‘ri!", success=False, ADMIN_USER=ADMIN_USER))

    set_key(ENV_PATH, "ADMIN_USER", new_username)
    set_key(ENV_PATH, "ADMIN_PASSWORD", new_password)

    tpl = templates.get_template("change_password.html")
    return HTMLResponse(tpl.render(error="Ma'lumotlar muvaffaqiyatli o‘zgartirildi!", success=True, ADMIN_USER=new_username))

# ===== STAFF LIST (qidiruv bilan) =====
@app.get("/admin/staffs", response_class=HTMLResponse)
async def staff_list(request: Request, q: str = ""):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    rows = all_staff_with_stats()
    if q:
        ql = q.lower()
        rows = [
            r for r in rows
            if ql in str(r["staff_id"]).lower()
            or ql in r["name"].lower()
            or ql in r["position"].lower()
            or ql in r["region"].lower()
        ]

    tpl = templates.get_template("staff_list.html")
    return HTMLResponse(tpl.render(rows=rows, q=q))

# ===== STAFF ADD =====
@app.post("/admin/staff")
async def staff_add(
    request: Request,
    staff_id: int = Form(...),
    name: str = Form(...),
    position: str = Form(...),
    region: str = Form(...)
):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    add_staff(staff_id, name, position, region)
    return RedirectResponse("/admin/staffs", 303)

# ===== STAFF DELETE =====
@app.post("/admin/staff/{staff_id}/delete")
async def staff_delete(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    delete_staff(staff_id)
    return RedirectResponse("/admin/staffs", 303)

# ===== STAFF DETAIL =====
@app.get("/admin/staff/{staff_id}", response_class=HTMLResponse)
async def staff_detail(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    staff_info = None
    for sid, name, pos, reg in list_staff():
        if sid == staff_id:
            staff_info = {"name": name, "position": pos, "region": reg}
            break

    stats = get_stats(staff_id)
    now = datetime.now()
    tpl = templates.get_template("staff_detail.html")
    return HTMLResponse(tpl.render(
        staff_id=staff_id,
        name=staff_info["name"] if staff_info else "-",
        position=staff_info["position"] if staff_info else "-",
        region=staff_info["region"] if staff_info else "-",
        stats=stats,
        bot_username=BOT_USERNAME,
        now_year=now.year,
        now_month=now.month,
    ))

# ===== MONTH RESET =====
@app.post("/admin/staff/{staff_id}/reset/month")
async def reset_month_form(request: Request, staff_id: int, month: int = Form(...), year: int = Form(...)):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    delete_staff_month_votes(staff_id, year, month)
    return RedirectResponse(f"/admin/staff/{staff_id}", 303)

# ===== FULL RESET (one staff) =====
@app.post("/admin/staff/{staff_id}/reset/all")
async def reset_all_votes(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    delete_all_votes_for_staff(staff_id)
    return RedirectResponse(f"/admin/staff/{staff_id}", 303)

# ===== QR (download/display) =====
@app.get("/admin/staff/{staff_id}/qr")
async def staff_qr(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    filename, _ = make_qr_for_staff(staff_id, BOT_USERNAME)
    return FileResponse(filename, media_type="image/png")

# QR fullscreen view (sahifada ko‘rsatish)
@app.get("/admin/staff/{staff_id}/qr-view", response_class=HTMLResponse)
async def staff_qr_view(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    qr_file, _ = make_qr_for_staff(staff_id, BOT_USERNAME)  # <-- BU YER TUZATILDI
    tpl = templates.get_template("qr_view.html")
    return HTMLResponse(tpl.render(qr_file=qr_file))

# ===== EXPORT =====
@app.get("/admin/staff/{staff_id}/excel")
async def staff_excel_one(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    filename = export_one_staff_excel(staff_id)
    return FileResponse(filename)

@app.get("/admin/export/excel")
async def staff_excel(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    filename = export_excel()
    return FileResponse(filename)

@app.get("/admin/export/excel/month")
async def export_month(request: Request, year: int, month: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    filename = export_month_excel(year, month)
    return FileResponse(filename)

# ===== DEMO VOTE =====
@app.get("/vote/{staff_id}/{kind}")
async def vote_demo(staff_id: int, kind: str):
    if kind not in {"like", "dislike", "neutral"}:
        return {"ok": False}
    vote_staff(staff_id, kind)
    return {"ok": True}

# ===== DELETE ALL VOTES =====
@app.post("/admin/reset-votes")
async def reset_votes(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    from db import delete_all_votes
    delete_all_votes()
    return RedirectResponse("/admin/staffs", 303)

# ===== STAFF EDIT (page + save) =====
@app.get("/admin/staff/{staff_id}/edit", response_class=HTMLResponse)
async def staff_edit_page(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    staff_info = None
    for sid, name, pos, reg in list_staff():
        if sid == staff_id:
            staff_info = {"id": sid, "name": name, "position": pos, "region": reg}
            break
    tpl = templates.get_template("staff_edit.html")
    return HTMLResponse(tpl.render(staff=staff_info))

@app.post("/admin/staff/{staff_id}/edit", response_class=HTMLResponse)
async def staff_edit_save(
    request: Request,
    staff_id: int,
    name: str = Form(...),
    position: str = Form(...),
    region: str = Form(...)
):
    if not is_authed(request):
        return RedirectResponse("/", 303)
    add_staff(staff_id, name, position, region)
    # Back stack muammosiz ishlashi uchun 302/303 qaytarish
    return RedirectResponse(url=f"/admin/staff/{staff_id}", status_code=302)

# Healthcheck (docker uchun qulay)
@app.get("/health")
async def health():
    return {"ok": True}
