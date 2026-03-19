"""
GUI для транслятора JavaScript → R
Лабораторные работы 1-4

Запуск:
    python gui.py
Затем открыть в браузере: http://localhost:5000
"""

import os, sys, json, traceback
from flask import Flask, render_template_string, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))

def _run_lab1(source: str) -> dict:
    from lexer import LexicalAnalyzer
    lex = LexicalAnalyzer()
    tokens = lex.analyze(source)
    # Сохраняем файлы
    os.chdir(BASE)
    from main import save_tables
    save_tables(lex, source)
    return {
        'tokens': [{'tc': t.token_class, 'code': t.code, 'value': t.value} for t in tokens],
        'id_table': [{'code': r.code, 'name': r.name, 'level': r.nesting_level, 'type': r.id_type}
                     for r in lex.id_records],
        'num_table': [{'code': v[0], 'value': k, 'type': v[1]}
                      for k, v in sorted(lex.num_table.items(), key=lambda x: x[1][0])],
        'str_table': [{'code': v[0], 'value': k, 'type': v[1]}
                      for k, v in sorted(lex.str_table.items(), key=lambda x: x[1][0])],
        'errors': lex.errors,
        'tokens_txt': '\n'.join(
            lex.get_line_repr(line_toks)
            for line_toks in lex.tokens_by_line
            if lex.get_line_repr(line_toks)
        ),
    }

def _run_lab2() -> dict:
    from load_tables import load_lab1_results
    from rpn import RpnTranslator, format_rpn
    tokens = load_lab1_results(prefix=os.path.join(BASE, 'output'))
    t = RpnTranslator()
    elems = t.translate(tokens)
    rpn_str = format_rpn(elems)
    # Сохраняем
    from main2 import save_rpn
    os.chdir(BASE)
    save_rpn(elems, prefix=os.path.join(BASE, 'output2'))
    return {
        'elements': [{'kind': e.kind, 'value': e.display()} for e in elems],
        'rpn_string': rpn_str,
        'trace': t.trace,
    }

def _run_lab3() -> dict:
    from codegen import CodeGenerator, load_rpn, format_r_code_clean, save_r_code
    rpn_path = os.path.join(BASE, 'output2_rpn.txt')
    elems = load_rpn(rpn_path)
    gen = CodeGenerator()
    lines = gen.generate(elems)
    os.chdir(BASE)
    save_r_code(lines, gen.label_table, prefix=os.path.join(BASE, 'output3'))
    return {
        'code_lines': [{'num': l.num, 'text': l.text, 'indent': l.indent} for l in lines],
        'label_table': gen.label_table,
        'P': gen.P,
        'trace': gen.trace,
    }

def _run_lab4() -> dict:
    from parser4 import run_parser
    return run_parser(prefix=os.path.join(BASE, 'output'))


# ── маршруты ─────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/lab1', methods=['POST'])
def api_lab1():
    src = request.json.get('source', '')
    try:
        return jsonify({'ok': True, 'data': _run_lab1(src)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()})

@app.route('/api/lab2', methods=['POST'])
def api_lab2():
    try:
        return jsonify({'ok': True, 'data': _run_lab2()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()})

@app.route('/api/lab3', methods=['POST'])
def api_lab3():
    try:
        return jsonify({'ok': True, 'data': _run_lab3()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()})

@app.route('/api/lab4', methods=['POST'])
def api_lab4():
    try:
        return jsonify({'ok': True, 'data': _run_lab4()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'trace': traceback.format_exc()})


# ── HTML шаблон ───────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Транслятор JS → R | Вариант 10</title>
<style>
:root {
  --bg: #ffffff; --bg2: #f7f7f5; --bg3: #f0ede8;
  --border: rgba(0,0,0,0.12); --border2: rgba(0,0,0,0.22);
  --text: #1a1a1a; --text2: #666; --text3: #999;
  --blue: #185FA5; --blue-bg: #E6F1FB; --blue-text: #0C447C;
  --teal: #0F6E56; --teal-bg: #E1F5EE; --teal-text: #085041;
  --purple: #534AB7; --purple-bg: #EEEDFE; --purple-text: #3C3489;
  --green: #3B6D11; --green-bg: #EAF3DE; --green-text: #27500A;
  --amber: #854F0B; --amber-bg: #FAEEDA; --amber-text: #633806;
  --red: #A32D2D; --red-bg: #FCEBEB; --red-text: #791F1F;
  --coral: #993C1D; --coral-bg: #FAECE7; --coral-text: #4A1B0C;
  --gray: #5F5E5A; --gray-bg: #F1EFE8; --gray-text: #444441;
  --radius: 8px; --radius-lg: 12px; --mono: 'Courier New', monospace;
  --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1c1a; --bg2: #252523; --bg3: #2e2e2b;
    --border: rgba(255,255,255,0.1); --border2: rgba(255,255,255,0.2);
    --text: #e8e6e1; --text2: #a09e99; --text3: #666;
    --blue-bg: #0c2d4a; --blue-text: #85B7EB;
    --teal-bg: #042e23; --teal-text: #5DCAA5;
    --purple-bg: #1e1a4a; --purple-text: #AFA9EC;
    --green-bg: #152607; --green-text: #97C459;
    --amber-bg: #2a1e05; --amber-text: #EF9F27;
    --red-bg: #2a0e0e; --red-text: #F09595;
    --coral-bg: #2a1208; --coral-text: #F0997B;
    --gray-bg: #2a2a27; --gray-text: #B4B2A9;
  }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--sans); background: var(--bg3); color: var(--text); font-size: 14px; line-height: 1.5; }

/* ── Header ── */
.header { background: var(--bg); border-bottom: 0.5px solid var(--border); padding: 0 24px; display: flex; align-items: center; gap: 16px; height: 52px; position: sticky; top: 0; z-index: 100; }
.logo { font-size: 15px; font-weight: 600; color: var(--text); }
.logo span { color: var(--blue); }
.header-sub { font-size: 12px; color: var(--text3); }

/* ── Layout ── */
.layout { display: grid; grid-template-columns: 220px 1fr; min-height: calc(100vh - 52px); }
.sidebar { background: var(--bg); border-right: 0.5px solid var(--border); padding: 16px 0; position: sticky; top: 52px; height: calc(100vh - 52px); overflow-y: auto; }
.main { padding: 20px 24px; max-width: 1100px; }

/* ── Sidebar nav ── */
.nav-section { padding: 4px 16px 8px; font-size: 11px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: .05em; margin-top: 8px; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 8px 16px; cursor: pointer; transition: background .12s; border-left: 2px solid transparent; }
.nav-item:hover { background: var(--bg2); }
.nav-item.active { background: var(--blue-bg); border-left-color: var(--blue); }
.nav-item.active .nav-label { color: var(--blue-text); font-weight: 500; }
.nav-badge { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; flex-shrink: 0; }
.nb1 { background: var(--blue-bg); color: var(--blue-text); }
.nb2 { background: var(--teal-bg); color: var(--teal-text); }
.nb3 { background: var(--purple-bg); color: var(--purple-text); }
.nb4 { background: var(--green-bg); color: var(--green-text); }
.nav-label { font-size: 13px; color: var(--text2); }
.nav-status { width: 6px; height: 6px; border-radius: 50%; background: var(--border2); margin-left: auto; }
.nav-status.done { background: #1D9E75; }
.nav-status.error { background: var(--red); }

/* ── Cards ── */
.card { background: var(--bg); border: 0.5px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 16px; }
.card-header { padding: 12px 16px; border-bottom: 0.5px solid var(--border); background: var(--bg2); display: flex; align-items: center; gap: 10px; }
.badge { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px; flex-shrink: 0; }
.b1 { background: var(--blue-bg); color: var(--blue-text); }
.b2 { background: var(--teal-bg); color: var(--teal-text); }
.b3 { background: var(--purple-bg); color: var(--purple-text); }
.b4 { background: var(--green-bg); color: var(--green-text); }
.berr { background: var(--red-bg); color: var(--red-text); }
.bok { background: var(--teal-bg); color: var(--teal-text); }
.card-title { font-size: 14px; font-weight: 500; }
.card-sub { font-size: 12px; color: var(--text3); margin-left: auto; }
.card-body { padding: 14px 16px; }

/* ── Tabs ── */
.tabs { display: flex; gap: 3px; padding: 8px 12px; border-bottom: 0.5px solid var(--border); background: var(--bg2); overflow-x: auto; }
.tab { padding: 4px 10px; font-size: 12px; font-weight: 500; border-radius: var(--radius); cursor: pointer; color: var(--text2); background: transparent; border: 0.5px solid transparent; white-space: nowrap; transition: all .1s; }
.tab:hover { background: var(--bg); color: var(--text); }
.tab.active { background: var(--bg); color: var(--text); border-color: var(--border2); }

/* ── Stats row ── */
.stats { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.stat { background: var(--bg2); border-radius: var(--radius); padding: 8px 12px; flex: 1; min-width: 80px; }
.stat-val { font-size: 20px; font-weight: 600; color: var(--text); }
.stat-lbl { font-size: 11px; color: var(--text2); margin-top: 2px; }

/* ── Code blocks ── */
.code { font-family: var(--mono); font-size: 12px; background: var(--bg2); border: 0.5px solid var(--border); border-radius: var(--radius); padding: 10px 12px; overflow-x: auto; line-height: 1.7; white-space: pre; max-height: 280px; overflow-y: auto; }
.code-line { display: flex; gap: 8px; }
.ln { color: var(--text3); min-width: 24px; text-align: right; user-select: none; font-size: 11px; }
.cmt { color: var(--green-text); }
.kw  { color: var(--purple-text); }
.asgn { color: var(--amber-text); }
.str  { color: var(--coral-text); }
.err-line { background: var(--red-bg); }

/* ── Token chips ── */
.chip-grid { display: flex; flex-wrap: wrap; gap: 4px; max-height: 200px; overflow-y: auto; }
.chip { font-family: var(--mono); font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 500; white-space: nowrap; }
.tW { background: var(--purple-bg); color: var(--purple-text); }
.tI { background: var(--teal-bg); color: var(--teal-text); }
.tO { background: var(--amber-bg); color: var(--amber-text); }
.tR { background: var(--gray-bg); color: var(--gray-text); }
.tN { background: var(--blue-bg); color: var(--blue-text); }
.tC { background: var(--coral-bg); color: var(--coral-text); }

/* ── RPN chips ── */
.rpn-wrap { display: flex; flex-wrap: wrap; gap: 4px; max-height: 200px; overflow-y: auto; }
.rpn { font-family: var(--mono); font-size: 11px; padding: 2px 7px; border-radius: 20px; font-weight: 500; border: 0.5px solid transparent; }
.rp-op     { background: var(--blue-bg);   color: var(--blue-text);   border-color: #B5D4F4; }
.rp-ar     { background: var(--amber-bg);  color: var(--amber-text);  border-color: #FAC775; }
.rp-as     { background: var(--purple-bg); color: var(--purple-text); border-color: #CECBF6; }
.rp-ct     { background: var(--coral-bg);  color: var(--coral-text);  border-color: #F5C4B3; }
.rp-np     { background: var(--green-bg);  color: var(--green-text);  border-color: #C0DD97; }
.rp-dc     { background: var(--gray-bg);   color: var(--gray-text);   border-color: #D3D1C7; }
.rp-lb     { background: var(--red-bg);    color: var(--red-text);    border-color: #F7C1C1; }
.rp-fn     { background: var(--teal-bg);   color: var(--teal-text);   border-color: #9FE1CB; }

/* ── Table ── */
.tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
.tbl th { background: var(--bg2); padding: 6px 10px; text-align: left; font-weight: 500; border-bottom: 0.5px solid var(--border); color: var(--text2); }
.tbl td { padding: 4px 10px; border-bottom: 0.5px solid var(--border); font-family: var(--mono); color: var(--text); }
.tbl tr:last-child td { border-bottom: none; }
.tbl tr:hover td { background: var(--bg2); }
.tbl-wrap { overflow-x: auto; }

/* ── Buttons ── */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; border-radius: var(--radius); border: 0.5px solid var(--border2); background: var(--bg); color: var(--text); cursor: pointer; transition: all .12s; }
.btn:hover { background: var(--bg2); }
.btn-primary { background: var(--blue); color: #fff; border-color: var(--blue); }
.btn-primary:hover { background: var(--blue-text); }
.btn-sm { padding: 5px 12px; font-size: 12px; }
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }

/* ── Editor ── */
textarea { font-family: var(--mono); font-size: 12px; resize: vertical; background: var(--bg2); color: var(--text); border: 0.5px solid var(--border); border-radius: var(--radius); padding: 10px 12px; line-height: 1.6; width: 100%; }
textarea:focus { outline: none; border-color: var(--blue); }

/* ── Pipeline ── */
.pipeline { display: flex; align-items: center; gap: 0; background: var(--bg); border: 0.5px solid var(--border); border-radius: var(--radius-lg); padding: 12px 16px; overflow-x: auto; margin-bottom: 16px; }
.pipe-step { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 8px 14px; border-radius: var(--radius); cursor: pointer; min-width: 90px; border: 1.5px solid transparent; transition: all .12s; }
.pipe-step:hover { background: var(--bg2); }
.pipe-step.active { background: var(--blue-bg); border-color: var(--blue); }
.pipe-step.done { background: var(--teal-bg); }
.pipe-step.has-error { background: var(--red-bg); }
.ps-num { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; }
.ps1 .ps-num { background: var(--blue-bg); color: var(--blue-text); }
.ps2 .ps-num { background: var(--teal-bg); color: var(--teal-text); }
.ps3 .ps-num { background: var(--purple-bg); color: var(--purple-text); }
.ps4 .ps-num { background: var(--green-bg); color: var(--green-text); }
.pipe-step.done .ps-num { background: #1D9E75; color: #fff; }
.pipe-step.has-error .ps-num { background: var(--red); color: #fff; }
.ps-title { font-size: 12px; font-weight: 500; color: var(--text); }
.ps-sub { font-size: 11px; color: var(--text2); }
.pipe-arrow { color: var(--text3); font-size: 18px; padding: 0 4px; }

/* ── Tree ── */
.tree { font-family: var(--mono); font-size: 12px; max-height: 320px; overflow-y: auto; background: var(--bg2); border: 0.5px solid var(--border); border-radius: var(--radius); padding: 10px 12px; }
.tree-node { margin-left: 16px; }
.tree-label { color: var(--blue-text); }
.tree-token { color: var(--text3); font-size: 10px; margin-left: 4px; }
.tree-leaf { color: var(--teal-text); }

/* ── Section label ── */
.sec { font-size: 11px; font-weight: 600; color: var(--text2); text-transform: uppercase; letter-spacing: .04em; margin: 12px 0 6px; }
.sec:first-child { margin-top: 0; }

/* ── Spinner ── */
.spin { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--blue); border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Alert ── */
.alert { padding: 10px 14px; border-radius: var(--radius); font-size: 12px; margin-bottom: 10px; }
.alert-ok  { background: var(--teal-bg); color: var(--teal-text); border: 0.5px solid var(--teal); }
.alert-err { background: var(--red-bg); color: var(--red-text); border: 0.5px solid var(--red); }

/* ── Notice ── */
.notice { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 40px; color: var(--text2); text-align: center; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">JS<span>→</span>R Translator</div>
  <div class="header-sub">Вариант 10 · Лабораторные работы 1–4</div>
  <div style="margin-left:auto;display:flex;gap:8px;align-items:center">
    <span id="chain-status" style="font-size:12px;color:var(--text3)">Загрузите JS и запустите Лабу 1</span>
    <button class="btn btn-primary btn-sm" onclick="runAll()">▶ Запустить всё</button>
  </div>
</div>

<div class="layout">

<!-- Sidebar -->
<div class="sidebar">
  <div class="nav-section">Цепочка трансляции</div>

  <div class="nav-item ps1 active" onclick="showLab(1)">
    <div class="nav-badge nb1">1</div>
    <div>
      <div class="nav-label">Лаба 1 — Лексер</div>
      <div style="font-size:11px;color:var(--text3)">JS → токены</div>
    </div>
    <div class="nav-status" id="ns1"></div>
  </div>
  <div class="nav-item ps2" onclick="showLab(2)">
    <div class="nav-badge nb2">2</div>
    <div>
      <div class="nav-label">Лаба 2 — ОПЗ</div>
      <div style="font-size:11px;color:var(--text3)">Токены → ОПЗ</div>
    </div>
    <div class="nav-status" id="ns2"></div>
  </div>
  <div class="nav-item ps3" onclick="showLab(3)">
    <div class="nav-badge nb3">3</div>
    <div>
      <div class="nav-label">Лаба 3 — Код R</div>
      <div style="font-size:11px;color:var(--text3)">ОПЗ → R</div>
    </div>
    <div class="nav-status" id="ns4"></div>
  </div>
  <div class="nav-item ps4" onclick="showLab(4)">
    <div class="nav-badge nb4">4</div>
    <div>
      <div class="nav-label">Лаба 4 — Синтаксис</div>
      <div style="font-size:11px;color:var(--text3)">Дерево разбора</div>
    </div>
    <div class="nav-status" id="ns3"></div>
  </div>

  <div class="nav-section" style="margin-top:16px">Файлы</div>
  <div style="padding:8px 16px;font-size:11px;color:var(--text3);line-height:1.7">
    output_tokens.txt<br>
    output_I_identifiers.txt<br>
    output_N_numbers.txt<br>
    output_C_strings.txt<br>
    output2_rpn.txt<br>
    output3_r.R
  </div>
</div>

<!-- Main content -->
<div class="main" id="main-content">

<!-- Pipeline -->
<div class="pipeline">
  <div class="pipe-step ps1 active" id="pip1" onclick="showLab(1)">
    <div class="ps-num">1</div>
    <div class="ps-title">Лаба 1</div>
    <div class="ps-sub">Лексер</div>
  </div>
  <div class="pipe-arrow">›</div>
  <div class="pipe-step ps2" id="pip2" onclick="showLab(2)">
    <div class="ps-num">2</div>
    <div class="ps-title">Лаба 2</div>
    <div class="ps-sub">ОПЗ</div>
  </div>
  <div class="pipe-arrow">›</div>
  <div class="pipe-step ps3" id="pip3" onclick="showLab(3)">
    <div class="ps-num">3</div>
    <div class="ps-title">Лаба 3</div>
    <div class="ps-sub">Код R</div>
  </div>
  <div class="pipe-arrow">›</div>
  <div class="pipe-step ps4" id="pip4" onclick="showLab(4)">
    <div class="ps-num">4</div>
    <div class="ps-title">Лаба 4</div>
    <div class="ps-sub">Синтаксис</div>
  </div>
</div>

<!-- Lab panels -->
<div id="lab1-panel">
  <div class="card">
    <div class="card-header">
      <span class="badge b1">Лаба 1</span>
      <span class="card-title">Лексический анализатор</span>
      <span class="card-sub">JavaScript → токены</span>
    </div>
    <div class="card-body">
      <div class="btn-row">
        <button class="btn btn-primary" onclick="runLab1()"><span id="l1-spin" style="display:none" class="spin"></span> ▶ Запустить анализ</button>
        <button class="btn btn-sm" onclick="loadExample()">Загрузить пример</button>
        <span id="l1-status" style="font-size:12px;color:var(--text3)"></span>
      </div>
      <div class="sec">Исходный код JavaScript</div>
      <textarea id="js-input" rows="14" placeholder="Введите JavaScript код..."></textarea>
    </div>
  </div>
  <div class="card" id="l1-result" style="display:none">
    <div class="tabs" id="l1-tabs">
      <div class="tab active" onclick="l1tab(0)">Токены</div>
      <div class="tab" onclick="l1tab(1)">Таблица I</div>
      <div class="tab" onclick="l1tab(2)">Таблица N</div>
      <div class="tab" onclick="l1tab(3)">Таблица C</div>
      <div class="tab" onclick="l1tab(4)">output_tokens.txt</div>
    </div>
    <div class="card-body" id="l1-body"></div>
  </div>
</div>

<div id="lab2-panel" style="display:none">
  <div class="card">
    <div class="card-header">
      <span class="badge b2">Лаба 2</span>
      <span class="card-title">Перевод в ОПЗ</span>
      <span class="card-sub">Алгоритм Дейкстры</span>
    </div>
    <div class="card-body">
      <div class="btn-row">
        <button class="btn btn-primary" onclick="runLab2()"><span id="l2-spin" style="display:none" class="spin"></span> ▶ Построить ОПЗ</button>
        <span id="l2-status" style="font-size:12px;color:var(--text3)">Необходимо сначала запустить Лабу 1</span>
      </div>
    </div>
  </div>
  <div class="card" id="l2-result" style="display:none">
    <div class="tabs">
      <div class="tab active" onclick="l2tab(0)">Элементы ОПЗ</div>
      <div class="tab" onclick="l2tab(1)">Строка ОПЗ</div>
      <div class="tab" onclick="l2tab(2)">Трассировка стека</div>
      <div class="tab" onclick="l2tab(3)">Таблица приоритетов</div>
    </div>
    <div class="card-body" id="l2-body"></div>
  </div>
</div>

<div id="lab3-panel" style="display:none">
  <div class="card">
    <div class="card-header">
      <span class="badge b3">Лаба 3</span>
      <span class="card-title">Генерация кода R</span>
      <span class="card-sub">МП-автомат</span>
    </div>
    <div class="card-body">
      <div class="btn-row">
        <button class="btn btn-primary" onclick="runLab3()"><span id="l3-spin" style="display:none" class="spin"></span> ▶ Генерировать R</button>
        <span id="l3-status" style="font-size:12px;color:var(--text3)">Необходимо сначала запустить Лабу 2</span>
      </div>
    </div>
  </div>
  <div class="card" id="l3-result" style="display:none">
    <div class="tabs">
      <div class="tab active" onclick="l3tab(0)">Код R</div>
      <div class="tab" onclick="l3tab(1)">Трассировка МП</div>
      <div class="tab" onclick="l3tab(2)">Таблица меток</div>
    </div>
    <div class="card-body" id="l3-body"></div>
  </div>
</div>

<div id="lab4-panel" style="display:none">
  <div class="card">
    <div class="card-header">
      <span class="badge b4">Лаба 4</span>
      <span class="card-title">Синтаксический анализатор</span>
      <span class="card-sub">Рекурсивный спуск</span>
    </div>
    <div class="card-body">
      <div class="btn-row">
        <button class="btn btn-primary" onclick="runLab4()"><span id="l4-spin" style="display:none" class="spin"></span> ▶ Анализировать</button>
        <span id="l4-status" style="font-size:12px;color:var(--text3)">Необходимо сначала запустить Лабу 1</span>
      </div>
    </div>
  </div>
  <div class="card" id="l4-result" style="display:none">
    <div class="tabs">
      <div class="tab active" onclick="l4tab(0)">Дерево разбора</div>
      <div class="tab" onclick="l4tab(1)">Шаги анализа</div>
      <div class="tab" onclick="l4tab(2)">Грамматика</div>
    </div>
    <div class="card-body" id="l4-body"></div>
  </div>
</div>

</div><!-- /main -->
</div><!-- /layout -->

<script>
const JS_EXAMPLE = `var a1;\nvar a2;\na1 = 15;\na2 = 4;\nvar x;\nx = 123.45;\nvar str;\nstr = "Привет мир";\nvar sum;\nsum = a1 + a2;\nif (a1 > a2) {\n    sum = a1 + a2;\n} else {\n    sum = a2;\n}\nfunction square(x) {\n    var r;\n    r = x * x;\n    return r;\n}\nvar arr;\narr[0] = 42;\narr[a1 + 1] = 100;`;

const PRIO_TABLE = [
  ['if, (, [, Ф, АЭМ','0','Открывающие — не выталкиваются'],
  [';, ), ]','1','Закрывающие'],
  ['= (присваивание)','2','Правоассоциативное'],
  ['==, !=, <, >, <=, >=','3','Операции сравнения'],
  ['+, -','4','Аддитивные'],
  ['*, /, %','5','Мультипликативные'],
  ['^','6','Возведение в степень'],
  ['function, var, return, :','7','Описательные (наибольший)'],
];

const GRAMMAR = [
  ['&lt;программа&gt;', '::= &lt;текст&gt;'],
  ['&lt;текст&gt;', '::= { &lt;элемент&gt; }'],
  ['&lt;элемент&gt;', '::= &lt;описание&gt; | &lt;функция&gt; | &lt;условный&gt; | &lt;while&gt; | &lt;for&gt; | &lt;return&gt; | &lt;оператор&gt;'],
  ['&lt;описание&gt;', '::= var &lt;идент&gt; { , &lt;идент&gt; } ;'],
  ['&lt;функция&gt;', '::= function &lt;идент&gt; ( &lt;парамы&gt; ) { &lt;текст&gt; }'],
  ['&lt;оператор&gt;', '::= &lt;идент&gt; = &lt;выражение&gt; ; | &lt;идент&gt; [ &lt;выраж&gt; ] = &lt;выражение&gt; ;'],
  ['&lt;условный&gt;', '::= if ( &lt;условие&gt; ) { &lt;текст&gt; } [ else { &lt;текст&gt; } ]'],
  ['&lt;while&gt;', '::= while ( &lt;условие&gt; ) { &lt;текст&gt; }'],
  ['&lt;условие&gt;', '::= &lt;выражение&gt; &lt;опер_сравн&gt; &lt;выражение&gt;'],
  ['&lt;выражение&gt;', '::= &lt;терм&gt; { (+|-) &lt;терм&gt; }'],
  ['&lt;терм&gt;', '::= &lt;множитель&gt; { (*|/|%) &lt;множитель&gt; }'],
  ['&lt;множитель&gt;', '::= &lt;аргумент&gt; | ( &lt;выражение&gt; )'],
  ['&lt;аргумент&gt;', '::= &lt;идент&gt; [ (...) | [...] ] | &lt;константа&gt;'],
  ['&lt;константа&gt;', '::= N | C | true | false | null'],
  ['&lt;опер_сравн&gt;', '::= &lt; | &gt; | == | != | &lt;= | &gt;='],
];

// Сохранённые данные
let D = { lab1: null, lab2: null, lab3: null, lab4: null };
let curLab = 1;
let l1tab_idx = 0, l2tab_idx = 0, l3tab_idx = 0, l4tab_idx = 0;

function e(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function showLab(n) {
  curLab = n;
  [1,2,3,4].forEach(i => {
    document.getElementById('lab'+i+'-panel').style.display = i===n ? '' : 'none';
    document.querySelectorAll('.nav-item')[i-1].classList.toggle('active', i===n);
    document.getElementById('pip'+i).classList.toggle('active', i===n);
  });
}

function loadExample() {
  document.getElementById('js-input').value = JS_EXAMPLE;
}

function setStatus(id, msg, ok) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.style.color = ok === true ? '#0F6E56' : ok === false ? '#A32D2D' : 'var(--text3)';
}

function spin(id, show) {
  const el = document.getElementById(id);
  if (el) el.style.display = show ? 'inline-block' : 'none';
}

async function runLab1() {
  const src = document.getElementById('js-input').value.trim();
  if (!src) { setStatus('l1-status', 'Введите код JS', false); return; }
  spin('l1-spin', true);
  setStatus('l1-status', 'Анализирую...', null);
  try {
    const r = await fetch('/api/lab1', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({source: src})});
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    D.lab1 = j.data;
    document.getElementById('l1-result').style.display = '';
    renderL1(0);
    setStatus('l1-status', `✓ ${D.lab1.tokens.length} токенов`, true);
    document.getElementById('ns1').className = 'nav-status done';
    document.getElementById('pip1').className = 'pipe-step ps1 done';
    setStatus('l2-status', 'Лаба 1 готова — можно запускать');
    setStatus('l4-status', 'Лаба 1 готова — можно запускать');
  } catch(ex) {
    setStatus('l1-status', '✗ ' + ex.message, false);
    document.getElementById('ns1').className = 'nav-status error';
  }
  spin('l1-spin', false);
}

async function runLab2() {
  if (!D.lab1) { setStatus('l2-status', 'Сначала запустите Лабу 1', false); return; }
  spin('l2-spin', true);
  setStatus('l2-status', 'Строю ОПЗ...', null);
  try {
    const r = await fetch('/api/lab2', {method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'});
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    D.lab2 = j.data;
    document.getElementById('l2-result').style.display = '';
    renderL2(0);
    setStatus('l2-status', `✓ ${D.lab2.elements.length} элементов ОПЗ`, true);
    document.getElementById('ns2').className = 'nav-status done';
    document.getElementById('pip2').className = 'pipe-step ps2 done';
    setStatus('l3-status', 'Лаба 2 готова — можно запускать');
  } catch(ex) {
    setStatus('l2-status', '✗ ' + ex.message, false);
  }
  spin('l2-spin', false);
}

async function runLab3() {
  if (!D.lab2) { setStatus('l3-status', 'Сначала запустите Лабу 2', false); return; }
  spin('l3-spin', true);
  setStatus('l3-status', 'Генерирую код R...', null);
  try {
    const r = await fetch('/api/lab3', {method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'});
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    D.lab3 = j.data;
    document.getElementById('l3-result').style.display = '';
    renderL3(0);
    setStatus('l3-status', `✓ ${D.lab3.code_lines.length} строк R`, true);
    document.getElementById('ns4').className = 'nav-status done';
    document.getElementById('pip3').className = 'pipe-step ps3 done';
  } catch(ex) {
    setStatus('l3-status', '✗ ' + ex.message, false);
  }
  spin('l3-spin', false);
}

async function runLab4() {
  if (!D.lab1) { setStatus('l4-status', 'Сначала запустите Лабу 1', false); return; }
  spin('l4-spin', true);
  setStatus('l4-status', 'Анализирую синтаксис...', null);
  try {
    const r = await fetch('/api/lab4', {method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'});
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    D.lab4 = j.data;
    document.getElementById('l4-result').style.display = '';
    renderL4(0);
    if (D.lab4.ok) {
      setStatus('l4-status', `✓ Синтаксически верно · ${D.lab4.steps.length} шагов`, true);
      document.getElementById('ns3').className = 'nav-status done';
      document.getElementById('pip4').className = 'pipe-step ps4 done';
    } else {
      setStatus('l4-status', `✗ ${D.lab4.errors.length} ошибок`, false);
      document.getElementById('ns3').className = 'nav-status error';
      document.getElementById('pip4').className = 'pipe-step ps4 has-error';
    }
  } catch(ex) {
    setStatus('l4-status', '✗ ' + ex.message, false);
  }
  spin('l4-spin', false);
}

async function runAll() {
  loadExample();
  document.getElementById('chain-status').textContent = 'Запускаю цепочку...';
  await runLab1(); if (!D.lab1) return;
  showLab(2); await runLab2(); if (!D.lab2) return;
  showLab(3); await runLab3();
  showLab(4); await runLab4();
  document.getElementById('chain-status').textContent = '✓ Все 4 лабы завершены';
}

// ── Рендеры Лаба 1 ──
function l1tab(i) {
  l1tab_idx = i;
  document.querySelectorAll('#l1-tabs .tab').forEach((t,j)=>t.classList.toggle('active',j===i));
  renderL1(i);
}

function renderL1(tab) {
  if (!D.lab1) return;
  const d = D.lab1;
  const el = document.getElementById('l1-body');
  if (tab === 0) {
    const chips = d.tokens.map(t => `<span class="chip t${t.tc}" title="${e(t.tc+t.code+': '+t.value)}">${e(t.tc+t.code)}</span>`).join('');
    const legend = ['W','I','O','R','N','C'].map(c=>`<span class="chip t${c}">${c}</span>`).join(' ');
    el.innerHTML = `
      <div class="stats">
        <div class="stat"><div class="stat-val">${d.tokens.length}</div><div class="stat-lbl">токенов</div></div>
        <div class="stat"><div class="stat-val">${d.id_table.length}</div><div class="stat-lbl">идентиф.</div></div>
        <div class="stat"><div class="stat-val">${d.num_table.length}</div><div class="stat-lbl">числ.конст.</div></div>
        <div class="stat"><div class="stat-val">${d.str_table.length}</div><div class="stat-lbl">стр.конст.</div></div>
      </div>
      <div class="sec">Поток токенов (→ вход для Лабы 2)</div>
      <div class="chip-grid">${chips}</div>
      <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;font-size:11px">
        <span style="color:var(--text2)">W ключевые</span>
        <span style="color:var(--text2)">I идентиф.</span>
        <span style="color:var(--text2)">O операции</span>
        <span style="color:var(--text2)">R разделит.</span>
        <span style="color:var(--text2)">N числа</span>
        <span style="color:var(--text2)">C строки</span>
      </div>
      ${d.errors.length ? `<div class="alert alert-err" style="margin-top:10px">Ошибки: ${d.errors.join('; ')}</div>` : ''}`;
  } else if (tab === 1) {
    const rows = d.id_table.map(r=>`<tr><td>${r.code}</td><td>${e(r.name)}</td><td>${r.level}</td><td>${e(r.type)}</td></tr>`).join('');
    el.innerHTML = `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Код</th><th>Имя</th><th>Ур.вл.</th><th>Тип</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  } else if (tab === 2) {
    const rows = d.num_table.map(r=>`<tr><td>${r.code}</td><td>${e(r.value)}</td><td>${e(r.type)}</td></tr>`).join('');
    el.innerHTML = `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Код</th><th>Значение</th><th>Тип</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  } else if (tab === 3) {
    const rows = d.str_table.map(r=>`<tr><td>${r.code}</td><td>${e(r.value)}</td><td>${e(r.type)}</td></tr>`).join('');
    el.innerHTML = `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Код</th><th>Значение</th><th>Тип</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  } else if (tab === 4) {
    el.innerHTML = `<div class="sec">output_tokens.txt</div><div class="code">${e(d.tokens_txt)}</div>`;
  }
}

// ── Рендеры Лаба 2 ──
function l2tab(i) {
  l2tab_idx = i;
  document.querySelectorAll('#l2-result .tab').forEach((t,j)=>t.classList.toggle('active',j===i));
  renderL2(i);
}

function rpnCls(k) {
  return {operand:'rp-op',op:'rp-ar',assign:'rp-as',УПЛ:'rp-ct',БП:'rp-ct',НП:'rp-np',КП:'rp-np',ТИП:'rp-dc',КО:'rp-dc',label:'rp-lb',Ф:'rp-fn',АЭМ:'rp-fn',return:'rp-fn'}[k]||'rp-op';
}

function renderL2(tab) {
  if (!D.lab2) return;
  const d = D.lab2;
  const el = document.getElementById('l2-body');
  if (tab === 0) {
    const chips = d.elements.map(x=>`<span class="rpn ${rpnCls(x.kind)}" title="${x.kind}">${e(x.value)}</span>`).join('');
    el.innerHTML = `
      <div class="stats">
        <div class="stat"><div class="stat-val">${d.elements.length}</div><div class="stat-lbl">элементов</div></div>
        <div class="stat"><div class="stat-val">${d.elements.filter(x=>x.kind==='assign').length}</div><div class="stat-lbl">присваив.</div></div>
        <div class="stat"><div class="stat-val">${d.elements.filter(x=>x.kind==='УПЛ').length}</div><div class="stat-lbl">УПЛ</div></div>
        <div class="stat"><div class="stat-val">${d.elements.filter(x=>x.kind==='НП').length}</div><div class="stat-lbl">НП</div></div>
      </div>
      <div class="sec">Элементы ОПЗ (→ output2_rpn.txt → Лаба 3)</div>
      <div class="rpn-wrap">${chips}</div>`;
  } else if (tab === 1) {
    el.innerHTML = `<div class="sec">Строка ОПЗ</div><div class="code" style="white-space:pre-wrap;word-break:break-all">${e(d.rpn_string)}</div>`;
  } else if (tab === 2) {
    const trace = d.trace || [];
    const rows = trace.map((s,i) => {
      const mkStack = arr => arr.length
        ? arr.map(op=>`<span class="rpn rp-ar" style="font-size:10px;padding:1px 5px">${e(op)}</span>`).join(' ')
        : '<span style="color:var(--text3);font-size:11px">∅</span>';
      const outAdded = (s.output_added||[]).length
        ? s.output_added.map(v=>`<span class="rpn rp-op" style="font-size:10px;padding:1px 5px">${e(v)}</span>`).join(' ')
        : '<span style="color:var(--text3);font-size:11px">—</span>';
      return `<tr>
        <td style="text-align:center;color:var(--text3);font-size:11px">${i+1}</td>
        <td><span class="chip t${s.tc}" style="font-size:11px">${e(s.val)}</span></td>
        <td style="max-width:160px">${mkStack(s.stack_before)}</td>
        <td style="max-width:160px">${mkStack(s.stack_after)}</td>
        <td>${outAdded}</td>
      </tr>`;
    }).join('');
    el.innerHTML = `
      <div class="sec">Трассировка алгоритма Дейкстры — всего ${trace.length} шагов</div>
      <div style="font-size:12px;color:var(--text2);margin-bottom:8px;line-height:1.5">
        Операнды сразу идут в выходную строку. Операции помещаются в стек и выталкиваются по приоритету.
      </div>
      <div class="tbl-wrap" style="max-height:520px;overflow-y:auto;border:0.5px solid var(--border);border-radius:var(--radius)">
      <table class="tbl">
        <thead style="position:sticky;top:0;z-index:1;background:var(--bg2)"><tr>
          <th style="width:36px">#</th>
          <th>Токен</th>
          <th>Стек до</th>
          <th>Стек после</th>
          <th>Добавлено в выход</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      </div>`;
  } else if (tab === 3) {
    const rows = PRIO_TABLE.map(r=>`<tr><td>${e(r[0])}</td><td style="text-align:center">${r[1]}</td><td style="color:var(--text2)">${r[2]}</td></tr>`).join('');
    el.innerHTML = `<div class="sec">Таблица приоритетов (адаптация табл. 2.8 методички)</div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Элемент</th><th>Приор.</th><th>Примечание</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }
}

// ── Рендеры Лаба 3 ──
function l3tab(i) {
  l3tab_idx = i;
  document.querySelectorAll('#l3-result .tab').forEach((t,j)=>t.classList.toggle('active',j===i));
  renderL3(i);
}

function colorRLine(t) {
  const s = e(t);
  if (s.startsWith('#')) return `<span class="cmt">${s}</span>`;
  return s.replace(/(&lt;-)/g,'<span class="asgn">$1</span>')
          .replace(/\b(function|return|if|goto_line_\d+)\b/g,'<span class="kw">$1</span>')
          .replace(/(&quot;[^&]*&quot;)/g,'<span class="str">$1</span>');
}

function renderL3(tab) {
  if (!D.lab3) return;
  const d = D.lab3;
  const el = document.getElementById('l3-body');
  if (tab === 0) {
    const lines = d.code_lines.map(l=>{
      const ind = '  '.repeat(l.indent);
      return `<div class="code-line"><span class="ln">${l.num}</span><span>${colorRLine(ind+l.text)}</span></div>`;
    }).join('');
    el.innerHTML = `
      <div class="stats">
        <div class="stat"><div class="stat-val">${d.code_lines.length}</div><div class="stat-lbl">строк R</div></div>
        <div class="stat"><div class="stat-val">${d.P}</div><div class="stat-lbl">перем. Rp</div></div>
        <div class="stat"><div class="stat-val">${Object.keys(d.label_table).length}</div><div class="stat-lbl">меток</div></div>
        <div class="stat"><div class="stat-val">2</div><div class="stat-lbl">прохода</div></div>
      </div>
      <div class="sec">output3_r.R</div>
      <div class="code">${lines}</div>`;
  } else if (tab === 1) {
    const rows = d.trace.map((s,i)=>`<tr>
      <td>${i+1}</td>
      <td><span class="rpn ${rpnCls(s.kind)}" style="font-size:11px">${e(s.elem)}</span></td>
      <td>[${e((s.stack_after||[]).slice(-3).join(', '))}]</td>
      <td style="text-align:center">${s.STR_after}</td>
      <td style="color:var(--text2);font-size:11px">${e(s.code_line||'')}</td>
    </tr>`).join('');
    el.innerHTML = `<div class="sec">Трассировка МП-автомата (табл. 3.2 методички) — всего ${d.trace.length} шагов</div>
      <div class="tbl-wrap" style="max-height:520px;overflow-y:auto;border:0.5px solid var(--border);border-radius:var(--radius)">
      <table class="tbl">
        <thead style="position:sticky;top:0;z-index:1;background:var(--bg2)"><tr><th>Шаг</th><th>Элемент ОПЗ</th><th>Стек</th><th>STR</th><th>Код R</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
  } else if (tab === 2) {
    const rows = Object.entries(d.label_table).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td><td style="color:var(--text2)">строка ${v} кода R</td></tr>`).join('');
    el.innerHTML = `<div class="sec">Таблица меток — второй проход МП-автомата</div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Метка</th><th>Строка R</th><th>Примечание</th></tr></thead><tbody>${rows || '<tr><td colspan="3" style="color:var(--text3)">Меток нет</td></tr>'}</tbody></table></div>
      <div style="margin-top:10px;font-size:12px;color:var(--text2);line-height:1.6">
        Второй проход заменяет символьные метки M1, M2… на номера строк R.<br>
        В языке R нет оператора goto — условные переходы реализованы через if/else.
      </div>`;
  }
}

// ── Рендеры Лаба 4 ──
function l4tab(i) {
  l4tab_idx = i;
  document.querySelectorAll('#l4-result .tab').forEach((t,j)=>t.classList.toggle('active',j===i));
  renderL4(i);
}

function renderTree(node, depth) {
  if (!node) return '';
  const isLeaf = !node.children || node.children.length === 0;
  const tok = node.token ? `<span class="tree-token">[${e(node.token)}]</span>` : '';
  const lbl = isLeaf
    ? `<span class="tree-leaf">${e(node.label)}</span>${tok}`
    : `<span class="tree-label">${e(node.label)}</span>${tok}`;
  if (isLeaf) return `<div class="tree-node">${lbl}</div>`;
  const kids = (node.children||[]).map(c => renderTree(c, depth+1)).join('');
  return `<div class="tree-node"><details${depth<3?' open':''}><summary style="cursor:pointer">${lbl}</summary>${kids}</details></div>`;
}

function renderL4(tab) {
  if (!D.lab4) return;
  const d = D.lab4;
  const el = document.getElementById('l4-body');
  if (tab === 0) {
    const alert = d.ok
      ? `<div class="alert alert-ok">✓ Синтаксически корректно — программа соответствует грамматике JS</div>`
      : `<div class="alert alert-err">✗ Ошибки: ${d.errors.map(e=>e(e)).join('<br>')}</div>`;
    const tree = d.tree ? renderTree(d.tree, 0) : '<span style="color:var(--text3)">Дерево не построено</span>';
    el.innerHTML = `${alert}<div class="sec">Дерево разбора (рекурсивный спуск)</div><div class="tree">${tree}</div>`;
  } else if (tab === 1) {
    const rows = d.steps.map((s,i)=>`<tr>
      <td>${i+1}</td>
      <td style="font-weight:500;color:var(--blue-text)">${e(s.proc)}</td>
      <td><span class="chip tI">${e(s.token)}</span></td>
      <td style="color:var(--text2);font-size:11px">${e(s.action)}</td>
    </tr>`).join('');
    el.innerHTML = `<div class="sec">Шаги рекурсивного спуска — всего ${d.steps.length} шагов</div>
      <div class="tbl-wrap" style="max-height:520px;overflow-y:auto;border:0.5px solid var(--border);border-radius:var(--radius)">
      <table class="tbl">
        <thead style="position:sticky;top:0;z-index:1;background:var(--bg2)"><tr><th>#</th><th>Процедура</th><th>NXTSYMB</th><th>Действие</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
  } else if (tab === 2) {
    const rows = GRAMMAR.map(r=>`<tr><td style="color:var(--blue-text);white-space:nowrap">${r[0]}</td><td>${r[1]}</td></tr>`).join('');
    el.innerHTML = `<div class="sec">Грамматика JavaScript (Вариант 10)</div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Нетерминал</th><th>Правило</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div style="margin-top:10px;font-size:12px;color:var(--text2);line-height:1.7">
        <b>NXTSYMB</b> — глобальная переменная с текущим токеном (методичка стр. 57)<br>
        <b>SCAN</b> — переход к следующему токену<br>
        <b>ERROR</b> — фиксация ошибки с указанием позиции<br>
        Каждый нетерминал = отдельная процедура (табл. 4.1 методички)
      </div>`;
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
  loadExample();
});
</script>
</body>
</html>"""

if __name__ == '__main__':
    print("=" * 60)
    print("  Транслятор JS → R | GUI")
    print("  Запустите браузер: http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, port=5000, host='0.0.0.0')