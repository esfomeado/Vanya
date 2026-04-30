import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


class DemonaShieldError(Exception):
    pass


class DemonaShieldLocked(Exception):
    def __init__(self, seconds: int):
        super().__init__(f"Demona Shield locked for {seconds}s")
        self.seconds = seconds


_MATH_RE = re.compile(r"(-?\d+)\s*([+\-*/xX×·])\s*(-?\d+)")
_PUZZLE_LEFT_RE = re.compile(r"left\s*:\s*(-?\d+)\s*px", re.IGNORECASE)


def is_shield_challenge(html: str) -> bool:
    if not html:
        return False
    if "Demona Shield" not in html:
        return False
    return 'name="human_answer"' in html and 'name="human_token"' in html


def parse_shield(shield_url: str, html: str) -> tuple[str, dict]:
    soup = BeautifulSoup(html, "html.parser")

    lock_el = soup.find(id="lockTimer")
    if lock_el is not None:
        raw = (lock_el.get_text(strip=True) or "0").strip()
        try:
            secs = int(raw)
        except ValueError:
            secs = 0
        raise DemonaShieldLocked(max(secs, 0))

    form = soup.find("form")
    if form is None:
        raise DemonaShieldError("Shield form not found")

    question_el = soup.find("div", class_="question")
    if question_el is not None:
        answer = _solve_math(question_el.get_text(" ", strip=True))
    else:
        hole_el = soup.find("div", class_="puzzle-hole")
        if hole_el is None:
            raise DemonaShieldError("Shield challenge not found")
        answer = _solve_puzzle(hole_el)

    data: dict[str, str] = {}
    for hidden in form.find_all("input", {"type": "hidden"}):
        name = hidden.get("name")
        if not name:
            continue
        data[name] = hidden.get("value", "")
    data["human_answer"] = answer

    action = (form.get("action") or "").strip()
    if not action:
        post_url = shield_url
    elif action.startswith(("http://", "https://")):
        post_url = action
    else:
        post_url = urljoin(shield_url, action)

    return post_url, data


def _solve_math(question: str) -> str:
    match = _MATH_RE.search(question)
    if not match:
        raise DemonaShieldError(f"Could not parse math question: {question!r}")

    a = int(match.group(1))
    op = match.group(2)
    b = int(match.group(3))

    if op in ("*", "x", "X", "×", "·"):
        result = a * b
    elif op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    elif op == "/":
        result = 0 if b == 0 else a // b
    else:
        raise DemonaShieldError(f"Unknown operator {op!r}")

    logging.info(f"Demona Shield math: {a} {op} {b} = {result}")
    return str(result)


def _solve_puzzle(hole_el) -> str:
    style = hole_el.get("style", "") or ""
    match = _PUZZLE_LEFT_RE.search(style)
    if match is None:
        raise DemonaShieldError(f"Could not parse puzzle hole style: {style!r}")

    hole_left = max(0, int(match.group(1)))
    answer = hole_left

    shape = next(
        (cls for cls in hole_el.get("class", []) or [] if cls.startswith("shape-")),
        None,
    )
    logging.info(
        f"Demona Shield puzzle: hole_left={hole_left} shape={shape} "
        f"style={style!r} answer={answer}"
    )
    return str(answer)
