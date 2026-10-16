#!/usr/bin/env python3
"""PaviFlow (ObraFlow) · une los archivos Avance_PaviFlow_*.json en paviflow/avance.enc.
Uso (desde la raíz del repositorio):
  python3 tabiflow/herramientas/consolidar_pavi.py unir --web paviflow --clave-web tabiflow ../avances_recibidos/Avance_PaviFlow_*.json
La clave de obra se toma de la variable de entorno TABIFLOW_CLAVE (nunca la escribas en el repositorio).
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
PESOS = {'vin': {'base': 40, 'inst': 40, 'term': 20}, 'por': {'base': 30, 'inst': 50, 'term': 20}, 'hor': {'inst': 70, 'term': 30},
         'mad': {'base': 30, 'inst': 50, 'term': 20}, 'otr': {'inst': 70, 'term': 30}, 'imp': {'imp': 100}}
PESOS_IMP = {'vin': {'imp': 15, 'base': 25, 'inst': 40, 'term': 20}, 'por': {'imp': 15, 'base': 15, 'inst': 50, 'term': 20},
             'hor': {'imp': 15, 'inst': 55, 'term': 30}, 'mad': {'imp': 15, 'base': 15, 'inst': 50, 'term': 20}, 'otr': {'imp': 15, 'inst': 55, 'term': 30}}
def unir(a):
    key = clave_de(a.clave_web, a.clave)
    modelo = descifrar(key, open(os.path.join(a.web, 'pisos.enc'), 'rb').read())
    pis = {}
    for n in modelo['niveles']:
        for p in n['pis']:
            s = (modelo['tipos'].get(p['t']) or {}).get('s', 'otr')
            if p['t'] == 'IMP': s = 'imp'
            p['nv'] = n['id']; p['w'] = (PESOS_IMP.get(s) if p.get('i') and s != 'imp' else PESOS[s]); pis[p['g']] = p
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
            if e.get('g') not in pis: ign += 1; continue
            x = ev.get(e['id'])
            if x is None: ev[e['id']] = e; nuevos += 1
            elif e.get('borrado') and not x.get('borrado'): x['borrado'] = True; x['borradoTs'] = e.get('borradoTs'); anul += 1
        if d.get('por'): personas.add(d['por'])
        fuentes.append({'archivo': os.path.basename(f), 'por': d.get('por'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s): %d registros nuevos, %d anulados%s' % (os.path.basename(f), d.get('por'), nuevos, anul, (', %d ignorados (recinto inexistente)' % ign) if ign else ''))
    est = collections.defaultdict(dict)
    for e in ev.values():
        if e.get('borrado'): continue
        o = est[e['g']].get(e['et'])
        if o is None or e['f'] > o: est[e['g']][e['et']] = e['f']
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
