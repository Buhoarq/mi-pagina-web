#!/usr/bin/env python3
"""PaviFlow (ObraFlow) · une los archivos Avance_PaviFlow_*.json en paviflow/avance.enc.
Uso (desde la raíz del repositorio):
  python3 tabiflow/herramientas/consolidar_pavi.py unir --web paviflow --clave-web tabiflow ../avances_recibidos/Avance_PaviFlow_*.json
La clave de obra se toma de la variable de entorno TABIFLOW_CLAVE (nunca la escribas en el repositorio).
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
# mismas etapas y pesos que PaviFlow v1.9 (sobrelosa + etapas del sistema; los pesos se reparten entre las etapas de cada pavimento)
SIS = {'vin': ['base', 'inst', 'term'], 'por': ['inst', 'term'], 'bal': ['base', 'inst', 'term'], 'hor': ['inst', 'term'], 'mad': ['base', 'inst', 'term'],
       'otr': ['inst', 'term'], 'asf': ['base', 'inst'], 'ext': ['base', 'inst', 'term']}
PESO = {'sob': 25, 'base': 20, 'inst': 35, 'term': 10}
def pesos(p, s):
    ets = (['sob'] if p.get('sl') else []) + SIS.get(s, SIS['otr']); t = sum(PESO[e] for e in ets)
    return {e: 100 * PESO[e] / t for e in ets}
def unir(a):
    key = clave_de(a.clave_web, a.clave)
    modelo = descifrar(key, open(os.path.join(a.web, 'pisos.enc'), 'rb').read())
    pis = {}; hijos = {}            # hijos: pavimento original → sus paños (lo marcado sobre el original vale para todos)
    for n in modelo['niveles']:
        for p in n['pis']:
            s = (modelo['tipos'].get(p['t']) or {}).get('s', 'otr')
            p['nv'] = n['id']; p['w'] = pesos(p, s); pis[p['g']] = p
            if p.get('pg'): hijos.setdefault(p['pg'], []).append(p['g'])
    ruta = os.path.join(a.web, 'avance.enc')
    base = descifrar(key, open(ruta, 'rb').read()) if os.path.exists(ruta) else {'eventos': []}
    ev = {e['id']: e for e in base.get('eventos', [])}
    personas = set(base.get('personas', [])); fuentes = list(base.get('fuentes', []))
    L = ['Consolidación PaviFlow · ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    for f in a.archivos:
        try: d = json.load(open(f, encoding='utf8'))
        except Exception as e: L.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(f), e)); continue
        if d.get('app') != 'PaviFlowHCQ': L.append('⚠ %s: no es un archivo de PaviFlow' % os.path.basename(f)); continue
        nuevos = anul = ign = 0
        for e in d.get('eventos', []):
            if e.get('g') not in pis and e.get('g') not in hijos: ign += 1; continue
            x = ev.get(e['id'])
            if x is None: ev[e['id']] = e; nuevos += 1
            elif e.get('borrado') and not x.get('borrado'): x['borrado'] = True; x['borradoTs'] = e.get('borradoTs'); anul += 1
        if d.get('por'): personas.add(d['por'])
        fuentes.append({'archivo': os.path.basename(f), 'por': d.get('por'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s): %d registros nuevos, %d anulados%s' % (os.path.basename(f), d.get('por'), nuevos, anul, (', %d ignorados (recinto inexistente)' % ign) if ign else ''))
    est = collections.defaultdict(dict)
    for e in ev.values():
        if e.get('borrado'): continue
        for g in ([e['g']] if e['g'] in pis else hijos.get(e['g'], [])):
            o = est[g].get(e['et'])
            if o is None or e['f'] > o: est[g][e['et']] = e['f']
    tot = collections.defaultdict(lambda: [0.0, 0.0])
    for g, p in pis.items():
        eq = sum(est.get(g, {}).get(et, 0) * w for et, w in p['w'].items()) / 100
        tot[p['nv']][0] += p['A'] * eq; tot[p['nv']][1] += p['A']
    L += ['', 'Registros vigentes: %d · personas: %s' % (sum(1 for e in ev.values() if not e.get('borrado')), ', '.join(sorted(personas)) or '—'), '', '| Nivel | m² modelo | m² eq. | % pond. |', '|---|---:|---:|---:|']
    for nv, (q, A) in tot.items():
        if q > 0: L.append('| %s | %d | %d | %.1f %% |' % (nv, A, q, 100 * q / A))
    out = {'modulo': 'pavi', 'actualizado': datetime.datetime.now().astimezone().isoformat(), 'eventos': list(ev.values()), 'personas': sorted(personas), 'fuentes': fuentes}
    open(ruta, 'wb').write(cifrar(key, out))
    print('\n'.join(L))
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave-web', default='tabiflow')
    u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra: defínela en la variable de entorno TABIFLOW_CLAVE.')
    unir(a)
