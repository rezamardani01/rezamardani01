"""Draw the profile's two contribution calendars from GitHub's GraphQL weeks."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path


COLORS = {
    "NONE": "#38343f",
    "FIRST_QUARTILE": "#54674f",
    "SECOND_QUARTILE": "#809b70",
    "THIRD_QUARTILE": "#aac68a",
    "FOURTH_QUARTILE": "#deeca3",
}
DAY = timedelta(days=1)


def calendar_days(weeks):
    records = {
        date.fromisoformat(day["date"]): day
        for week in weeks
        for day in week["contributionDays"]
    }
    last = max(records)
    first = max(min(records), last - 364 * DAY)
    # Index every date so an incomplete response cannot publish a misleading chart.
    return {first + n * DAY: records[first + n * DAY] for n in range((last - first).days + 1)}


def draw_grid(days, sundays, top, left, pitch, cell):
    parts = []
    months = []
    for column, sunday in enumerate(sundays):
        x = left + column * pitch
        for row in range(7):
            day = sunday + row * DAY
            if day not in days:
                continue
            if day.day == 1:
                months.append((column, day))
            color = COLORS[days[day]["contributionLevel"]]
            parts.append(
                f'<rect x="{x:.1f}" y="{top + row * pitch:.1f}" '
                f'width="{cell}" height="{cell}" rx="2" fill="{color}"/>'
            )
    if not months or months[0][0] >= 3:
        months.insert(0, (0, max(sundays[0], min(days))))
    for column, day in months:
        if column < len(sundays) - 1:
            parts.append(f'<text x="{left + column * pitch:.1f}" y="{top - 8}">{day:%b}</text>')
    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(
            f'<text x="{left - 7}" y="{top + row * pitch + cell:.1f}" '
            f'text-anchor="end">{label}</text>'
        )
    return "\n".join(parts)


def draw_calendar(days, compact):
    first, last = min(days), max(days)
    sunday = first - ((first.weekday() + 1) % 7) * DAY
    sundays = [sunday + n * 7 * DAY for n in range((last - sunday).days // 7 + 1)]
    contributions = sum(day["contributionCount"] for day in days.values())
    active = sum(day["contributionCount"] > 0 for day in days.values())
    period = f"{first:%d %b %Y} – {last:%d %b %Y}"
    total = f"{contributions:,} contribution{'s' if contributions != 1 else ''}"
    active_label = f"{active} active day{'s' if active != 1 else ''}"

    if compact:
        width, height, margin, rule = 356, 339, 17, 78
        heading_y, font_size = 39, 30
        date_x, date_y, anchor = margin, 64, "start"
        middle = (len(sundays) + 1) // 2
        grid = draw_grid(days, sundays[:middle], 111, 43, 10.9, 8.8)
        if middle < len(sundays):
            grid += "\n" + draw_grid(days, sundays[middle:], 217, 43, 10.9, 8.8)
    else:
        width, height, margin, rule = 840, 250, 29, 75
        heading_y, font_size = 52, 37
        date_x, date_y, anchor = width - margin, heading_y - 2, "end"
        grid = draw_grid(days, sundays, 113, 58, 14.25, 11.3)

    footer = height - 20
    legend_x = width - margin - 104
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{footer - 10}" width="10" height="10" '
        f'rx="2" fill="{color}"/>' for i, color in enumerate(COLORS.values())
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{total}</title>
<desc id="desc">{period}. {active_label}. Brighter squares indicate more contributions.</desc>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="#23212a" stroke="#4b444e"/>
<g font-family="Arial, Helvetica, sans-serif">
  <text x="{margin}" y="{heading_y}" fill="#fff2df" font-family="Georgia, serif" font-size="{font_size}">{total}</text>
  <text x="{date_x}" y="{date_y}" text-anchor="{anchor}" fill="#d2c7c9" font-size="16">{period}</text>
  <path d="M{margin} {rule}H{width - margin}" stroke="#49434e"/>
  <g fill="#d0c8cd" font-size="13">{grid}</g>
  <text x="{margin}" y="{footer}" fill="#deeca3" font-size="16">{active_label}</text>
  <g fill="#d0c8cd" font-size="13">
    <text x="{legend_x - 6}" y="{footer}" text-anchor="end">Less</text>{legend}
    <text x="{legend_x + 72}" y="{footer}">More</text>
  </g>
</g>
</svg>
'''


if __name__ == "__main__":
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    days = calendar_days(json.load(sys.stdin))
    for name, compact in [("activity-print.svg", False), ("activity-compact.svg", True)]:
        (output / name).write_text(draw_calendar(days, compact), encoding="utf-8")
