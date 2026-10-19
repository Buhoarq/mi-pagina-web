#!/usr/bin/env python3
"""PuertaFlow · une los archivos Avance_PuertaFlow_*.json en puertaflow/avance.enc.
Uso (desde la raíz del repositorio):
  python3 tabiflow/herramientas/consolidar_puerta.py unir --web puertaflow --clave-web tabiflow ../avances_recibidos/Avance_PuertaFlow_*.json
La clave de obra se toma de la variable de entorno TABIFLOW_CLAVE (nunca la escribas en el repositorio).
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
PESOS = {True: {'traz': 5, 'ref': 30, 'rec': 5, 'mar': 25, 'hoja': 25, 'quin': 10}, False: {'traz': 10, 'mar': 40, 'hoja': 35, 'quin': 15}}
def unir(a):
    key = clave_de(a.clave_web, a.clave)
    modelo = descifrar(key, open(os.path.join(a.web, 'puertas.enc'), 'rb').read())
    pue = {}
    for n in modelo['niveles']:
        for p in n['pue']: p['nv'] = n['id']; pue[p['g']] = p
    ruta = os.path.join(a.web, 'avance.enc')
    base = descifrar(key, open(ruta, 'rb').read()) if os.path.exists(ruta) else {'eventos': []}
    ev = {e['id']: e for e in base.get('eventos', [])}
    personas = set(base.get('personas', [])); fuentes = list(base.get('fuentes', []))
    L = ['Consolidación PuertaFlow · ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    for f in a.archivos:
        try: d = json.load(open(f, encoding='utf8'))
        except Exception as e: L.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(f), e)); continue
        if d.get('app') != 'PuertaFlowHCQ': L.append('⚠ %s: no es un archivo de PuertaFlow' % os.path.basename(f)); continue
        nuevos = anul = ign = 0
        for e in d.get('eventos', []):
            if e.get('g') not in pue: ign += 1; continue
            x = ev.get(e['id'])
            if x is None: ev[e['id']] = e; nuevos += 1
            elif e.get('borrado') and not x.get('borrado'): x['borrado'] = True; x['borradoTs'] = e.get('borradoTs'); anul += 1
        if d.get('por'): personas.add(d['por'])
        fuentes.append({'archivo': os.path.basename(f), 'por': d.get('por'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s): %d registros nuevos, %d anulados%s' % (os.path.basename(f), d.get('por'), nuevos, anul, (', %d ignorados (puerta inexistente)' % ign) if ign else ''))
    est = collections.defaultdict(dict)
    for e in sorted((e for e in ev.values() if not e.get('borrado')), key=lambda e: e.get('ts', '')):
        est[e['g']][e['et']] = e['f']   # el último registro vale (igual que la app)
    tot = collections.defaultdict(lambda: [0.0, 0, 0.0, 0])
    for g, p in pue.items():
        w = PESOS[bool(p.get('ref'))]; s = est.get(g, {})
        t = tot[p['nv']]; t[0] += sum(s.get(et, 0) * v for et, v in w.items()) / 100; t[1] += 1
        if p.get('ref'): t[2] += s.get('ref', 0); t[3] += 1
    L += ['', 'Registros vigentes: %d · personas: %s' % (sum(1 for e in ev.values() if not e.get('borrado')), ', '.join(sorted(personas)) or '—'),
          '', '| Nivel | Puertas | % pond. | Refuerzos instalados |', '|---|---:|---:|---:|']
    for nv, (q, n, r, nr) in tot.items():
        if q > 0: L.append('| %s | %d | %.1f %% | %.0f de %d |' % (nv, n, 100 * q / n, r, nr))
    out = {'modulo': 'puerta', 'actualizado': datetime.datetime.now().astimezone().isoformat(), 'eventos': list(ev.values()), 'personas': sorted(personas), 'fuentes': fuentes}
    open(ruta, 'wb').write(cifrar(key, out))
    print('\n'.join(L))
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave-web', default='tabiflow')
    u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra (variable TABIFLOW_CLAVE)')
    unir(a)
