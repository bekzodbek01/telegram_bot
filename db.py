import sqlite3
from pathlib import Path

DB_PATH = Path("data.db")

def _conn():
    return sqlite3.connect(DB_PATH)

# ----------------- INIT DB -----------------

def init_db():
    with _conn() as con:
        cur = con.cursor()

        # Staff table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS staff(
            staff_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            position TEXT,
            region TEXT
        );
        """)

        # Votes table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS votes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            kind TEXT CHECK(kind IN ('like','dislike','neutral')) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(staff_id) REFERENCES staff(staff_id) ON DELETE CASCADE
        );
        """)

        con.commit()


# ----------------- STAFF CRUD -----------------

def add_staff(staff_id: int, name: str, position: str, region: str):
    with _conn() as con:
        con.execute("""
            INSERT OR REPLACE INTO staff(staff_id, name, position, region)
            VALUES (?, ?, ?, ?);
        """, (staff_id, name, position, region))
        con.commit()


def delete_staff(staff_id: int):
    with _conn() as con:
        con.execute("DELETE FROM staff WHERE staff_id = ?;", (staff_id,))
        con.commit()


def list_staff():
    with _conn() as con:
        cur = con.execute("""
            SELECT staff_id, name, position, region
            FROM staff
            ORDER BY staff_id;
        """)
        return cur.fetchall()


# ----------------- VOTES -----------------

def vote_staff(staff_id: int, kind: str):
    with _conn() as con:
        con.execute("""
            INSERT INTO votes(staff_id, kind)
            VALUES (?, ?);
        """, (staff_id, kind))
        con.commit()


def get_stats(staff_id: int):
    """Bitta xodimning umumiy statistikasi."""
    with _conn() as con:
        cur = con.execute("""
            SELECT
              SUM(CASE WHEN kind='like' THEN 1 ELSE 0 END) as likes,
              SUM(CASE WHEN kind='dislike' THEN 1 ELSE 0 END) as dislikes,
              SUM(CASE WHEN kind='neutral' THEN 1 ELSE 0 END) as neutrals
            FROM votes
            WHERE staff_id = ?;
        """, (staff_id,))

        row = cur.fetchone()
        likes, dislikes, neutrals = row if row else (0, 0, 0)

        return {
            "likes": likes or 0,
            "dislikes": dislikes or 0,
            "neutrals": neutrals or 0,
            "total": (likes or 0) + (dislikes or 0) + (neutrals or 0)
        }


def all_staff_with_stats():
    """Barcha xodimlar + statistikalar."""
    with _conn() as con:
        cur = con.execute("""
        SELECT 
            s.staff_id, s.name, s.position, s.region,
            SUM(CASE WHEN v.kind='like' THEN 1 ELSE 0 END) as likes,
            SUM(CASE WHEN v.kind='dislike' THEN 1 ELSE 0 END) as dislikes,
            SUM(CASE WHEN v.kind='neutral' THEN 1 ELSE 0 END) as neutrals
        FROM staff s
        LEFT JOIN votes v ON v.staff_id = s.staff_id
        GROUP BY s.staff_id, s.name, s.position, s.region
        ORDER BY s.staff_id;
        """)

        rows = []
        for sid, name, pos, reg, likes, dislikes, neutrals in cur.fetchall():
            likes = likes or 0
            dislikes = dislikes or 0
            neutrals = neutrals or 0

            rows.append({
                "staff_id": sid,
                "name": name,
                "position": pos,
                "region": reg,
                "likes": likes,
                "dislikes": dislikes,
                "neutrals": neutrals,
                "total": likes + dislikes + neutrals
            })

        return rows


# ----------------- MONTHLY STATS -----------------

def get_month_stats(year: int, month: int):
    """Berilgan oy bo‘yicha barcha xodimlar statistikasi."""
    with _conn() as con:
        cur = con.execute("""
            SELECT 
                staff_id,
                SUM(CASE WHEN kind='like' THEN 1 ELSE 0 END) as likes,
                SUM(CASE WHEN kind='dislike' THEN 1 ELSE 0 END) as dislikes,
                SUM(CASE WHEN kind='neutral' THEN 1 ELSE 0 END) as neutrals
            FROM votes
            WHERE strftime('%Y', created_at) = ?
              AND strftime('%m', created_at) = ?
            GROUP BY staff_id;
        """, (str(year), f"{month:02}"))

        results = []
        for sid, like, dislike, neutral in cur.fetchall():
            like = like or 0
            dislike = dislike or 0
            neutral = neutral or 0

            results.append({
                "staff_id": sid,
                "likes": like,
                "dislikes": dislike,
                "neutrals": neutral,
                "total": like + dislike + neutral
            })

        return results


# ----------------- MONTHLY RESET -----------------

def delete_month_votes(year: int, month: int):
    with _conn() as con:
        con.execute("""
            DELETE FROM votes
            WHERE strftime('%Y', created_at) = ?
              AND strftime('%m', created_at) = ?;
        """, (str(year), f"{month:02}"))
        con.commit()


def delete_staff_month_votes(staff_id: int, year: int, month: int):
    with _conn() as con:
        con.execute("""
            DELETE FROM votes
            WHERE staff_id = ?
              AND strftime('%Y', created_at) = ?
              AND strftime('%m', created_at) = ?;
        """, (staff_id, str(year), f"{month:02}"))
        con.commit()


# ----------------- FULL RESET FOR ONE STAFF -----------------

def delete_all_votes_for_staff(staff_id: int):
    with _conn() as con:
        con.execute("DELETE FROM votes WHERE staff_id = ?;", (staff_id,))
        con.commit()


# ----------------- RESET ONLY VOTES (KEEP STAFF) -----------------

def delete_all_votes():
    """Barcha ovozlarni tozalaydi, staff qoldiriladi."""
    with _conn() as con:
        con.execute("DELETE FROM votes;")
        con.commit()

        con.execute("DELETE FROM sqlite_sequence WHERE name='votes';")
        con.commit()
