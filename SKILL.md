---
name: lab-solver
description: Solves a lab or practical assignment and fills the report from the template. Use when the user sends a lab or practical task file.
---

# Lab Solver

`SKILL_DIR` = this folder; personal data in `SKILL_DIR/settings.json`.

## Rules
1. Copy tasks word for word, same numbering and order; add nothing of your own. Produce only what the assignment asks for: no code, SQL or anything else it does not request (for a diagram-only work, no SQL schemas and no code in the report).
2. Plain text only: no markdown, no bold, no conclusion, no algorithm description, no comments in code (including code you run).
3. .docx only, checked by the build; never PDF or rendering (PNG screenshots allowed).
4. Strict template match: nothing added, nothing removed; control questions only if the assignment has them.

## Workflow
0. Read `SKILL_DIR/settings.json`; if missing, copy `settings.example.json`. If `list_number` or `student` is empty, ask once for list number, title-page full name and group (optional), write them to settings.json (UTF-8, ensure_ascii=False), and never ask again. Write the report in `report_language`.
1. Read the assignment once: subject, work number, title, teacher, goal, tasks, number of variants K, control questions. Deliverables: programs, scripts or SQL -> `template` `code` (subjects/_default); only diagrams, schemes, models, calculations or text answers -> `nocode` (subjects/_nocode); mixed -> `code`. Set it in data.json.
2. Ask in ONE message everything missing: list number, student and group on first run; the teacher; the diagram notation or tool. Never build with an empty teacher or invent one.
3. Variant: follow the assignment's own rule; else variant = ((list_number - 1) mod K) + 1. State it and how it was computed. No variants: all tasks, `variant` empty.
4. Solve: write each solution to a code file, run it once with `> out.txt 2>&1`, set `lang`, reference `code_file` and `images:["out.txt"]`. Teacher: read it from the assignment (title block, header, signature, file name, text); if absent, ask the user. Diagrams: use the notation, elements, naming and tool the assignment (or materials) specifies; if none, use `diagram_notation` from settings.json when set, else ask once. Draw each as a PNG (Graphviz `dot` if installed, else matplotlib, installed with pip if needed; if neither works, stop and report), readable text in the report language, width fitting the page, no tool code or diagram source in the report. Put PNG paths into the task's `images`. Use `python3` with absolute `SKILL_DIR/scripts/...` paths. If an import fails, run `python3 -m pip install -r SKILL_DIR/requirements.txt` once, else stop.
5. Build: `python3 SKILL_DIR/scripts/build_report.py data.json OUT.docx`; it checks itself. On VIOLATIONS fix the input and rebuild once; do not run `--check` separately. Name it next to the assignment `ЛР<number>.docx` (lab), `ПР<number>.docx` (practical), else `report_<number>.docx`. Delete temp files (data.json, code files, out.txt, PNGs, diagram sources).
6. Reply: subject and work, template (code/nocode), variant and computation, path, open [FILL IN] items. No retelling.

## data.json
{
 "work_type":"ЛАБОРАТОРНОЙ","number":"4","subject":"...","variant":"5","teacher":"...","goal":"...","template":"code",
 "tasks":[{"n":1,"text":"...","lang":"cpp","code":"..." OR "code_file":"sol.cpp","images":["out.txt","scheme.png"]}],
 "questions":[{"q":"...","a":"..."}]
}
`template` optional (auto by code). `images` alias `screenshots`. Nocode: omit `code`/`code_file`.
Student/group from settings.json (data.json override only if asked). If Pillow cannot render, leave `images` empty and say so.
NEVER open, unzip or dump the template XML/footer; the script handles it.
One pass: each step once; do not re-read files without need.
