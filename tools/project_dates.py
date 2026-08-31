from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

DateStyle = Literal["preserve", "dd.mm.yy", "yyyy.mm.dd"]

_DATE_PATTERN = re.compile(
    r"(?<!\d)(?:(?P<year4>\d{4})(?P<sep4>[._-])(?P<month4>\d{1,2})(?P=sep4)(?P<day4>\d{1,2})|"
    r"(?P<day2>\d{1,2})(?P<sep2>[._-])(?P<month2>\d{1,2})(?P=sep2)(?P<year2>\d{2}))(?!\d)"
)


@dataclass(frozen=True)
class DateToken:
    value: date
    matched_text: str
    start: int
    end: int
    style: Literal["dmy_2", "ymd_4"]
    separator: str


def find_date_tokens(text: str) -> list[DateToken]:
    tokens: list[DateToken] = []
    for match in _DATE_PATTERN.finditer(str(text)):
        try:
            if match.group("year4"):
                value = date(
                    int(match.group("year4")),
                    int(match.group("month4")),
                    int(match.group("day4")),
                )
                style: Literal["dmy_2", "ymd_4"] = "ymd_4"
                separator = match.group("sep4")
            else:
                value = date(
                    2000 + int(match.group("year2")),
                    int(match.group("month2")),
                    int(match.group("day2")),
                )
                style = "dmy_2"
                separator = match.group("sep2")
        except ValueError:
            continue
        tokens.append(
            DateToken(
                value=value,
                matched_text=match.group(0),
                start=match.start(),
                end=match.end(),
                style=style,
                separator=separator,
            )
        )
    return tokens


def unique_folder_date(name: str) -> date | None:
    tokens = find_date_tokens(name)
    values = {token.value for token in tokens}
    if len(values) > 1:
        rendered = ", ".join(sorted(token.matched_text for token in tokens))
        raise ValueError(f"Folder name contains more than one date: {rendered}")
    return next(iter(values)) if values else None


def normalize_v10_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError("V10 Date* is missing.")
    iso = text.split(" ", 1)[0]
    try:
        return date.fromisoformat(iso)
    except ValueError:
        parsed = unique_folder_date(text)
        if parsed is None:
            raise ValueError(f"Unrecognised date: {value!r}")
        return parsed


def format_date(value: date, style: Literal["dd.mm.yy", "yyyy.mm.dd"]) -> str:
    if style == "dd.mm.yy":
        return value.strftime("%d.%m.%y")
    if style == "yyyy.mm.dd":
        return value.strftime("%Y.%m.%d")
    raise ValueError(f"Unsupported date style: {style}")


def replace_date_token(
    text: str,
    canonical_date: date,
    output_style: DateStyle,
    *,
    prepend_if_missing: bool = False,
) -> str:
    value = str(text)
    tokens = find_date_tokens(value)
    distinct = {token.value for token in tokens}
    if len(distinct) > 1:
        raise ValueError(f"Name contains conflicting dates: {value}")
    if output_style == "preserve":
        return value
    replacement = format_date(canonical_date, output_style)
    if not tokens:
        return f"{replacement}_{value}" if prepend_if_missing else value
    token = tokens[0]
    return value[: token.start] + replacement + value[token.end :]


def folder_name_with_date_style(
    folder_name: str,
    canonical_date: date,
    style: Literal["dd.mm.yy", "yyyy.mm.dd"],
) -> str:
    return replace_date_token(folder_name, canonical_date, style)


def working_filename_for(
    image: dict[str, Any],
    session: dict[str, Any],
    *,
    date_style: Literal["v10", "yyyy.mm.dd"] = "v10",
) -> str:
    proposed = str(
        image.get("working_filename") or image.get("original") or image.get("image_uid") or "image.jpg"
    ).strip()
    if date_style == "v10":
        return proposed
    if date_style != "yyyy.mm.dd":
        raise ValueError(f"Unsupported working-filename date style: {date_style}")
    canonical = normalize_v10_date(session.get("date"))
    return replace_date_token(
        proposed,
        canonical,
        "yyyy.mm.dd",
        prepend_if_missing=True,
    )
