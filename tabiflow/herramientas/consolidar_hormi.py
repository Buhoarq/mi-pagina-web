#!/usr/bin/env python3
"""HormiFlow (FlujoPlan) · une los archivos Avance_HormiFlow_*.json en hormiflow/avance.enc.
Uso (desde la raíz del repositorio):
  python3 tabiflow/herramientas/consolidar_hormi.py unir --web hormiflow --clave-web tabiflow ../avances_recibidos/Avance_HormiFlow_*.json
La clave de obra se toma de la variable de entorno TABIFLOW_CLAVE (nunca la escribas en el repositorio).
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
def unir(a):
    key = clave_de(a.clave_web, a.clave)
    modelo = descifrar(key, open(os.path.join(a.web, 'hormi.enc'), 'rb').read())
    els = {e['g']: e for e in modelo['el']}
    padres = {e['pg'] for e in modelo['el'] if e.get('pg')}          # muros divididos: aún se aceptan registros hechos sobre el muro entero
    conocido = lambda g: g in els or g in padres
    ruta = os.path.join(a.web, 'avance.enc')
    base = descifrar(key, open(ruta, 'rb').read()) if os.path.exists(ruta) else {'eventos': []}
    ev = {e['id']: e for e in base.get('eventos', [])}
    personas = set(base.get('personas', [])); fuentes = list(base.get('fuentes', []))
    L = ['Consolidación HormiFlow · ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    for f in a.archivos:
        try: d = json.load(open(f, encoding='utf8'))
        except Exception as e: L.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(f), e)); continue
        if d.get('app') != 'HormiFlowHCQ': L.append('⚠ %s: no es un archivo de HormiFlow' % os.path.basename(f)); continue
        nuevos = anul = ign = 0
        for e in d.get('eventos', []):
            gs = e.get('gs') or ([e['g']] if e.get('g') else [])
            if not gs or any(not conocido(g) for g in gs): ign += 1; continue
            x = ev.get(e['id'])
            if x is None: ev[e['id']] = e; nuevos += 1
            elif e.get('borrado') and not x.get('borrado'): x['borrado'] = True; x['borradoTs'] = e.get('borradoTs'); anul += 1
            elif e.get('k') == 'comp' and not x.get('borrado'):          # el compromiso puede recibir causa de incumplimiento
                for c in ('causa', 'notaCausa'):
                    if e.get(c) and e.get(c) != x.get(c): x[c] = e[c]
        if d.get('por'): personas.add(d['por'])
        fuentes.append({'archivo': os.path.basename(f), 'por': d.get('por'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s): %d registros nuevos, %d anulados%s' % (os.path.basename(f), d.get('por'), nuevos, anul, (', %d ignorados (elemento inexistente)' % ign) if ign else ''))
    est = collections.defaultdict(dict)
    for e in ev.values():
        if e.get('borrado') or e.get('k') == 'comp': continue
        o = est[e['g']].get(e['et'])
        if o is None or e['ts'] > o[1]: est[e['g']][e['et']] = (e['f'], e['ts'])   # el último registro manda (se puede desmarcar)
    vol = collections.defaultdict(lambda: [0.0, 0.0])
    for g, el in els.items():
        f_ = est.get(g, {}).get('hor') or est.get(el.get('pg'), {}).get('hor') or (0, '')
        vol[el['nv']][1] += el['v']; vol[el['nv']][0] += el['v'] * f_[0]
    L += ['', 'Registros vigentes: %d · personas: %s' % (sum(1 for e in ev.values() if not e.get('borrado')), ', '.join(sorted(personas)) or '—'), '',
          '| Nivel | m³ modelo | m³ hormigonados | % |', '|---|---:|---:|---:|']
    for nv, (q, V) in vol.items(): L.append('| %s | %.1f | %.1f | %.1f %% |' % (nv, V, q, 100 * q / V if V else 0))
    out = {'modulo': 'hormi', 'actualizado': datetime.datetime.now().astimezone().isoformat(), 'eventos': list(ev.values()), 'personas': sorted(personas), 'fuentes': fuentes}
    open(ruta, 'wb').write(cifrar(key, out))
    print('\n'.join(L))
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave-web', default='tabiflow')
    u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra: defínela en la variable de entorno TABIFLOW_CLAVE.')
    unir(a)
