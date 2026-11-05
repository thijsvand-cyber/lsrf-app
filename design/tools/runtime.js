// Minimal static renderer for .dc.html artboards (print only: no events).
class DCLogic {
  constructor(props) { this.props = props || {}; this.state = {}; }
  setState(s) { Object.assign(this.state, s); }
  forceUpdate() {}
}
window.DCLogic = DCLogic;

function lookup(path, scope) {
  path = path.trim();
  if (path === 'true') return true;
  if (path === 'false') return false;
  if (/^-?\d+(\.\d+)?$/.test(path)) return Number(path);
  let v = scope;
  for (const k of path.split('.')) { if (v == null) return undefined; v = v[k]; }
  return v;
}
function fill(str, scope) {
  return str.replace(/\{\{([^}]+)\}\}/g, (_, p) => { const v = lookup(p, scope); return v == null || typeof v === 'function' ? '' : String(v); });
}
function proc(node, scope) {
  if (node.nodeType === 3) { if (node.nodeValue.includes('{{')) node.nodeValue = fill(node.nodeValue, scope); return; }
  if (node.nodeType !== 1) return;
  const tag = node.tagName.toLowerCase();
  if (tag === 'sc-for') {
    const list = lookup(node.getAttribute('list').replace(/[{}]/g, ''), scope) || [];
    const as = node.getAttribute('as');
    const parent = node.parentNode;
    list.forEach((item, i) => {
      const s = Object.assign({}, scope, { [as]: item, $index: i });
      for (const c of Array.from(node.childNodes)) { const cl = c.cloneNode(true); parent.insertBefore(cl, node); proc(cl, s); }
    });
    parent.removeChild(node); return;
  }
  if (tag === 'sc-if') {
    const ok = lookup(node.getAttribute('value').replace(/[{}]/g, ''), scope);
    const parent = node.parentNode;
    if (ok) { for (const c of Array.from(node.childNodes)) { parent.insertBefore(c, node); proc(c, scope); } }
    parent.removeChild(node); return;
  }
  for (const a of Array.from(node.attributes)) {
    if (/^on[A-Z]/.test(a.name) || /^on/i.test(a.name)) { node.removeAttribute(a.name); continue; }
    if (a.value.includes('{{')) node.setAttribute(a.name, fill(a.value, scope));
  }
  for (const c of Array.from(node.childNodes)) proc(c, scope);
}

window.renderDC = function (markup, code, propsDefaults) {
  const Component = new Function('DCLogic', code + '\nreturn Component;')(DCLogic);
  const inst = new Component(propsDefaults);
  const vals = inst.renderVals();
  const tpl = document.createElement('template');
  tpl.innerHTML = markup;
  const frag = tpl.content;
  const helmet = frag.querySelector('helmet');
  if (helmet) {
    helmet.querySelectorAll('style').forEach((s) => { const st = document.createElement('style'); st.textContent = s.textContent; document.head.appendChild(st); });
    helmet.remove();
  }
  const host = document.getElementById('host');
  host.appendChild(frag);
  for (const c of Array.from(host.childNodes)) proc(c, vals);
  // Expand the scroll area so the full screen length is shown.
  const root = host.firstElementChild;
  let extra = 0;
  root.querySelectorAll('*').forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.overflowY === 'auto' && el.scrollHeight > el.clientHeight) extra = Math.max(extra, el.scrollHeight - el.clientHeight);
  });
  if (extra && !window.NO_EXPAND) root.style.height = (844 + extra) + 'px';
  return { w: root.offsetWidth, h: root.offsetHeight };
};
