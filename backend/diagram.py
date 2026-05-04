"""
diagram.py — PlantUML Sequence Diagram Generator for CodeLens.

Generates PlantUML syntax from the parsed code structure,
encodes it using the PlantUML deflate+base64 scheme, and
fetches a rendered PNG from the free PlantUML public server
(https://www.plantuml.com/plantuml/png/<encoded>).

Public API
----------
generate_plantuml(parsed)   -> str          PlantUML @startuml ... @enduml text
get_plantuml_url(puml_text) -> str          URL to PNG on public server
fetch_diagram_png(puml_text)-> bytes | None PNG bytes, or None if server unreachable
"""

import re
import zlib
import requests
from backend.parser import ParsedCode


# ─────────────────────────────────────────────────────────────
# Noise filter — calls we never want in the diagram
# ─────────────────────────────────────────────────────────────

_NOISE_CALLS = frozenset({
    "print", "len", "str", "int", "float", "list", "dict", "set", "tuple",
    "range", "super", "self", "cls", "type", "isinstance", "hasattr",
    "getattr", "setattr", "append", "extend", "update", "get",
    "println", "toString", "equals", "hashCode", "getClass",
    "format", "join", "split", "strip", "lower", "upper",
})


# ─────────────────────────────────────────────────────────────
# PlantUML encoding  (deflate → custom base64)
# ─────────────────────────────────────────────────────────────

_ENCODE_TABLE = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "-_"
)


def _encode_6bit(b: int) -> str:
    return _ENCODE_TABLE[b & 0x3F]


def _encode_3bytes(b1: int, b2: int, b3: int) -> str:
    return (
        _encode_6bit(b1 >> 2)
        + _encode_6bit(((b1 & 0x3) << 4) | (b2 >> 4))
        + _encode_6bit(((b2 & 0xF) << 2) | (b3 >> 6))
        + _encode_6bit(b3 & 0x3F)
    )


def _plantuml_encode(text: str) -> str:
    """Compress with zlib (deflate) and encode with PlantUML's custom base64."""
    compressed = zlib.compress(text.encode("utf-8"), level=9)
    # Strip the 2-byte zlib header and 4-byte Adler-32 checksum
    data = compressed[2:-4]
    result = []
    i = 0
    while i < len(data):
        b1 = data[i]
        b2 = data[i + 1] if i + 1 < len(data) else 0
        b3 = data[i + 2] if i + 2 < len(data) else 0
        result.append(_encode_3bytes(b1, b2, b3))
        i += 3
    return "".join(result)


# ─────────────────────────────────────────────────────────────
# Interaction extraction  (shared with old Plotly version)
# ─────────────────────────────────────────────────────────────

def _extract_interactions(parsed: ParsedCode) -> tuple[list, list]:
    """
    Returns:
        participants  – ordered list of unique participant names
        interactions  – list of (src, dst, label) tuples, capped at 20
    """
    participants: list = []
    interactions: list = []

    def _add(name: str):
        if name not in participants:
            participants.append(name)

    if parsed.classes:
        for cls in parsed.classes:
            _add(cls.name)

        for cls in parsed.classes:
            for method in cls.methods:
                for call in method.calls:
                    if call in _NOISE_CALLS:
                        continue
                    for other in parsed.classes:
                        if other.name == cls.name:
                            continue
                        if any(m.name == call for m in other.methods):
                            interactions.append((cls.name, other.name, f"{call}()"))
                            break

        seen: set = set()
        deduped = []
        for item in interactions:
            if item not in seen and item[0] != item[1]:
                seen.add(item)
                deduped.append(item)
        interactions = deduped[:20]

    elif parsed.functions:
        _add("__main__")
        for fn in parsed.functions:
            _add(fn.name)

        if parsed.functions:
            first = parsed.functions[0]
            interactions.append(("__main__", first.name, f"{first.name}()"))

        for fn in parsed.functions:
            for call in fn.calls:
                if call in _NOISE_CALLS:
                    continue
                if any(f.name == call for f in parsed.functions):
                    interactions.append((fn.name, call, f"{call}()"))

        seen2: set = set()
        deduped2 = []
        for item in interactions:
            if item not in seen2 and item[0] != item[1]:
                seen2.add(item)
                deduped2.append(item)
        interactions = deduped2[:20]

    else:
        # Fallback — no structure found
        _add("User")
        _add("Module")
        _add("Output")
        interactions = [
            ("User",   "Module", "execute()"),
            ("Module", "Output", "process()"),
            ("Output", "Module", "result"),
            ("Module", "User",   "response"),
        ]

    for src, dst, _ in interactions:
        _add(src)
        _add(dst)

    return participants, interactions


# ─────────────────────────────────────────────────────────────
# PlantUML syntax builder
# ─────────────────────────────────────────────────────────────

def generate_plantuml(parsed: ParsedCode) -> str:
    """
    Build a PlantUML @startuml ... @enduml string from the parsed code.

    Styling uses a dark Mono theme with sky-blue arrows and
    navy participant boxes — visually consistent with the CodeLens dashboard.
    """
    participants, interactions = _extract_interactions(parsed)

    lines = [
        "@startuml",
        "",
        "' ── CodeLens auto-generated sequence diagram ──",
        "",
        "skinparam style strictuml",
        "skinparam backgroundColor #0f172a",
        "skinparam sequenceArrowThickness 2",
        "skinparam roundcorner 6",
        "",
        "skinparam participant {",
        "  BackgroundColor #1e293b",
        "  BorderColor     #0ea5e9",
        "  FontColor       #e2e8f0",
        "  FontSize        13",
        "  FontStyle       bold",
        "}",
        "",
        "skinparam sequence {",
        "  ArrowColor            #38bdf8",
        "  ArrowFontColor        #94a3b8",
        "  ArrowFontSize         11",
        "  LifeLineBorderColor   #334155",
        "  LifeLineBackgroundColor #0f172a",
        "  DividerBackgroundColor #1e293b",
        "  DividerBorderColor    #334155",
        "  GroupBorderColor      #0ea5e9",
        "  GroupFontColor        #e2e8f0",
        "  GroupHeaderFontColor  #38bdf8",
        "  NoteBackgroundColor   #1e293b",
        "  NoteBorderColor       #0ea5e9",
        "  NoteFontColor         #e2e8f0",
        "}",
        "",
    ]

    # Declare participants explicitly so the order is preserved
    for p in participants:
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", p)
        # Use alias so display name can contain spaces / special chars
        if safe == p:
            lines.append(f'participant "{p}"')
        else:
            lines.append(f'participant "{p}" as {safe}')

    lines.append("")

    # Write interactions
    if not interactions:
        lines.append("note over " + ", ".join(
            re.sub(r"[^a-zA-Z0-9_]", "_", p) for p in participants[:2]
        ) + " : No cross-component calls detected")
    else:
        for step, (src, dst, label) in enumerate(interactions, start=1):
            safe_src = re.sub(r"[^a-zA-Z0-9_]", "_", src)
            safe_dst = re.sub(r"[^a-zA-Z0-9_]", "_", dst)
            lines.append(f"{safe_src} -> {safe_dst} : {step}. {label}")

    lines += ["", "@enduml"]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# URL builder & PNG fetcher
# ─────────────────────────────────────────────────────────────

PLANTUML_SERVER = "https://www.plantuml.com/plantuml"


def get_plantuml_url(plantuml_text: str) -> str:
    """Return the URL that renders a PNG on the public PlantUML server."""
    encoded = _plantuml_encode(plantuml_text)
    return f"{PLANTUML_SERVER}/png/{encoded}"


def fetch_diagram_png(plantuml_text: str) -> bytes | None:
    """
    Fetch the rendered PNG bytes from the PlantUML public server.
    Returns None if the server is unreachable or returns an error.
    """
    url = get_plantuml_url(plantuml_text)
    try:
        resp = requests.get(url, timeout=15)
        ct = resp.headers.get("content-type", "")
        if resp.status_code == 200 and ct.startswith("image"):
            return resp.content
    except Exception:
        pass
    return None
