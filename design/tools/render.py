import html, json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfWriter, PdfReader

SRC = Path('/home/claude/lsrf/project')
OUT = Path('/home/claude/render/out'); OUT.mkdir(exist_ok=True)
NM = Path('/home/claude/render/node_modules').as_uri()
RUNTIME = Path('/home/claude/render/runtime.js').read_text()

SCREENS = [
    ('Main.dc.html', 'Front page'),
    ('Podcasts.dc.html', 'Listen — podcasts'),
    ('KlakAf.dc.html', 'Klak Af! — channels'),
    ('Channel.dc.html', 'Klak Af! — Cross'),
    ('Team.dc.html', 'Team Bomba Join'),
    ('Shop.dc.html', 'Shop'),
]

FONTS = f"""
@font-face{{font-family:'Archivo';font-style:normal;font-weight:100 900;font-stretch:62% 125%;src:url('{NM}/@fontsource-variable/archivo/files/archivo-latin-wdth-normal.woff2') format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2190-2199,U+2212,U+2215,U+FEFF,U+FFFD;}}
@font-face{{font-family:'Archivo';font-style:normal;font-weight:100 900;font-stretch:62% 125%;src:url('{NM}/@fontsource-variable/archivo/files/archivo-latin-ext-wdth-normal.woff2') format('woff2');unicode-range:U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF;}}
""" + ''.join(
    f"@font-face{{font-family:'Chakra Petch';font-weight:{w};src:url('{NM}/@fontsource/chakra-petch/files/chakra-petch-latin-{w}-normal.woff2') format('woff2');}}"
    for w in (500, 600, 700))

PAGE_CSS = """
html,body{margin:0;background:#1d0712;}
.wrap{padding:36px 40px 44px;display:flex;flex-direction:column;gap:18px;}
.lab{display:flex;justify-content:space-between;align-items:baseline;font-family:'Chakra Petch';color:#F062F9;font-weight:700;font-size:13px;letter-spacing:.08em;text-transform:uppercase}
.lab b{font-family:Archivo;font-weight:900;font-stretch:62.5%;font-size:30px;color:#EEFF07;letter-spacing:0}
#host{border-radius:36px;overflow:hidden;width:390px;box-shadow:0 0 0 8px #043241;}
"""

def page_html(body_extra=''):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{FONTS}{PAGE_CSS}</style></head><body>{body_extra}</body></html>"

def parse(path):
    t = path.read_text()
    markup = re.search(r'<x-dc>(.*)</x-dc>', t, re.S).group(1)
    m = re.search(r"<script type=\"text/x-dc\" data-dc-script data-props='(.*?)'>(.*?)</script>", t, re.S)
    props = json.loads(html.unescape(m.group(1)))
    defaults = {k: v.get('default') for k, v in props.items() if isinstance(v, dict) and 'default' in v and not k.startswith('$')}
    return markup, m.group(2), defaults

if __name__ == '__main__':
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--allow-file-access-from-files'])
        pg = b.new_page()
        parts = []
        # Cover
        cover = OUT / 'cover.html'
        cover.write_text(page_html("""
    <div style="width:470px;height:964px;box-sizing:border-box;padding:56px 40px;background:#F062F9;color:#043241;display:flex;flex-direction:column;justify-content:space-between">
    <div style="font-family:Archivo;font-weight:900;font-stretch:125%;font-size:22px;line-height:1;text-transform:uppercase">Live Slow<br>Ride Fast</div>
    <div>
    <div style="font-family:'Chakra Petch';font-weight:700;font-size:14px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px">Mobile app · core screens v1</div>
    <div style="font-family:Archivo;font-weight:900;font-stretch:62.5%;font-size:120px;line-height:.86;text-transform:uppercase">Just.<br>Show.<br>Up.</div>
    </div>
    <div style="font-family:'Chakra Petch';font-weight:600;font-size:14px;line-height:1.6">
    01 Front page<br>02 Listen — LSRF Podcast &amp; Beter Worden<br>03 Klak Af! — channels<br>04 Klak Af! — Cross<br>05 Team Bomba Join — cyclocross<br>06 Shop
    <div style="margin-top:18px;font-weight:500;font-size:12px">Concept mockups · [bracketed] text = placeholder · 05/11/2026</div>
    </div>
    </div>"""))
        pg.goto(cover.as_uri()); pg.wait_for_timeout(400); pg.evaluate('document.fonts.ready')
        f = OUT / '00.pdf'; pg.pdf(path=str(f), width='470px', height='964px', print_background=True); parts.append(f)

        for i, (fn, label) in enumerate(SCREENS, 1):
            markup, code, defaults = parse(SRC / fn)
            h = OUT / f'{i:02d}.html'
            h.write_text(page_html(f"<div class='wrap'><div class='lab'><b>{i:02d} {html.escape(label)}</b><span>LSRF app</span></div><div id='host'></div></div><script>{RUNTIME}</script>"))
            pg.goto(h.as_uri())
            size = pg.evaluate('([m,c,d]) => renderDC(m,c,d)', [markup, code, defaults])
            pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(500)
            W = 470; H = pg.evaluate("document.querySelector('.wrap').offsetHeight")
            f = OUT / f'{i:02d}.pdf'
            pg.pdf(path=str(f), width=f'{W}px', height=f'{H + 1}px', print_background=True, page_ranges='1')
            pg.screenshot(path=str(OUT / f'{i:02d}.png'), full_page=True)
            parts.append(f)
            print(fn, size, H)
        b.close()

    w = PdfWriter()
    for f in parts:
        for page in PdfReader(str(f)).pages: w.add_page(page)
    w.write('/home/claude/render/LSRF-app-screens.pdf')
    print('done')
