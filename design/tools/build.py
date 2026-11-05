import html, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright
from render import parse, FONTS, RUNTIME  # reuse helpers (render.py guarded below)

SCREENS = [('main', 'Main.dc.html'), ('listen', 'Podcasts.dc.html'), ('klak-af', 'KlakAf.dc.html'),
           ('cross', 'Channel.dc.html'), ('team', 'Team.dc.html'), ('shop', 'Shop.dc.html')]
ROUTE = {f: r for r, f in SCREENS}
SRC = Path('/home/claude/lsrf/project')

POST = r"""
(route) => {
  const root = document.getElementById('host').firstElementChild;
  root.style.width = '100%'; root.style.height = '100%';
  document.querySelectorAll('#host a[href$=".dc.html"]').forEach(a => {
    const f = a.getAttribute('href'); a.setAttribute('href', '#' + route[f]);
  });
  const rep = [
    ['bottom: 156px', 'bottom: calc(var(--tab) + 72px)'],
    ['bottom: 92px', 'bottom: calc(var(--tab) + 8px)'],
    ['bottom: 84px', 'bottom: var(--tab)'],
    ['height: 84px', 'height: var(--tab); padding-bottom: var(--bot)'],
    ['padding: 52px 16px', 'padding: calc(var(--top) + 10px) 16px'],
    ['padding: 48px 12px 12px', 'padding: calc(var(--top) + 4px) 12px 12px'],
    ['padding: 10px 12px 30px', 'padding: 10px 12px calc(10px + var(--bot))'],
  ];
  document.querySelectorAll('#host [style]').forEach(el => {
    let s = el.getAttribute('style');
    for (const [a, b] of rep) s = s.split(a).join(b);
    if (/overflow-y: auto/.test(s)) s += '; overscroll-behavior: contain; -webkit-overflow-scrolling: touch';
    el.setAttribute('style', s);
  });
  document.querySelectorAll('#host input').forEach(i => { i.style.fontSize = '16px'; i.removeAttribute('value'); });
  document.querySelectorAll('#host [aria-selected]').forEach(e => {});
  return root.outerHTML;
}
"""

views = []
styles = set()
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--allow-file-access-from-files'])
    pg = b.new_page()
    for route, fn in SCREENS:
        markup, code, defaults = parse(SRC / fn)
        h = Path('/home/claude/render/out') / f'proto-{route}.html'
        h.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{FONTS}</style></head><body><div id='host' style='width:390px;height:844px'></div><script>window.NO_EXPAND=true;{RUNTIME}</script></body></html>")
        pg.goto(h.as_uri())
        pg.evaluate('([m,c,d]) => renderDC(m,c,d)', [markup, code, defaults])
        out = pg.evaluate(POST, ROUTE)
        for s in pg.evaluate("[...document.querySelectorAll('head style')].slice(1).map(s=>s.textContent)"):
            styles.add(s.strip())
        views.append((route, out))
    b.close()

helmet_css = '\n'.join(sorted(styles))
# keep only rules useful in the app (the .ph stripe pattern + link colours scoped by screen are fine to share)
ph = '.ph{background:repeating-linear-gradient(135deg,#0A3E50 0 14px,#06384A 14px 28px)}'

view_html = '\n'.join(f'<section class="view" id="v-{r}" data-route="{r}" aria-label="{r}">{o}</section>' for r, o in views)

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="LSRF">
<meta name="theme-color" content="#043241">
<title>LSRF — app prototype</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&family=Chakra+Petch:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--top:max(env(safe-area-inset-top),20px);--bot:env(safe-area-inset-bottom,0px);--tab:calc(60px + var(--bot));}}
html,body{{margin:0;height:100%;background:#1d0712;overflow:hidden;-webkit-text-size-adjust:100%;}}
*{{-webkit-tap-highlight-color:transparent;}}
#app{{position:fixed;top:0;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:430px;overflow:hidden;background:#043241;}}
@media (min-width:600px){{#app{{top:24px;bottom:24px;max-height:932px;margin:auto 0;border-radius:44px;box-shadow:0 0 0 10px #043241,0 30px 80px rgba(0,0,0,.6);}}}}
.view{{position:absolute;inset:0;display:none;}}
.view.on{{display:block;animation:in .18s ease-out;}}
@keyframes in{{from{{opacity:.4;transform:translateX(8px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{.view.on{{animation:none}}}}
{ph}
a{{color:inherit}}
button{{-webkit-appearance:none}}
input::placeholder{{color:#A9C4CD}}
</style>
</head>
<body>
<div id="app">
{view_html}
</div>
<script>
(function(){{
  var routes = {json.dumps([r for r, _ in SCREENS])};
  function show(){{
    var r = (location.hash || '').slice(1);
    if (routes.indexOf(r) < 0) r = 'main';
    document.querySelectorAll('.view').forEach(function(v){{
      var on = v.dataset.route === r;
      v.classList.toggle('on', on);
      if (on) v.querySelectorAll('*').forEach(function(el){{ if (getComputedStyle(el).overflowY === 'auto') el.scrollTop = 0; }});
    }});
  }}
  window.addEventListener('hashchange', show);
  document.querySelectorAll('form').forEach(function(f){{ f.addEventListener('submit', function(e){{ e.preventDefault(); }}); }});
  show();
}})();
</script>
</body>
</html>
"""
Path('/home/claude/render/lsrf-prototype.html').write_text(page)
print(len(page), [r for r, _ in views])
