#!/usr/bin/env python3
"""PuertaFlow · Coordinación de refuerzos: une los archivos Coord_PuertaFlow_*.json en puertaflow/coordavance.enc.
Uso (desde la raíz del repositorio):
  python3 tabiflow/herramientas/consolidar_coord.py unir --web puertaflow --clave-web tabiflow ../avances_recibidos/Coord_PuertaFlow_*.json
La clave de obra se toma de TABIFLOW_CLAVE; con ella se abre la clave de coordinación guardada en coord_acceso.json.
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, base64, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
NOM = {'rdi': 'interferencias', 'prog': 'solicitadas', 'lib': 'liberadas', 'inst': 'instaladas', 'ok': 'recibidas', 'obs': 'observadas', 'prob': 'problemas'}
def unir(a):
    obra = clave_de(a.clave_web, a.clave)
    acc = json.load(open(os.path.join(a.web, 'coord_acceso.json')))
    e = [x for x in acc['roles'] if x['rol'] == 'obra'][0]
    kc = base64.b64decode(descifrar(obra, base64.b64decode(e['w']))['k'])
    ruta = os.path.join(a.web, 'coordavance.enc')
    base = descifrar(kc, open(ruta, 'rb').read()) if os.path.exists(ruta) else {'tickets': []}
    rf = os.path.join(a.web, 'coordfotos.enc')
    fotos = descifrar(kc, open(rf, 'rb').read()) if os.path.exists(rf) else {}
    tk = {t['id']: t for t in base.get('tickets', [])}; fuentes = list(base.get('fuentes', [])); personas = set(base.get('personas', []))
    L = ['Consolidación Coordinación PuertaFlow · ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    for f in a.archivos:
        try: d = json.load(open(f, encoding='utf8'))
        except Exception as ex: L.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(f), ex)); continue
        if d.get('app') != 'PuertaCoordHCQ': L.append('⚠ %s: no es un archivo de tickets de PuertaFlow' % os.path.basename(f)); continue
        nuevos = anul = 0
        for t in d.get('tickets', []):
            t.pop('recibido', None)
            for fo in t.get('fotos') or []:
                if fo.get('d'): fotos[fo['id']] = fo.pop('d')
            x = tk.get(t['id'])
            if x is None: tk[t['id']] = t; nuevos += 1
            elif t.get('borrado') and not x.get('borrado'): x['borrado'] = True; x['borradoTs'] = t.get('borradoTs'); anul += 1
        if d.get('por'): personas.add('%s (%s)' % (d['por'], d.get('rol', '?')))
        fuentes.append({'archivo': os.path.basename(f), 'por': d.get('por'), 'rol': d.get('rol'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s, %s): %d tickets nuevos, %d anulados' % (os.path.basename(f), d.get('por'), d.get('rol'), nuevos, anul))
    est = {}
    for t in sorted((t for t in tk.values() if not t.get('borrado')), key=lambda t: t['ts']):
        for g in t['g']:
            if t['tipo'] not in ('prob', 'rdi'): est[g] = t['tipo']
    c = collections.Counter(est.values())
    L += ['', 'Tickets vigentes: %d · puertas con estado: %d' % (sum(1 for t in tk.values() if not t.get('borrado')), len(est)),
          'Estado actual: ' + (', '.join('%d %s' % (c[k], NOM[k]) for k in ('prog', 'lib', 'inst', 'obs', 'ok') if c[k]) or '—')]
    out = {'modulo': 'coord', 'actualizado': datetime.datetime.now().astimezone().isoformat(), 'tickets': list(tk.values()), 'personas': sorted(personas), 'fuentes': fuentes[-500:]}
    open(ruta, 'wb').write(cifrar(kc, out)); open(rf, 'wb').write(cifrar(kc, fotos))
    L.append('Fotos guardadas: %d · interferencias para RDI: %d' % (len(fotos), sum(1 for t in tk.values() if t['tipo'] == 'rdi' and not t.get('borrado'))))
    print('\n'.join(L))
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave-web', default='tabiflow')
    u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra (variable TABIFLOW_CLAVE)')
    unir(a)
