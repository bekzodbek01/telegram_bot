import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import dotenv_values

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

# ===================== ENV =====================
ENV_PATH = ".env"
env_data = dotenv_values(ENV_PATH)

ADMIN_USER = env_data.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = env_data.get("ADMIN_PASSWORD", "admin123")
BOT_USERNAME = env_data.get("BOT_USERNAME", "SenBaholash_bot")

# ===================== EXCEL MIME-TYPE =====================
EXCEL_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ===================== APP =====================
app = FastAPI(title="SenBaholash Admin", docs_url=None, redoc_url=None)

# STATIC
app.mount("/static", StaticFiles(directory="static"), name="static")

# TEMPLATES
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"])
)


# ===================== AUTH =====================
def is_authed(request: Request) -> bool:
    return request.cookies.get("auth") == "true"


def auth_ok_redirect(path="/admin/staffs"):
    r = RedirectResponse(path, 303)
    r.set_cookie("auth", "true")
    return r


def auth_clear():
    r = RedirectResponse("/", 303)
    r.delete_cookie("auth")
    return r


# ===================== STARTUP =====================
@app.on_event("startup")
def startup():
    init_db()


# ===================== LOGIN =====================
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authed(request):
        return RedirectResponse("/admin/staffs", 303)

    tpl = templates.get_template("login.html")
    return HTMLResponse(tpl.render(error=None))


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        return auth_ok_redirect()

    tpl = templates.get_template("login.html")
    return HTMLResponse(tpl.render(error="Login yoki parol noto‘g‘ri!"))


@app.get("/logout")
async def logout(request: Request):
    return auth_clear()


# ===================== STAFF LIST =====================
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


# ===================== STAFF ADD =====================
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


# ===================== STAFF DELETE =====================
@app.post("/admin/staff/{staff_id}/delete")
async def staff_delete(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    delete_staff(staff_id)
    return RedirectResponse("/admin/staffs", 303)


# ===================== STAFF DETAIL =====================
@app.get("/admin/staff/{staff_id}", response_class=HTMLResponse)
async def staff_detail(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    staff_info = next(
        ({"name": n, "position": p, "region": r}
         for sid, n, p, r in list_staff() if sid == staff_id),
        None
    )

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


# ===================== STAFF EDIT =====================
@app.get("/admin/staff/{staff_id}/edit", response_class=HTMLResponse)
async def staff_edit_page(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    staff_info = next(
        ({"id": sid, "name": n, "position": p, "region": r}
         for sid, n, p, r in list_staff() if sid == staff_id),
        None
    )

    tpl = templates.get_template("staff_edit.html")
    return HTMLResponse(tpl.render(staff=staff_info))


@app.post("/admin/staff/{staff_id}/edit")
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
    return RedirectResponse(f"/admin/staff/{staff_id}", 302)


# ===================== QR =====================
@app.get("/admin/staff/{staff_id}/qr")
async def staff_qr(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    file = make_qr_for_staff(staff_id, BOT_USERNAME)
    return FileResponse(file)


@app.get("/admin/staff/{staff_id}/qr-view", response_class=HTMLResponse)
async def staff_qr_view(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    qr_file = make_qr_for_staff(staff_id, BOT_USERNAME)
    qr_file = "/" + qr_file

    tpl = templates.get_template("qr_view.html")
    return HTMLResponse(tpl.render(qr_file=qr_file))


# ===================== EXCEL EXPORT (ZIP MUAMMO YO‘Q) =====================
@app.get("/admin/staff/{staff_id}/excel")
async def staff_excel_one(request: Request, staff_id: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename = export_one_staff_excel(staff_id)

    return FileResponse(
        filename,
        media_type=EXCEL_TYPE,
        filename=os.path.basename(filename)
    )


@app.get("/admin/export/excel")
async def staff_excel(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename = export_excel()

    return FileResponse(
        filename,
        media_type=EXCEL_TYPE,
        filename=os.path.basename(filename)
    )


@app.get("/admin/export/excel/month")
async def export_month(request: Request, year: int, month: int):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    filename = export_month_excel(year, month)

    return FileResponse(
        filename,
        media_type=EXCEL_TYPE,
        filename=os.path.basename(filename)
    )


# ===================== VOTE =====================
@app.get("/vote/{staff_id}/{kind}")
async def vote_demo(staff_id: int, kind: str):
    if kind not in {"like", "dislike", "neutral"}:
        return {"ok": False}

    vote_staff(staff_id, kind)
    return {"ok": True}


# ===================== DELETE ALL VOTES =====================
@app.post("/admin/reset-votes")
async def reset_votes(request: Request):
    if not is_authed(request):
        return RedirectResponse("/", 303)

    from db import delete_all_votes
    delete_all_votes()
    return RedirectResponse("/admin/staffs", 303)


# ===================== HEALTH =====================
@app.get("/health")
async def health():
    return {"ok": True}
