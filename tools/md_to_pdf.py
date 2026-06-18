#!/usr/bin/env python3
"""md_to_pdf.py — convert a markdown resume to a clean, ATS-friendly PDF.

Stdlib only (no deps, nothing to pip-install). Uses the base-14 Helvetica fonts, so the
text layer is fully selectable/extractable — run `pdftotext out.pdf -` and ATS keyword
parsing works. Supports: # / ## / ### headings, - bullets, **bold**, *italic*, paragraphs,
auto page breaks. Non-ASCII typographic glyphs are normalized so nothing mangles extraction.

Usage:
    python3 tools/md_to_pdf.py examples/resume.md
    python3 tools/md_to_pdf.py input.md output.pdf
"""
import sys, re, os

# AFM advance widths (per-1000-em) for ASCII 32..126. Helvetica & Helvetica-Oblique share
# widths; Helvetica-Bold differs. Plus periodcentered (·) and bullet (•).
_HELV = [278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,556,556,556,556,556,
556,556,556,556,556,278,278,584,584,584,556,1015,667,667,722,722,667,611,778,722,278,500,667,
556,833,722,778,667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,333,556,556,
500,556,556,278,556,556,222,222,500,222,833,556,556,556,556,333,500,278,556,500,722,500,500,
500,334,260,334,584]
_HELVB = [278,333,474,556,556,889,722,238,333,333,389,584,278,333,278,278,556,556,556,556,556,
556,556,556,556,556,333,333,584,584,584,611,975,722,722,722,722,667,611,778,722,278,556,722,
611,833,722,778,667,778,722,667,611,722,667,944,667,667,611,333,278,333,584,556,333,556,611,
556,611,556,333,611,611,278,278,556,278,889,611,611,611,611,389,556,333,611,556,778,556,556,
500,389,280,389,584]
HELV = {chr(32 + i): w for i, w in enumerate(_HELV)}
HELVB = {chr(32 + i): w for i, w in enumerate(_HELVB)}
for t in (HELV, HELVB):
    t['·'] = 278   # middle dot ·
    t['•'] = 350   # bullet •

NORM = {'—': '-', '–': '-', '‘': "'", '’': "'", '“': '"',
        '”': '"', '…': '...', ' ': ' '}
ENC = {'·': 0xB7, '•': 0x95}  # WinAnsi byte for the kept non-ASCII glyphs


NORM.update({'→': '->', '←': '<-', '⇒': '=>', '\t': ' '})


def normalize(s):
    return ''.join(NORM.get(c, c) for c in s)


def width(s, size, bold):
    t = HELVB if bold else HELV
    return sum(t.get(c, 556) for c in s) / 1000.0 * size


def enc(s):
    out = bytearray()
    for c in s:
        if c in ENC:
            out.append(ENC[c])
        else:
            o = ord(c)
            out.append(o if 32 <= o <= 126 else ord('?'))
    # escape PDF string specials
    return bytes(out).replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')


def parse_runs(text):
    """Split inline **bold** / *italic* into (text, style) runs; style in r/b/i."""
    runs = []
    for tok in re.split(r'(\*\*.*?\*\*|\*[^*]+?\*)', text):
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**'):
            runs.append((normalize(tok[2:-2]), 'b'))
        elif tok.startswith('*') and tok.endswith('*'):
            runs.append((normalize(tok[1:-1]), 'i'))
        else:
            runs.append((normalize(tok), 'r'))
    return runs


def parse_blocks(md):
    blocks, cur = [], None
    def flush():
        nonlocal cur
        if cur:
            blocks.append(cur); cur = None
    for raw in md.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            flush(); continue
        if s.startswith('### '):
            flush(); blocks.append(('h3', s[4:]))
        elif s.startswith('## '):
            flush(); blocks.append(('h2', s[3:]))
        elif s.startswith('# '):
            flush(); blocks.append(('h1', s[2:]))
        elif s.startswith('- '):
            flush(); cur = ['bullet', s[2:]]
        else:
            if cur:
                cur[1] += ' ' + s
            else:
                cur = ['body', s]
    flush()
    return blocks


# layout constants (Letter)
PW, PH = 612.0, 792.0
LM, RM, TM, BM = 54.0, 54.0, 760.0, 42.0
MAXW = PW - LM - RM
FNT = {'r': '/F1', 'b': '/F2', 'i': '/F3'}


def wrap(runs, size, maxw, hang=0):
    """Greedy-wrap mixed-style runs into lines; each line = list of (text, style)."""
    words = []
    for txt, st in runs:
        parts = txt.split(' ')
        for i, p in enumerate(parts):
            if p == '' and i == 0:
                continue
            words.append((p, st))
    lines, line, x = [], [], 0.0
    space = width(' ', size, False)
    avail = maxw - hang
    for w, st in words:
        ww = width(w, size, st == 'b')
        add = ww + (space if line else 0)
        if line and x + add > avail:
            lines.append(line); line, x = [], 0.0
            add = ww
        line.append((w, st)); x += add
    if line:
        lines.append(line)
    return lines


class PDF:
    def __init__(self):
        self.pages, self.ops, self.y = [], [], TM

    def newpage(self):
        if self.ops:
            self.pages.append(self.ops)
        self.ops, self.y = [], TM

    def need(self, h):
        if self.y - h < BM:
            self.newpage()

    def line_runs(self, runs, size, x0, leading, hang=0, gap_after=0):
        for ln in wrap(runs, size, MAXW - (x0 - LM), hang):
            self.need(leading)
            x = x0 + (hang if False else 0)
            tx = x0 + hang if hang else x0
            cx = tx
            for w, st in ln:
                t = ('BT %s %.1f Tf 1 0 0 1 %.1f %.1f Tm (' % (FNT[st], size, cx, self.y)).encode('latin-1')
                t += enc(w) + b') Tj ET'
                self.ops.append(t)
                cx += width(w, size, st == 'b') + width(' ', size, False)
            self.y -= leading
        self.y -= gap_after

    def rule(self, y):
        self.ops.append(('%.1f %.1f m %.1f %.1f l 0.5 w 0.7 0.7 0.7 RG S' %
                          (LM, y, PW - RM, y)).encode('latin-1'))

    def render(self, blocks):
        for b in blocks:
            kind = b[0]
            if kind == 'h1':
                self.need(24)
                self.line_runs([(normalize(b[1]), 'b')], 18, LM, 21, gap_after=0.5)
            elif kind == 'h2':
                self.y -= 4.5
                self.need(16)
                self.line_runs([(normalize(b[1]).upper(), 'b')], 11, LM, 12.8)
                self.rule(self.y + 8.3)  # sit the rule just under the (uppercase) heading, clear of body
                self.y -= 1.5
            elif kind == 'h3':
                self.y -= 2.5
                self.need(14)
                self.line_runs(parse_runs(b[1]), 10.3, LM, 12.3, gap_after=0.5)
            elif kind == 'bullet':
                runs = parse_runs(b[1])
                # bullet marker then hanging-indented text
                self.need(11.7)
                self.ops.append(('BT /F1 9.4 Tf 1 0 0 1 %.1f %.1f Tm (' % (LM + 3, self.y)).encode('latin-1')
                                 + enc('•') + b') Tj ET')
                self.line_runs(runs, 9.4, LM + 13, 11.7)
            else:  # body
                self.line_runs(parse_runs(b[1]), 9.4, LM, 11.8, gap_after=1)
        self.newpage()

    def bytes(self):
        objs = []
        # 1 catalog, 2 pages, fonts 3/4/5, then per page: content + page
        font_objs = {'/F1': 'Helvetica', '/F2': 'Helvetica-Bold', '/F3': 'Helvetica-Oblique'}
        n_pages = len(self.pages)
        page_ids = [6 + 2 * i for i in range(n_pages)]
        content_ids = [7 + 2 * i for i in range(n_pages)]
        objs.append((1, b'<< /Type /Catalog /Pages 2 0 R >>'))
        kids = ' '.join('%d 0 R' % p for p in page_ids)
        objs.append((2, ('<< /Type /Pages /Count %d /Kids [%s] >>' % (n_pages, kids)).encode()))
        objs.append((3, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'))
        objs.append((4, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>'))
        objs.append((5, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>'))
        for i, ops in enumerate(self.pages):
            stream = b'\n'.join(ops)
            objs.append((content_ids[i], b'<< /Length %d >>\nstream\n%s\nendstream' % (len(stream), stream)))
            page = ('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] '
                    '/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> '
                    '/Contents %d 0 R >>' % (PW, PH, content_ids[i])).encode()
            objs.append((page_ids[i], page))
        objs.sort()
        out = bytearray(b'%PDF-1.4\n')
        offsets = {}
        for num, body in objs:
            offsets[num] = len(out)
            out += ('%d 0 obj\n' % num).encode() + body + b'\nendobj\n'
        xref = len(out)
        maxn = max(offsets) + 1
        out += ('xref\n0 %d\n' % maxn).encode()
        out += b'0000000000 65535 f \n'
        for n in range(1, maxn):
            out += ('%010d 00000 n \n' % offsets.get(n, 0)).encode()
        out += ('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF' % (maxn, xref)).encode()
        return bytes(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(inp)[0] + '.pdf'
    md = open(inp, encoding='utf-8').read()
    pdf = PDF()
    pdf.render(parse_blocks(md))
    data = pdf.bytes()
    with open(out, 'wb') as f:
        f.write(data)
    print('wrote %s (%d bytes, %d page(s))' % (out, len(data), len(pdf.pages)))


if __name__ == '__main__':
    main()
