"""
בונה את דשבורד הביקורות של דרים איילנד.

קורא מגיליון הבקרה (קריאה בלבד), מחשב את כל המדדים, ומזריק אותם לתבנית
template/index.html. הפלט נכתב ל-dist/index.html, ואחר כך StaticCrypt מצפין אותו.

משתני סביבה:
  GOOGLE_SERVICE_ACCOUNT_JSON  תוכן קובץ המפתח של חשבון השירות (JSON)
  SHEET_ID                     מזהה גיליון הבקרה
  DATA_FILE                    (לפיתוח בלבד) נתיב ל-JSON עם נתונים גולמיים במקום קריאה מהגיליון

הסקריפט לא מדפיס תוכן ביקורות ללוג, כי לוגים של GitHub Actions במאגר ציבורי גלויים לכולם.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template" / "index.html"
OUT_DIR = ROOT / "dist"

TAB_DATA = "נתוני דשבורד"
TAB_GOOGLE = "מדדי גוגל"
TAB_DOMAINS = "תחומים"

CLASSES = ["חיובית", "מעורבת", "שלילית"]


def israel_now():
    # שעון ישראל, כולל שעון קיץ, בלי תלות בספריות נוספות
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Jerusalem"))
    except Exception:  # pragma: no cover
        return datetime.now(timezone(timedelta(hours=2)))


def serial_to_dt(v):
    """תאריך של Google Sheets (מספר סידורי) -> datetime."""
    if v in ("", None):
        return None
    if isinstance(v, (int, float)):
        return datetime(1899, 12, 30) + timedelta(days=float(v))
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v), fmt)
        except ValueError:
            pass
    return None


def fetch_from_sheet():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession

    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    session = AuthorizedSession(creds)
    sheet_id = os.environ["SHEET_ID"]
    ranges = [f"'{TAB_DATA}'!A2:L", f"'{TAB_GOOGLE}'!A2:C2", f"'{TAB_DOMAINS}'!A2:A"]
    params = "&".join("ranges=" + quote(r) for r in ranges)
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchGet?"
        f"{params}&valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=SERIAL_NUMBER"
    )
    r = session.get(url, timeout=60)
    if r.status_code != 200:
        # מדפיסים רק קוד שגיאה, בלי תוכן
        sys.exit(f"קריאת הגיליון נכשלה: HTTP {r.status_code}")
    vr = r.json().get("valueRanges", [])
    rows = vr[0].get("values", []) if len(vr) > 0 else []
    google = vr[1].get("values", [[]])[0] if len(vr) > 1 and vr[1].get("values") else []
    domains = [d[0] for d in (vr[2].get("values", []) if len(vr) > 2 else []) if d and str(d[0]).strip()]
    return rows, google, domains


def split_domains(cell):
    return [t.strip() for t in str(cell or "").split(",") if t.strip()]


def next_steps(avg, total):
    """כמה ביקורות של 5 כוכבים צריך כדי להגיע ליעדים הבאים."""
    if not avg or not total:
        return []
    out = []
    base = math.floor(avg * 10 + 1e-9) / 10
    for target in (round(base + 0.05, 2), round(base + 0.1, 1)):
        if target <= avg or target >= 5:
            continue
        n = math.ceil(total * (target - avg) / (5 - target))
        out.append({"target": target, "fiveStarNeeded": n})
    return out


def compute(rows, google, domains):
    reviews = []
    for r in rows:
        r = list(r) + [""] * (12 - len(r))
        if not str(r[0]).strip():
            continue
        dt = serial_to_dt(r[1])
        try:
            rating = int(float(r[3])) if r[3] not in ("", None) else None
        except (TypeError, ValueError):
            rating = None
        reviews.append({
            "id": str(r[0]),
            "date": dt,
            "name": str(r[2] or "").strip(),
            "rating": rating,
            "text": str(r[4] or "").strip(),
            "cls": str(r[5] or "").strip(),
            "topic": str(r[6] or "").strip(),
            "praised": split_domains(r[7]),
            "complaints": split_domains(r[8]),
            "answered": str(r[9]).strip() == "כן",
        })

    total = len(reviews)
    rated = [x["rating"] for x in reviews if x["rating"]]
    avg = sum(rated) / len(rated) if rated else None

    by_cls = {c: [x for x in reviews if x["cls"] == c] for c in CLASSES}
    classes = []
    for c in CLASSES:
        lst = by_cls[c]
        rs = [x["rating"] for x in lst if x["rating"]]
        classes.append({
            "name": c,
            "count": len(lst),
            "share": (len(lst) / total) if total else 0,
            "avg": (sum(rs) / len(rs)) if rs else None,
            "unanswered": sum(1 for x in lst if not x["answered"]),
        })

    domain_rows = []
    for d in domains:
        p = sum(1 for x in reviews if d in x["praised"])
        c = sum(1 for x in reviews if d in x["complaints"])
        domain_rows.append({"name": d, "praise": p, "complaints": c})

    months = {}
    for x in reviews:
        if not x["date"]:
            continue
        key = x["date"].strftime("%Y-%m")
        months.setdefault(key, []).append(x)
    monthly = []
    for key in sorted(months):
        lst = months[key]
        rs = [x["rating"] for x in lst if x["rating"]]
        monthly.append({
            "month": key,
            "count": len(lst),
            "avg": (sum(rs) / len(rs)) if rs else None,
            "negShare": sum(1 for x in lst if x["cls"] == "שלילית") / len(lst),
            "posShare": sum(1 for x in lst if x["cls"] == "חיובית") / len(lst),
        })

    dated = [x["date"] for x in reviews if x["date"]]
    period = {
        "from": min(dated).strftime("%d.%m.%Y") if dated else "",
        "to": max(dated).strftime("%d.%m.%Y") if dated else "",
    }

    unanswered = sorted(
        [x for x in reviews if not x["answered"]],
        key=lambda x: x["date"] or datetime.min,
        reverse=True,
    )
    unanswered_out = [{
        "name": x["name"],
        "date": x["date"].strftime("%d.%m.%Y") if x["date"] else "",
        "rating": x["rating"],
        "cls": x["cls"],
        "topic": x["topic"],
        "text": x["text"],
        "complaints": x["complaints"],
    } for x in unanswered]

    # גוגל: נתוני כל הזמנים (מתעדכנים בתרחיש 4 ב-Make)
    g_avg = g_total = None
    g_updated = ""
    try:
        g_avg = float(google[0]) if len(google) > 0 and google[0] != "" else None
        g_total = int(float(google[1])) if len(google) > 1 and google[1] != "" else None
        g_updated = str(google[2]) if len(google) > 2 else ""
    except (TypeError, ValueError):
        pass

    # בדיקות תקינות
    known = set(domains)
    unknown = sorted({t for x in reviews for t in x["praised"] + x["complaints"] if t not in known})
    checks = {
        "unknownDomains": unknown,
        "positiveWithComplaints": sum(1 for x in reviews if x["cls"] == "חיובית" and x["complaints"]),
        "negativeNoDomain": sum(1 for x in reviews if x["cls"] == "שלילית" and x["text"] and not x["complaints"]),
        "unclassified": sum(1 for x in reviews if not x["cls"]),
    }

    return {
        "generatedAt": israel_now().strftime("%d.%m.%Y %H:%M"),
        "period": period,
        "google": {
            "avg": g_avg,
            "total": g_total,
            "updated": g_updated,
            "steps": next_steps(g_avg, g_total),
        },
        "kpi": {
            "total": total,
            "avg": avg,
            "withText": sum(1 for x in reviews if x["text"]),
            "unansweredNegMixed": sum(1 for x in reviews if not x["answered"] and x["cls"] in ("שלילית", "מעורבת")),
        },
        "classes": classes,
        "domains": domain_rows,
        "monthly": monthly,
        "unanswered": unanswered_out,
        "checks": checks,
    }


def main():
    if os.environ.get("DATA_FILE"):
        raw = json.loads(Path(os.environ["DATA_FILE"]).read_text(encoding="utf-8"))
        rows, google, domains = raw["rows"], raw["google"], raw["domains"]
    else:
        rows, google, domains = fetch_from_sheet()

    data = compute(rows, google, domains)
    html = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    if "/*__DATA__*/null" not in html:
        sys.exit("התבנית חסרה את מציין המקום של הנתונים")
    html = html.replace("/*__DATA__*/null", payload)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    # בלי מספרים: במאגר ציבורי הלוג גלוי לכולם
    print("הדשבורד נבנה בהצלחה.")


if __name__ == "__main__":
    main()
