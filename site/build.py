#!/usr/bin/env python3
"""Build the web edition of Simply Automation from the LaTeX manuscript.

Usage:  python3 site/build.py          (writes the static site to docs/)

No dependencies beyond the Python standard library. The converter understands
the subset of LaTeX the manuscript actually uses: chapters, sections, quote,
center, itemize, enumerate, description, tabularx tables, and inline
\\textbf / \\textit / \\emph / \\texttt.
"""

import html
import json
from urllib.parse import quote
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "book"
SITE = ROOT / "site"
ILLUSTRATIONS = SITE / "illustrations.json"
OUT = ROOT / "docs"

TITLE = "Simply Automation"
SUBTITLE = "A History of Automation, One Tool at a Time"
AUTHOR = "Serene Dipster"
REPO = "https://github.com/lana-20/simply-automation"
SITE_URL = "https://lana-20.github.io/simply-automation/"
WORDS_PER_MINUTE = 230

# Reading order. `kind` groups the table of contents; `label` is the running head.
CHAPTERS = [
    dict(slug="prologue", src="prologue/prologue.tex", kind="front",
         label="Prologue", title="The Machine That Said “Again”"),
    dict(slug="part-01", src="parts/part-01-before-the-browser/chapter-01.tex", kind="part",
         label="Part I", title="Before the Browser",
         chapter="Chapter 1 — The Machine That Repeated Itself", stage="Repeat"),
    dict(slug="part-02", src="parts/part-02-first-great-test-automation-battle/part-02.tex", kind="part",
         label="Part II", title="The First Great Test Automation Battle",
         chapter="Chapter 2 — Selenium vs. UFT", stage="Automate"),
    dict(slug="part-03", src="parts/part-03-browser-becomes-programmable-infrastructure/part-03.tex", kind="part",
         label="Part III", title="The Browser Becomes Programmable Infrastructure",
         chapter="Chapter 3 — Selenium WebDriver", stage="Program"),
    dict(slug="part-04", src="parts/part-04-mobile-breaks-the-model/part-04.tex", kind="part",
         label="Part IV", title="Mobile Breaks the Model",
         chapter="Chapter 4 — Appium", stage="Program"),
    dict(slug="part-05", src="parts/part-05-automation-escapes-the-test/part-05.tex", kind="part",
         label="Part V", title="Automation Escapes the Test",
         chapter="Chapter 5 — When the UI Became Optional", stage="Integrate"),
    dict(slug="part-06", src="parts/part-06-automation-becomes-continuous/part-06.tex", kind="part",
         label="Part VI", title="Automation Becomes Continuous",
         chapter="Chapter 6 — Jenkins: The Machine That Never Stopped", stage="Continuously Execute"),
    dict(slug="part-07", src="parts/part-07-machine-starts-reasoning/part-07.tex", kind="part",
         label="Part VII", title="The Machine Starts Reasoning",
         chapter="Chapter 7 — Playwright: When Automation Learned to Wait", stage="Understand"),
    dict(slug="part-08", src="parts/part-08-agentic-era/part-08.tex", kind="part",
         label="Part VIII", title="The Agentic Era",
         chapter="Chapter 8 — Vibium: When the Automation Tool Became a Tool for the Machine", stage="Delegate"),
    dict(slug="part-09", src="parts/part-09-pattern-hidden-inside-the-tools/part-09.tex", kind="reflect",
         label="Part IX", title="What Seven Tools Reveal",
         chapter="Chapter 9 — The Pattern Hidden Inside the Tools"),
    dict(slug="part-10", src="parts/part-10-automation-wars/part-10.tex", kind="reflect",
         label="Part X", title="The Automation Wars",
         chapter="Chapter 10 — The Battles Were Never Just About Tools"),
    dict(slug="part-11", src="parts/part-11-simple-rules/part-11.tex", kind="reflect",
         label="Part XI", title="The Simple Rules",
         chapter="Chapter 11 — What Automation History Actually Teaches Us"),
    dict(slug="part-12", src="parts/part-12-after-automation/part-12.tex", kind="reflect",
         label="Part XII", title="After Automation",
         chapter="Chapter 12 — What Happens When the Machine Has the Work?"),
    dict(slug="epilogue", src="epilogue/epilogue.tex", kind="back",
         label="Epilogue", title="What Happens After “Again”?"),
    dict(slug="appendices", src="appendices/appendices.tex", kind="back",
         label="Appendices", title="Timeline, Tools, Glossary, Graveyard, Further Reading"),
]

# --------------------------------------------------------------------------
# LaTeX → HTML
# --------------------------------------------------------------------------

SYMBOLS = {
    r"\rightarrow": "→", r"\to": "→", r"\leftarrow": "←", r"\downarrow": "↓",
    r"\uparrow": "↑", r"\leftrightarrow": "↔", r"\Rightarrow": "⇒",
    r"\times": "×", r"\dots": "…", r"\ldots": "…", r"\cdot": "·",
    r"\approx": "≈", r"\neq": "≠", r"\geq": "≥", r"\leq": "≤",
}
INLINE_TAGS = {"textbf": "strong", "textit": "em", "emph": "em", "texttt": "code",
               "textsc": "span class=\"sc\"", "underline": "u"}
# Commands dropped along with their brace arguments.
DROP_WITH_ARGS = {"addcontentsline": 3, "label": 1, "vspace": 1, "vspace*": 1,
                  "hspace": 1, "titleformat": 0, "setlength": 2}
# Commands dropped on their own (no arguments).
DROP_BARE = {"noindent", "centering", "small", "normalsize", "large", "Large", "Huge",
             "huge", "footnotesize", "vfill", "mainmatter", "frontmatter", "backmatter",
             "appendix", "toprule", "midrule", "bottomrule", "newpage", "clearpage",
             "par", "bfseries", "itshape", "sffamily", "medskip", "bigskip", "smallskip",
             "hfill", "tableofcontents"}


def read_group(s, i, open_ch="{", close_ch="}"):
    """Return (content, index after the closing brace) for a group starting at s[i]."""
    assert s[i] == open_ch
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def skip_ws(s, i):
    while i < len(s) and s[i] in " \t":
        i += 1
    return i


def math(expr):
    out = expr
    for k in sorted(SYMBOLS, key=len, reverse=True):
        out = out.replace(k, SYMBOLS[k])
    out = re.sub(r"\\(text|mathrm|mathit)\{([^}]*)\}", r"\2", out)
    out = out.replace("^", "").replace("{", "").replace("}", "")
    return html.escape(out.strip(), quote=False)


def inline(s):
    """Convert inline LaTeX to HTML."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+\*?|.)", s[i:])
            name = m.group(1)
            i += len(m.group(0))
            if name == "\\":
                if i < len(s) and s[i] == "[":
                    _, i = read_group(s, i, "[", "]")
                out.append("<br>")
            elif name in ("&", "%", "$", "#", "_", "{", "}"):
                out.append(html.escape(name, quote=False))
            elif name == " ":
                out.append(" ")
            elif name == ",":
                out.append("\u202f")
            elif name in ("quad", "qquad"):
                out.append("\u2003")
            elif name == "textbar":
                out.append("|")
            elif name in ("ldots", "dots"):
                out.append("…")
            elif name == "initialcap":
                i = skip_ws(s, i)
                arg, i = read_group(s, i)
                out.append(f'<span class="initial">{inline(arg)}</span>')
            elif name in INLINE_TAGS:
                i = skip_ws(s, i)
                arg, i = read_group(s, i)
                tag = INLINE_TAGS[name]
                out.append(f"<{tag}>{inline(arg)}</{tag.split()[0]}>")
            elif name in ("framebox", "fbox"):
                arg, i = read_group(s, skip_ws(s, i))
                out.append(f'<span class="framed">{inline(arg)}</span>')
            elif name == "parbox":
                _, i = read_group(s, skip_ws(s, i))
                arg, i = read_group(s, skip_ws(s, i))
                out.append(inline(arg))
            elif name in DROP_WITH_ARGS:
                for _ in range(DROP_WITH_ARGS[name]):
                    i = skip_ws(s, i)
                    if i < len(s) and s[i] == "{":
                        _, i = read_group(s, i)
            elif name in DROP_BARE:
                pass
            elif name in SYMBOLS or ("\\" + name) in SYMBOLS:
                out.append(SYMBOLS["\\" + name])
            else:
                # Unknown command: keep its argument text, if any.
                i = skip_ws(s, i)
                if i < len(s) and s[i] == "{":
                    arg, i = read_group(s, i)
                    out.append(inline(arg))
        elif c == "$":
            j = s.index("$", i + 1)
            out.append(math(s[i + 1:j]))
            i = j + 1
        elif c == "{":
            arg, i = read_group(s, i)
            out.append(inline(arg))
        elif c == "}":
            i += 1
        elif c == "~":
            out.append("\u00a0")
            i += 1
        elif s.startswith("``", i):
            out.append("“"); i += 2
        elif s.startswith("''", i):
            out.append("”"); i += 2
        elif c == "`":
            out.append("‘"); i += 1
        elif c == "'":
            out.append("’"); i += 1
        elif s.startswith("---", i):
            out.append("—"); i += 3
        elif s.startswith("--", i):
            out.append("–"); i += 2
        elif c == "%" :
            # Comment to end of line.
            j = s.find("\n", i)
            i = len(s) if j == -1 else j
        elif c == '"':
            # Straight double quote typed directly into the source.
            prev = s[i - 1] if i else " "
            out.append("“" if prev in " \t\n([{" else "”")
            i += 1
        else:
            out.append(html.escape(c, quote=False))
            i += 1
    return re.sub(r"[ \t]+", " ", "".join(out))


def add_initial(body):
    """Wrap a paragraph's first letter in a drop cap, as \\initialcap does in Parts I–VIII.

    Leaves the paragraph alone if it already has one, or opens with markup, a digit or punctuation
    (a drop cap there reads badly)."""
    if body.startswith('<span class="initial">'):
        return body
    m = re.match(r"([A-Za-z])", body)
    if not m:
        return body
    return f'<span class="initial">{m.group(1)}</span>' + body[1:]


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).lower()
    text = re.sub(r"^\d+(\.\d+)*\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "section"


class Converter:
    """Line-oriented block converter with an environment stack."""

    def __init__(self):
        self.html = []
        self.para = []
        self.stack = []          # open environments
        self.item_open = []      # per list: is an <li>/<dd> currently open?
        self.table_rows = None
        self.toc = []            # (level, id, text)
        self.cap_next = True     # next top-level paragraph opens a chapter or section
        self.ids = set()

    def flush(self):
        text = " ".join(l.strip() for l in self.para).strip()
        self.para = []
        if not text:
            return
        body = inline(text).strip()
        if not body or body == "<br>":
            return
        body = re.sub(r"^(<br>\s*)+|(\s*<br>)+$", "", body)
        env = self.stack[-1] if self.stack else None
        if env in ("itemize", "enumerate", "description"):
            self.html.append(body)
        elif env == "center":
            self.html.append(f'<p class="center">{body}</p>')
        else:
            if self.cap_next and not self.stack:
                body = add_initial(body)
            self.cap_next = False
            cls = ' class="has-initial"' if body.startswith('<span class="initial">') else ""
            self.html.append(f"<p{cls}>{body}</p>")

    def heading(self, level, raw):
        self.flush()
        self.cap_next = True
        text = inline(raw).strip()
        num = None
        m = re.match(r"^(\d+\.\d+)\s+(.*)$", text)
        if m:
            num, text = m.group(1), m.group(2)
        hid = slugify(text)
        base, n = hid, 2
        while hid in self.ids:
            hid = f"{base}-{n}"; n += 1
        self.ids.add(hid)
        tag = {1: "h2", 2: "h3", 3: "h4"}[level]
        numhtml = f'<span class="sec-num">{num}</span>' if num else ""
        self.html.append(f'<{tag} id="{hid}">{numhtml}<a class="anchor" href="#{hid}">{text}</a></{tag}>')
        if level <= 2:
            self.toc.append((level, hid, text))

    def close_item(self):
        if self.item_open and self.item_open[-1]:
            env = self.stack[-1]
            self.html.append("</dd>" if env == "description" else "</li>")
            self.item_open[-1] = False

    def begin(self, env, rest):
        self.flush()
        if env != "center":
            self.cap_next = False
        if env in ("itemize", "enumerate", "description"):
            tag = {"itemize": "ul", "enumerate": "ol", "description": "dl"}[env]
            self.html.append(f"<{tag}>")
            self.item_open.append(False)
        elif env == "quote" or env == "quotation":
            self.html.append("<blockquote>")
        elif env == "center":
            self.html.append('<div class="center">')
        elif env in ("tabularx", "tabular"):
            self.table_rows = []
        self.stack.append(env)

    def end(self, env):
        self.flush()
        if env in ("tabularx", "tabular") and self.table_rows is not None:
            self.emit_table(self.table_rows)
            self.table_rows = None
        if env in ("itemize", "enumerate", "description"):
            self.close_item()
            self.item_open.pop()
            self.html.append({"itemize": "</ul>", "enumerate": "</ol>", "description": "</dl>"}[env])
        elif env in ("quote", "quotation"):
            self.html.append("</blockquote>")
        elif env == "center":
            self.html.append("</div>")
        if self.stack and self.stack[-1] == env:
            self.stack.pop()

    def emit_table(self, rows):
        # Drop the column spec (e.g. {lXX}) that follows \begin{tabularx}{\textwidth}.
        text = re.sub(r"^\s*\{[^}]*\}", "", " ".join(rows))
        cells = [r.strip() for r in re.split(r"\\\\", text) if r.strip()]
        out = ['<div class="table-wrap"><table>']
        for n, row in enumerate(cells):
            row = re.sub(r"\\(toprule|midrule|bottomrule|hline)", "", row).strip()
            if not row:
                continue
            cols = [inline(c).strip() for c in re.split(r"(?<!\\)&", row)]
            tag = "th" if n == 0 else "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cols) + "</tr>")
        out.append("</table></div>")
        self.html.append("\n".join(out))

    def item(self, rest):
        self.flush()
        env = self.stack[-1]
        self.close_item()
        if env == "description":
            rest = rest.lstrip()
            term = ""
            if rest.startswith("["):
                term, k = read_group(rest, 0, "[", "]")
                rest = rest[k:]
            self.html.append(f"<dt>{inline(term)}</dt><dd>")
        else:
            self.html.append("<li>")
        self.item_open[-1] = True
        if rest.strip():
            self.para.append(rest)

    def feed(self, src):
        # Put structural commands on their own lines so the line scanner sees them.
        src = re.sub(r"(\\(?:begin|end)\{[a-zA-Z*]+\}(?:\[[^\]]*\])?(?:\{[^}]*\})?)", r"\n\1\n", src)
        src = re.sub(r"(\\item)(?![a-zA-Z])", r"\n\1", src)
        src = re.sub(r"(\\(?:chapter|section|subsection)\*?\{)", r"\n\1", src)
        lines = src.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            i += 1
            if stripped.startswith("%"):
                continue
            m = re.match(r"\\begin\{([a-zA-Z*]+)\}(.*)", stripped)
            if m:
                env = m.group(1)
                if env == "titlepage":
                    while i < len(lines) and "\\end{titlepage}" not in lines[i]:
                        i += 1
                    i += 1
                    continue
                if env in ("table", "figure", "document"):
                    continue
                self.begin(env, m.group(2))
                continue
            m = re.match(r"\\end\{([a-zA-Z*]+)\}", stripped)
            if m:
                if m.group(1) not in ("table", "figure", "document"):
                    self.end(m.group(1))
                continue
            if self.table_rows is not None:
                self.table_rows.append(stripped)
                continue
            m = re.match(r"\\(chapter|section|subsection)\*?\{", stripped)
            if m:
                start = stripped.index("{")
                title, k = read_group(stripped, start)
                level = {"chapter": 1, "section": 2, "subsection": 3}[m.group(1)]
                self.heading(level, title)
                tail = stripped[k:].strip()
                if tail:
                    self.para.append(tail)
                continue
            if stripped.startswith("\\epigraphlem"):
                # \epigraphlem{quote}{source} — may span several lines.
                self.flush()
                chunk = stripped
                while chunk.count("{") > chunk.count("}") and i < len(lines):
                    chunk += " " + lines[i].strip(); i += 1
                k = skip_ws(chunk, len("\\epigraphlem"))
                quote, k = read_group(chunk, k)
                source, k = read_group(chunk, skip_ws(chunk, k))
                self.html.append(f'<figure class="epigraph"><blockquote><p>{inline(quote)}</p></blockquote>'
                                 f'<figcaption>{inline(source)}</figcaption></figure>')
                continue
            if stripped.startswith("\\item"):
                self.item(stripped[len("\\item"):])
                continue
            if not stripped:
                self.flush()
                continue
            self.para.append(line)
        self.flush()
        return "\n".join(self.html)


def convert(path):
    tex = path.read_text(encoding="utf-8")
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", tex, re.S)
    body = m.group(1) if m else tex
    conv = Converter()
    out = conv.feed(body)
    # Strip the heading duplicated by the page masthead (the part title and
    # the "Chapter N — …" line the manuscript opens with).
    return out, conv.toc


# --------------------------------------------------------------------------
# Page templates
# --------------------------------------------------------------------------

FONTS = ("https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700"
         "&family=Jost:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;"
         "0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=IBM+Plex+Mono:wght@400;500&display=swap")

THEME_BOOT = """<script>
try{var t=localStorage.getItem('sa-theme');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}
</script>"""


def page(title, body, description, extra_head="", body_class="", path="index.html"):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="author" content="{AUTHOR}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="book">
<meta property="og:site_name" content="{TITLE}">
<meta property="og:url" content="{SITE_URL}{'' if path == 'index.html' else path}">
<meta property="og:image" content="{SITE_URL}assets/share-card.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Simply Automation by {AUTHOR}: the book cover beside the title, free to read online.">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{SITE_URL}{'' if path == 'index.html' else path}">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="assets/book.css">
{THEME_BOOT}
{extra_head}
</head>
<body class="{body_class}">
{body}
<script src="assets/book.js"></script>
</body>
</html>
"""


def topbar(current_label=""):
    crumb = f'<span class="bar-part">{html.escape(current_label)}</span>' if current_label else ""
    return f"""<header class="bar">
  <a class="bar-title" href="index.html">Simply Automation</a>
  {crumb}
  <nav class="bar-actions" aria-label="Book">
    <a href="index.html#contents">Contents</a>
    <button type="button" class="theme-toggle" id="theme-toggle" aria-label="Switch color theme">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 7a5 5 0 0 1 0 10z" fill="currentColor"/></svg>
    </button>
  </nav>
  <div class="progress" aria-hidden="true"><span id="progress"></span></div>
</header>"""


def footer():
    return f"""<footer class="colophon">
  <p><em>{TITLE}</em> by {AUTHOR} is licensed under
  <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
  You may share and adapt it with attribution.</p>
  <p><a href="{REPO}">Source on GitHub</a> · <a href="{REPO}/blob/main/CONTRIBUTING.md">Contribute</a> · Tools come and go. The pattern remains.</p>
</footer>"""


def reading_minutes(tex_path):
    tex = tex_path.read_text(encoding="utf-8")
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", tex, re.S)
    body = re.sub(r"\\[a-zA-Z]+\*?", " ", m.group(1) if m else tex)
    words = len(re.findall(r"[A-Za-z][A-Za-z'’-]*", body))
    return words, max(1, round(words / WORDS_PER_MINUTE))


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(re.sub(r"<[^>]+>", "", text)).lower()).strip()


def drop_masthead_headings(body_html, toc, ch):
    """Remove the opening part/chapter headings that the page masthead already shows."""
    shown = {_norm(ch["title"]), _norm(f'{ch["label"]} — {ch["title"]}')}
    if ch.get("chapter"):
        shown.add(_norm(ch["chapter"]))
        shown.add(_norm(ch["chapter"].split("—", 1)[-1]))
    dropped = set()
    while True:
        m = re.match(r'\s*<h[23] id="([^"]+)">.*?<a class="anchor" href="#[^"]+">(.*?)</a></h[23]>', body_html)
        if not m or _norm(m.group(2)) not in shown:
            break
        dropped.add(m.group(1))
        body_html = body_html[m.end():]
    return body_html, [t for t in toc if t[1] not in dropped]


def plate(ch):
    """The chapter illustration under the masthead, if one has been published for this chapter."""
    img = SITE / "assets/illustrations" / f"{ch['slug']}.jpg"
    if not img.exists():
        return ""
    alts = json.loads(ILLUSTRATIONS.read_text(encoding="utf-8")) if ILLUSTRATIONS.exists() else {}
    alt = alts.get(ch["slug"], f"Illustration for {ch['label']}: {ch['title']}")
    return (f'<figure class="plate"><img src="assets/illustrations/{ch["slug"]}.jpg" width="1400" height="933" '
            f'alt="{html.escape(alt)}" decoding="async"></figure>')


def build_chapter(idx, ch):
    body_html, toc = convert(BOOK / ch["src"])
    body_html, toc = drop_masthead_headings(body_html, toc, ch)
    words, minutes = reading_minutes(BOOK / ch["src"])
    ch["words"], ch["minutes"] = words, minutes
    prev_ch = CHAPTERS[idx - 1] if idx > 0 else None
    next_ch = CHAPTERS[idx + 1] if idx + 1 < len(CHAPTERS) else None

    toc_items = "\n".join(
        f'<li class="lvl{lvl}"><a href="#{hid}">{text}</a></li>' for lvl, hid, text in toc)
    kicker = ch["label"]
    if ch.get("chapter"):
        heading_sub = f'<p class="mast-chapter">{html.escape(ch["chapter"])}</p>'
    else:
        heading_sub = ""

    def link(c, rel):
        if not c:
            return "<span></span>"
        word = "Previous" if rel == "prev" else "Next"
        return (f'<a class="pager-{rel}" rel="{rel}" href="{c["slug"]}.html">'
                f'<span class="pager-dir">{word} · {html.escape(c["label"])}</span>'
                f'<span class="pager-title">{html.escape(c["title"])}</span></a>')

    where = f"{ch['label']}: {ch['title']}"
    feedback_url = (f"{REPO}/issues/new?template=feedback.yml"
                    f"&title={quote('Feedback: ' + where)}&chapter={quote(where)}")
    edit_url = f"{REPO}/edit/main/book/{ch['src']}"
    participate = f"""<aside class="participate" aria-label="Help shape this chapter">
      <p>This book is written in the open. Spot an error, or have a thought about this chapter?</p>
      <p class="participate-links"><a href="{html.escape(feedback_url)}">Leave feedback</a><a href="{edit_url}">Suggest an edit</a><a href="{REPO}/blob/main/CONTRIBUTING.md">How to contribute</a></p>
    </aside>"""
    body = f"""{topbar(ch['label'])}
<div class="reader">
  <aside class="rail" aria-label="In this part">
    <p class="rail-label">In this part</p>
    <ol class="rail-list">{toc_items}</ol>
  </aside>
  <main class="chapter" id="main">
    <header class="mast">
      <p class="mast-kicker">{html.escape(kicker)}<span class="mast-dot" aria-hidden="true"></span>{minutes} min read</p>
      <h1>{html.escape(ch['title'])}</h1>
      {heading_sub}
      <div class="rule" aria-hidden="true"><span></span></div>
    </header>
    {plate(ch)}
    <article class="prose">
{body_html}
    </article>
    {participate}
    <nav class="pager" aria-label="Chapters">
      {link(prev_ch, 'prev')}
      {link(next_ch, 'next')}
    </nav>
  </main>
</div>
{footer()}"""
    description = f"{ch['label']}: {ch['title']}. From {TITLE} by {AUTHOR}."
    return page(f"{ch['label']}: {ch['title']} · {TITLE}", body, description, body_class="is-chapter",
                path=f"{ch['slug']}.html")


def build_index():
    groups = [
        ("front", "Opening"),
        ("part", "The seven tools"),
        ("reflect", "What the tools reveal"),
        ("back", "Closing"),
    ]
    blocks = []
    for kind, heading in groups:
        rows = []
        for ch in CHAPTERS:
            if ch["kind"] != kind:
                continue
            chap = f'<span class="toc-chapter">{html.escape(ch["chapter"])}</span>' if ch.get("chapter") else ""
            stage = f'<span class="toc-stage">{html.escape(ch["stage"])}</span>' if ch.get("stage") else ""
            rows.append(f"""<li><a href="{ch['slug']}.html">
  <span class="toc-label">{html.escape(ch['label'])}</span>
  <span class="toc-main"><span class="toc-title">{html.escape(ch['title'])}</span>{chap}</span>
  <span class="toc-meta">{stage}<span class="toc-min">{ch['minutes']} min</span></span>
</a></li>""")
        blocks.append(f'<section class="toc-group"><h3>{heading}</h3><ol class="toc">{"".join(rows)}</ol></section>')

    total_words = sum(c["words"] for c in CHAPTERS)
    total_hours = total_words / WORDS_PER_MINUTE / 60
    stages = ["Repeat", "Automate", "Program", "Integrate", "Continuously Execute", "Understand", "Delegate"]
    stage_html = "".join(f"<li>{s}</li>" for s in stages)

    tools = [
        ("Selenium / UFT", "Can repetitive user interaction be automated?"),
        ("Selenium WebDriver", "Can the browser become programmable infrastructure?"),
        ("Appium", "Can browser automation ideas move to mobile devices?"),
        ("API Automation / Postman", "Do we need the UI at all?"),
        ("Jenkins", "Can automation run continuously without a human starting it?"),
        ("Playwright", "Can automation understand more of the browser’s state and context?"),
        ("Vibium", "Can automation itself become a tool for machines?"),
    ]
    tool_rows = "".join(f"<tr><th scope=\"row\">{t}</th><td>{q}</td></tr>" for t, q in tools)

    body = f"""{topbar()}
<main class="home" id="main">
  <section class="hero">
    <div class="hero-text">
      <p class="eyebrow">A book, free to read</p>
      <h1 class="book-title">Simply<br>Automation</h1>
      <p class="book-sub">{SUBTITLE}</p>
      <div class="rule" aria-hidden="true"><span></span></div>
      <p class="book-author">{AUTHOR}</p>
      <p class="hero-lede">Automation didn’t begin with artificial intelligence. It began with repetition.
      From mechanical looms to AI agents, this is the story of how people taught machines to take over
      the work they’d rather not do, told through seven tools and the questions each one tried to answer.</p>
      <div class="hero-actions">
        <a class="btn" href="prologue.html">Start reading</a>
        <a class="btn-quiet" href="#contents">Contents</a>
      </div>
      <p class="hero-facts">{len(CHAPTERS) - 3} parts · about {total_words // 1000}k words · roughly {total_hours:.0f} hours · CC BY 4.0</p>
    </div>
    <figure class="hero-cover">
      <img src="assets/cover.jpg" width="716" height="1024" alt="Cover of Simply Automation: a pilot stands on a red flying craft docked at a towering yellow wall, looking toward a line of planets shrinking to a small sun.">
    </figure>
  </section>

  <section class="boundary" aria-labelledby="boundary-h">
    <h2 id="boundary-h">The moving boundary</h2>
    <p>Every era moved the line between what humans must do and what machines can reliably do.</p>
    <ol class="stages">{stage_html}</ol>
  </section>

  <section class="contents" id="contents" aria-labelledby="contents-h">
    <h2 id="contents-h">Contents</h2>
    {''.join(blocks)}
  </section>

  <section class="tools" aria-labelledby="tools-h">
    <h2 id="tools-h">Seven tools, seven questions</h2>
    <div class="table-wrap"><table class="tool-table"><tbody>{tool_rows}</tbody></table></div>
  </section>

  <section class="about" aria-labelledby="about-h">
    <h2 id="about-h">Open, and meant to be shared</h2>
    <p>The full text is published under the Creative Commons Attribution 4.0 license. Read it here, copy it,
    translate it, teach from it, or build on it. Credit <strong>{AUTHOR}</strong> and link back to the source.</p>
    <p>Each chapter opens with a passage from Stanisław Lem’s <em>Summa Technologiae</em> (1964), translated by
    Joanna Zylinska (University of Minnesota Press, 2013). Those quotations remain the property of their copyright
    holders and are not covered by the Creative Commons license.</p>
    <p>The manuscript is written in LaTeX and developed in the open. Readers help shape it: leave feedback on any
    chapter, report a correction, or suggest an edit. <a href="{REPO}/blob/main/CONTRIBUTING.md">Here’s how to contribute</a>.</p>
  </section>
</main>
{footer()}"""
    description = (f"{TITLE}: {SUBTITLE}. A free, openly licensed book by {AUTHOR} on the history of "
                   "automation, from punched cards to AI agents.")
    return page(f"{TITLE} · {AUTHOR}", body, description, body_class="is-home")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(SITE / "assets", OUT / "assets")
    for idx, ch in enumerate(CHAPTERS):
        (OUT / f"{ch['slug']}.html").write_text(build_chapter(idx, ch), encoding="utf-8")
    (OUT / "index.html").write_text(build_index(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    cname = SITE / "CNAME"
    if cname.exists():
        shutil.copy2(cname, OUT / "CNAME")
    total = sum(c["words"] for c in CHAPTERS)
    print(f"Built {len(CHAPTERS) + 1} pages, {total:,} words → {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
