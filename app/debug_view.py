import csv
import html
from io import StringIO


def render_bookings_table(shop_name: str, csv_text: str) -> str:
    rows = list(csv.reader(StringIO(csv_text)))
    header, body = (rows[0], rows[1:]) if rows else ([], [])

    def esc(value: str) -> str:
        return html.escape(value)

    if body:
        header_html = "".join(f"<th>{esc(col)}</th>" for col in header)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>"
            for row in body
        )
        content = (
            f"<table><thead><tr>{header_html}</tr></thead>"
            f"<tbody>{body_html}</tbody></table>"
        )
    else:
        content = '<p class="empty">No bookings logged yet.</p>'

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>{esc(shop_name)} — Bookings</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 2rem; color: #20241F; }}
  h1 {{ font-size: 1.1rem; margin-bottom: 1rem; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 720px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #ddd; font-size: .9rem; }}
  th {{ color: #565C4E; text-transform: uppercase; font-size: .7rem; letter-spacing: .04em; }}
  .empty {{ color: #565C4E; font-style: italic; }}
</style>
</head>
<body>
<h1>{esc(shop_name)} — Bookings</h1>
{content}
</body>
</html>
"""
