#!/usr/bin/env python3
"""Build a lab report .docx from data.json on top of the skill templates.

Usage:
    python3 scripts/build_report.py data.json out.docx
    python3 scripts/build_report.py data.json --next-to assignment.docx
    python3 scripts/build_report.py --read assignment.docx|assignment.pdf
    python3 scripts/build_report.py --check out.docx [--dump]

Templates: "code" (subjects/_default) and "nocode" (subjects/_nocode).
Exit codes: 0 ok, 1 error, 2 violations, 3 missing optional dependency.
"""

import argparse
import copy
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
REQUIREMENTS = SKILL_DIR / "requirements.txt"

try:
    from docx import Document
    from docx.image.image import Image as DocxImage
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml.ns import qn
    from docx.shared import Inches
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from lxml import etree
except ImportError as exc:
    sys.exit(
        "missing Python package (%s); run once: python3 -m pip install -r %s"
        % (exc, REQUIREMENTS)
    )

TEMPLATES = {
    "code": SKILL_DIR / "subjects" / "_default" / "template.docx",
    "nocode": SKILL_DIR / "subjects" / "_nocode" / "template.docx",
}
SETTINGS = SKILL_DIR / "settings.json"
SETTINGS_EXAMPLE = SKILL_DIR / "settings.example.json"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

BODY_START = "Цель работы"
CODE_LABEL = "Код программы"
SHOT_LABEL = "Скрин выполнения"
Q_HEADER = "КОНТРОЛЬНЫЕ ВОПРОСЫ"

C_LIKE = {"c", "cpp", "cs", "java", "js", "ts", "go", "php", "rust", "kotlin", "swift"}
HASH_LIKE = {"python", "sh", "bash", "ruby", "r"}
PASCAL = {"pascal", "delphi"}
MATLAB = {"matlab", "octave"}
MARKUP = {"html", "xml"}

sys.path.insert(0, str(HERE))
import make_screenshot  # noqa: E402


def paragraph_text(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t")))


def replace_placeholders(el, mapping):
    """Replace {{...}} even when it is split across several runs."""
    nodes = [t for t in el.iter(qn("w:t"))]
    if not nodes:
        return
    for placeholder, value in mapping.items():
        value = "" if value is None else str(value)
        full = "".join(n.text or "" for n in nodes)
        start = full.find(placeholder)
        while start != -1:
            end = start + len(placeholder)
            spans = []
            pos = 0
            for n in nodes:
                s = n.text or ""
                spans.append((pos, pos + len(s)))
                pos += len(s)
            first = True
            for n, (a, b) in zip(nodes, spans):
                if b <= start or a >= end:
                    continue
                s = n.text or ""
                pre = s[: start - a] if a < start else ""
                post = s[end - a :] if b > end else ""
                n.text = pre + (value if first else "") + post
                first = False
            full = "".join(n.text or "" for n in nodes)
            start = full.find(placeholder)


def expand_breaks(el):
    """Turn \\n inside w:t nodes into w:br line breaks."""
    for t in list(el.iter(qn("w:t"))):
        if not t.text or "\n" not in t.text:
            continue
        parts = t.text.split("\n")
        parent = t.getparent()
        idx = list(parent).index(t)
        parent.remove(t)
        for k, part in enumerate(parts):
            if k:
                parent.insert(idx, etree.Element(qn("w:br")))
                idx += 1
            nt = etree.Element(qn("w:t"))
            nt.set(XML_SPACE, "preserve")
            nt.text = part
            parent.insert(idx, nt)
            idx += 1


def clear_runs(el):
    for r in el.findall(qn("w:r")):
        el.remove(r)


def code_paragraphs(source_p, lines):
    ppr = source_p.find(qn("w:pPr"))
    run = source_p.find(qn("w:r"))
    rpr = run.find(qn("w:rPr")) if run is not None else None
    out = []
    for line in lines:
        p = etree.Element(qn("w:p"))
        if ppr is not None:
            p.append(copy.deepcopy(ppr))
        r = etree.SubElement(p, qn("w:r"))
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        t = etree.SubElement(r, qn("w:t"))
        t.set(XML_SPACE, "preserve")
        t.text = line
        out.append(p)
    return out


def image_width(doc, path):
    section = doc.sections[0]
    try:
        content = section.page_width - section.left_margin - section.right_margin
    except TypeError:
        content = Inches(6)
    try:
        native = DocxImage.from_file(str(path)).width
    except Exception:
        native = None
    if not content:
        content = Inches(6)
    return min(native, content) if native else content


def normalize_core_relationship(doc):
    """Fix the malformed core-properties rel type carried by the templates.

    Without it python-docx does not recognize the existing docProps/core.xml
    part, adds a second one and the saved package gets two core.xml entries.
    """
    for rel in list(doc.part.package.rels.values()):
        if rel.reltype != RT.CORE_PROPERTIES and str(rel.reltype).endswith(
            "/metadata/core-properties"
        ):
            rel._reltype = RT.CORE_PROPERTIES


def load_settings():
    if not SETTINGS.is_file():
        if not SETTINGS_EXAMPLE.is_file():
            sys.exit("settings.json and settings.example.json are both missing")
        shutil.copyfile(SETTINGS_EXAMPLE, SETTINGS)
        print("created: " + str(SETTINGS))
    with open(SETTINGS, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError as exc:
            sys.exit("settings.json is not valid JSON: " + str(exc))


def compact_lines(lines):
    """Drop blank-line runs and trailing spaces: fewer tokens per read."""
    out = []
    blank = 0
    for line in lines:
        line = line.rstrip()
        if line:
            blank = 0
            out.append(line)
            continue
        blank += 1
        if blank == 1 and out:
            out.append("")
    while out and not out[-1]:
        out.pop()
    return out


def docx_lines(path):
    doc = Document(str(path))
    lines = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            lines.append(Paragraph(child, doc).text)
        elif child.tag == qn("w:tbl"):
            lines.append("[table]")
            for row in Table(child, doc).rows:
                cells = []
                seen = set()
                for cell in row.cells:
                    if id(cell._tc) in seen:
                        continue
                    seen.add(id(cell._tc))
                    cells.append(" ".join(cell.text.split()))
                lines.append(" | ".join(cells))
    return lines


def pdf_lines(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            sys.exit(
                "PDF needs the pypdf package; run once: "
                "python3 -m pip install -r %s" % REQUIREMENTS
            )
    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:
        sys.exit("cannot read PDF (%s); ask the user for a .docx copy" % exc)
    return "\n\n".join(pages).split("\n")


def text_lines(path):
    return path.read_text(encoding="utf-8", errors="replace").split("\n")


def read_assignment(path, max_chars=0):
    """Print the assignment text and tables in one call: replaces ad-hoc docx probes."""
    if not path.is_file():
        sys.exit("file not found: " + str(path))
    suffix = path.suffix.lower()
    readers = {".docx": docx_lines, ".pdf": pdf_lines, ".txt": text_lines, ".md": text_lines}
    reader = readers.get(suffix)
    if reader is None:
        sys.exit("unsupported assignment format: %s (use .docx, .pdf or .txt)" % suffix)
    lines = compact_lines(reader(path))
    text = "\n".join(lines)
    print("== %s (%d lines)" % (path.name, len(lines)))
    if max_chars and len(text) > max_chars:
        print(text[:max_chars])
        print("... [truncated: %d chars total, rerun with a higher --max-chars]" % len(text))
    else:
        print(text)
    return 0


def report_name(work_type, number):
    kind = str(work_type or "").upper()
    if "ЛАБ" in kind:
        return "ЛР%s.docx" % number
    if "ПРАКТ" in kind:
        return "ПР%s.docx" % number
    return "report_%s.docx" % number


def doctor():
    """One call instead of probing fonts, Graphviz and Python packages."""
    import importlib.util

    def spec(name):
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            return False

    print("python: %s (%s)" % (sys.version.split()[0], sys.executable))
    print("python-docx: ok")
    print("lxml: ok")
    try:
        from PIL import __version__ as pillow_version

        font = make_screenshot._load_font()
        print("Pillow: %s (monospace font: %s)" % (pillow_version, "ok" if font else "missing"))
    except ImportError:
        print("Pillow: missing (text screenshots unavailable)")
    pdf_lib = next((name for name in ("pypdf", "PyPDF2") if spec(name)), None)
    print("pdf reader: %s" % (pdf_lib or "missing (--read .pdf needs pypdf)"))
    print("graphviz dot: %s" % (shutil.which("dot") or "missing"))
    print("matplotlib: %s" % ("ok" if spec("matplotlib") else "missing"))
    for name, path in sorted(TEMPLATES.items()):
        print("template %s: %s" % (name, "ok" if path.is_file() else "MISSING"))
    if SETTINGS.is_file():
        settings = load_settings()
        state = "ok" if str(settings.get("student") or "").strip() else "student empty"
        print("settings: %s (%s)" % (SETTINGS.name, state))
    else:
        print("settings: missing (created by the first build)")
    return 0


def resolve(base_dir, value):
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def task_code(task, base_dir):
    if task.get("code_file"):
        path = resolve(base_dir, task["code_file"])
        if not path.is_file():
            sys.exit("code file not found: " + str(path))
        return path.read_text(encoding="utf-8")
    return task.get("code") or ""


def code_lines(task, base_dir):
    text = task_code(task, base_dir).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.expandtabs(4) for line in text.split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines or [""]


def task_images(task, data_dir, warnings):
    entries = task.get("images") or task.get("screenshots") or []
    jobs = []
    for entry in entries:
        path = resolve(data_dir, entry)
        if not path.is_file():
            warnings.append("WARN: missing image, skipped: " + str(path))
            continue
        kind = "text" if path.suffix.lower() == ".txt" else "image"
        jobs.append((path, kind))
    return jobs


def render_task(block, task, data_dir, warnings):
    els = [copy.deepcopy(e) for e in block]
    replace_placeholders(
        els[0], {"{{N}}": task.get("n", ""), "{{TASK_TEXT}}": task.get("text", "")}
    )
    expand_breaks(els[0])

    code_idx = next(
        (i for i, el in enumerate(els) if "{{CODE}}" in paragraph_text(el)), None
    )
    shot_idx = next(
        i for i, el in enumerate(els) if "{{SCREENSHOT_IMAGE}}" in paragraph_text(el)
    )

    out = [els[0]]
    code_count = 0
    if code_idx is not None:
        out.extend(els[1:code_idx])
        if task.get("code") or task.get("code_file"):
            lines = code_lines(task, data_dir)
            code_count = len(lines)
        else:
            lines = [""]
        out.extend(code_paragraphs(els[code_idx], lines))
        out.extend(els[code_idx + 1 : shot_idx])
    else:
        out.extend(els[1:shot_idx])

    jobs = task_images(task, data_dir, warnings)
    for path, kind in jobs:
        p = copy.deepcopy(els[shot_idx])
        clear_runs(p)
        out.append(p)
    if not jobs:
        p = copy.deepcopy(els[shot_idx])
        clear_runs(p)
        out.append(p)

    image_jobs = []
    for index, (path, kind) in enumerate(jobs):
        p = out[-len(jobs) + index]
        image_jobs.append((p, kind, path))
    return out, image_jobs, code_count


def drop_paragraph(elements, placeholder):
    hits = [i for i, el in enumerate(elements) if placeholder in paragraph_text(el)]
    if len(hits) != 1:
        sys.exit("template: expected exactly one paragraph with " + placeholder)
    del elements[hits[0]]


def strip_strings(line):
    out = []
    i = 0
    quote = None
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def has_comment(line, lang):
    lang = (lang or "").lower()
    stripped = strip_strings(line)
    if lang in C_LIKE:
        return any(m in stripped for m in ("//", "/*", "*/"))
    if lang in HASH_LIKE:
        if lang == "python" and line.strip().startswith(('"""', "'''")):
            return True
        return "#" in stripped
    if lang == "sql":
        return any(m in stripped for m in ("--", "/*", "*/"))
    if lang in PASCAL:
        return any(m in stripped for m in ("//", "{", "(*"))
    if lang in MATLAB:
        return "%" in stripped
    if lang in MARKUP:
        return "<!--" in stripped
    return any(m in stripped for m in ("/*", "*/", "<!--"))


def markdown_hits(text):
    hits = []
    if "**" in text:
        hits.append("**")
    if "`" in text:
        hits.append("`")
    for line in text.split("\n"):
        if re.match(r"\s{0,3}#{1,6}\s", line):
            hits.append("#")
            break
    return hits


def select_template(data):
    if "template" in data:
        name = data["template"]
        if name not in TEMPLATES:
            sys.exit("template must be 'code' or 'nocode'")
        return name
    for task in data.get("tasks") or []:
        if task.get("code") or task.get("code_file"):
            return "code"
    return "nocode"


def build(template_path, template_name, data, data_dir, out_path):
    settings = load_settings()
    student = data["student"] if "student" in data else settings.get("student", "")
    group = data["group"] if "group" in data else settings.get("group", "")
    if not str(student).strip():
        sys.exit("student is empty in settings.json; fill it in first")
    student = str(student).strip()
    group = "" if group is None else str(group).strip()

    doc = Document(str(template_path))
    body = doc.element.body
    children = list(body)
    sect = children[-1] if children and children[-1].tag == qn("w:sectPr") else None
    interior = children[:-1] if sect is not None else children

    def find(pred, name):
        for el in interior:
            if el.tag == qn("w:p") and pred(paragraph_text(el)):
                return el
        sys.exit("template anchor not found: " + name)

    goal = find(lambda t: t.strip().startswith(BODY_START), "Цель работы")
    task0 = find(lambda t: t.startswith("Задание") and "{{N}}" in t, "Задание {{N}}")
    shot = find(lambda t: "{{SCREENSHOT_IMAGE}}" in t, "{{SCREENSHOT_IMAGE}}")
    ctrl = find(lambda t: Q_HEADER in t, Q_HEADER)
    qp = find(lambda t: "{{QUESTION}}" in t, "{{QUESTION}}")
    ap = find(lambda t: "{{ANSWER}}" in t, "{{ANSWER}}")
    order = [interior.index(x) for x in (goal, task0, shot, ctrl, qp, ap)]
    if order != sorted(order):
        sys.exit("unexpected template paragraph order")

    i_task = interior.index(task0)
    head = [copy.deepcopy(e) for e in interior[:i_task]]
    block = interior[i_task : interior.index(shot) + 1]
    mid = interior[interior.index(shot) + 1 : interior.index(ctrl)]
    qpre = interior[interior.index(ctrl) : interior.index(qp)]
    qpost = interior[interior.index(ap) + 1 :]

    variant = data.get("variant", "")
    variant = "" if variant is None else str(variant).strip()
    if variant in ("", "-"):
        drop_paragraph(head, "{{VARIANT}}")
        variant = ""
    if not group:
        drop_paragraph(head, "{{GROUP}}")

    teacher = data.get("teacher")
    teacher = "" if teacher is None else str(teacher).strip()
    teacher_ok = bool(teacher)
    if teacher == "-":
        drop_paragraph(head, "{{TEACHER}}")
        teacher = ""
        teacher_ok = True

    fields = {
        "{{WORK_TYPE}}": data.get("work_type", ""),
        "{{WORK_NUMBER}}": data.get("number", ""),
        "{{SUBJECT}}": data.get("subject", ""),
        "{{VARIANT}}": variant,
        "{{TEACHER}}": teacher,
        "{{GOAL}}": data.get("goal", ""),
        "{{STUDENT}}": student,
        "{{GROUP}}": group,
    }
    for el in head:
        replace_placeholders(el, fields)
        expand_breaks(el)

    warnings = []
    final = list(head)
    images = []
    tasks = data.get("tasks") or []
    if not tasks:
        sys.exit("data.json has no tasks")
    code_total = 0
    for task in tasks:
        els, jobs, count = render_task(block, task, data_dir, warnings)
        final.extend(els)
        images.extend(jobs)
        code_total += count

    questions = data.get("questions") or []
    if questions:
        final.extend(copy.deepcopy(e) for e in mid)
        final.extend(copy.deepcopy(e) for e in qpre)
        for pair in questions:
            q = copy.deepcopy(qp)
            replace_placeholders(q, {"{{QUESTION}}": pair.get("q", "")})
            expand_breaks(q)
            a = copy.deepcopy(ap)
            replace_placeholders(a, {"{{ANSWER}}": pair.get("a", "")})
            expand_breaks(a)
            final.extend([q, a])
        final.extend(copy.deepcopy(e) for e in qpost)

    for el in list(body):
        body.remove(el)
    for el in final:
        body.append(el)
    if sect is not None:
        body.append(sect)

    image_total = 0
    tmpdir = Path(tempfile.mkdtemp(prefix="labshot_"))
    try:
        for index, (p_el, kind, payload) in enumerate(images):
            if kind == "image":
                par = Paragraph(p_el, doc)
                par.add_run().add_picture(str(payload), width=image_width(doc, payload))
                image_total += 1
            else:
                png = tmpdir / ("shot_%d.png" % index)
                try:
                    make_screenshot.render(payload.read_text(encoding="utf-8"), png)
                except RuntimeError as exc:
                    warnings.append("WARN: " + str(exc) + ", image skipped")
                    continue
                par = Paragraph(p_el, doc)
                par.add_run().add_picture(str(png), width=image_width(doc, png))
                image_total += 1

        normalize_core_relationship(doc)
        doc.core_properties.author = student
        doc.core_properties.last_modified_by = student
        doc.core_properties.title = ""
        doc.save(str(out_path))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("saved: " + str(out_path))
    checked = Document(str(out_path))
    problems = build_problems(checked, data, data_dir, warnings)
    for i, task in enumerate(tasks, 1):
        has_code = bool(task.get("code") or task.get("code_file"))
        if template_name == "nocode" and has_code:
            problems.append(
                "task %d has code but the template has no code block" % i
            )
        if template_name == "code" and not has_code:
            warnings.append("WARN: task %d has no code" % i)
    if not teacher_ok:
        problems.append("teacher is empty: ask the user")

    for warning in warnings:
        print(warning)
    if problems:
        print("VIOLATIONS (" + str(len(problems)) + "):")
        for item in problems:
            print("  - " + item)
        return 2
    print(
        "OK (template=%s, tasks=%d, code_lines=%d, images=%d, questions=%d)"
        % (template_name, len(tasks), code_total, image_total, len(questions))
    )
    return 0


def text_fields(data):
    fields = [("goal", data.get("goal", ""))]
    for i, task in enumerate(data.get("tasks") or [], 1):
        fields.append(("task %d" % i, task.get("text", "")))
    for i, pair in enumerate(data.get("questions") or [], 1):
        fields.append(("question %d" % i, pair.get("q", "")))
        fields.append(("answer %d" % i, pair.get("a", "")))
    return fields


def build_problems(doc, data, data_dir, warnings):
    problems = []
    for p in doc.paragraphs:
        if "{{" in p.text:
            problems.append("leftover placeholder: " + p.text.strip()[:80])
    for label, text in text_fields(data):
        hits = markdown_hits(str(text or ""))
        if hits:
            problems.append("markdown in " + label + ": " + ",".join(hits))
    for i, task in enumerate(data.get("tasks") or [], 1):
        if not str(task.get("text") or "").strip():
            problems.append("task %d text is empty" % i)
        lang = (task.get("lang") or "").lower()
        if task.get("code") or task.get("code_file"):
            if lang not in C_LIKE | HASH_LIKE | PASCAL | MATLAB | MARKUP | {"sql"}:
                warnings.append(
                    "WARN: lang not set for task %d, comment check limited" % i
                )
            for line in code_lines(task, data_dir):
                if has_comment(line, lang):
                    problems.append(
                        "comment in code (task %d): %s" % (i, line.strip()[:80])
                    )
    return problems


def iter_code(paras):
    in_code = False
    for p in paras:
        text = p.text.strip()
        if text.startswith(CODE_LABEL):
            in_code = True
            continue
        if text.startswith(SHOT_LABEL) or text.startswith(Q_HEADER):
            in_code = False
            continue
        yield p, in_code


def check(path, dump=False):
    doc = Document(str(path))
    if dump:
        print("TEXT:")
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                print("  " + text)

    problems = []
    for p in doc.paragraphs:
        if "{{" in p.text:
            problems.append("leftover placeholder: " + p.text.strip()[:80])
    for p, in_code in iter_code(doc.paragraphs):
        if in_code:
            if any(m in p.text for m in ("/*", "*/", "<!--")):
                problems.append("comment in code: " + p.text.strip()[:80])
            continue
        if "**" in p.text:
            problems.append("markdown bold: " + p.text.strip()[:80])
        if "`" in p.text:
            problems.append("markdown backtick: " + p.text.strip()[:80])
        for line in p.text.split("\n"):
            if re.match(r"\s{0,3}#{1,6}\s", line):
                problems.append("markdown heading: " + line.strip()[:80])
                break

    if problems:
        print("VIOLATIONS (" + str(len(problems)) + "):")
        for item in problems:
            print("  - " + item)
        return 2
    print("OK")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data", nargs="?", help="input data.json")
    parser.add_argument("out", nargs="?", help="output .docx")
    parser.add_argument("--read", metavar="FILE", help="print an assignment and exit")
    parser.add_argument("--max-chars", type=int, default=0, help="truncate --read output")
    parser.add_argument("--doctor", action="store_true", help="print environment status and exit")
    parser.add_argument("--next-to", metavar="ASSIGNMENT", help="write next to the assignment")
    parser.add_argument("--check", metavar="DOCX", help="check a finished report")
    parser.add_argument("--dump", action="store_true", help="print text dump with --check")
    parser.add_argument("--template", default=None, help="override the template path")
    args = parser.parse_args(argv)

    if args.doctor:
        return doctor()
    if args.read:
        return read_assignment(Path(args.read).expanduser(), args.max_chars)
    if args.check:
        return check(args.check, dump=args.dump)
    if not args.data:
        parser.error("data.json is required (or use --read/--check)")
    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)
    if args.out:
        out = Path(args.out).expanduser()
    elif args.next_to:
        assignment = Path(args.next_to).expanduser()
        out = assignment.resolve().parent / report_name(
            data.get("work_type"), data.get("number")
        )
    else:
        parser.error("out.docx or --next-to is required")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        sys.exit("cannot create output folder (%s); build inside the workspace instead" % exc)
    if args.template:
        template = Path(args.template)
        template_name = "nocode" if "nocode" in str(template) else "code"
    else:
        template_name = select_template(data)
        template = TEMPLATES[template_name]
    if not template.is_file():
        sys.exit("template not found: " + str(template))
    return build(template, template_name, data, Path(args.data).resolve().parent, out)



if __name__ == "__main__":
    sys.exit(main())
