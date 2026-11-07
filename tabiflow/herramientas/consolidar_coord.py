#!/usr/bin/env python3
"""PuertaFlow · Coordinación de refuerzos: une los archivos Coord_PuertaFlow_*.json en puertaflow/coordavance.enc.
Uso (desde la raíz del repositorio):
  python3 tabiflow/herramientas/consolidar_coord.py unir --web puertaflow --clave-web tabiflow ../avances_recibidos/Coord_PuertaFlow_*.json
La clave de obra se toma de TABIFLOW_CLAVE; con ella se abre la clave de coordinación guardada en coord_acceso.json.
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, base64, collections, io, glob
# v0.32 (07-11-2026, Renato: "que las fotos pesen lo mínimo y carguen más rápido"): cada foto se deja en ≤ 800 px, JPEG calidad 50
# (~35 KB) y se reparten en 16 archivos coordfotos_00.enc … coordfotos_15.enc según su id: el teléfono baja solo el archivo de la foto
# que mira (~1 MB) y no las ~300 fotos juntas. El antiguo coordfotos.enc (todo junto) se lee si existe y se elimina.
NFOT = 16; LADO = 800; CALIDAD = 50
def grupo(i):
    h = 0
    for ch in i: h = (h * 31 + ord(ch)) & 0xffffffff
    return h % NFOT
def liviana(d):
    """data URL → JPEG ≤ 800 px, calidad 50 (si Pillow no está, la foto queda como llegó)"""
    try:
        from PIL import Image
        if len(d) < 60000: return d
        im = Image.open(io.BytesIO(base64.b64decode(d.split(',', 1)[1]))).convert('RGB'); im.thumbnail((LADO, LADO))
        b = io.BytesIO(); im.save(b, 'JPEG', quality=CALIDAD, optimize=True, progressive=True)
        n = 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
        return n if len(n) < len(d) else d
    except Exception: return d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
NOM = {'rdi': 'interferencias', 'prog': 'por trazar', 'tr1': 'por desarmar y picar', 'des': 'desarmadas', 'sin': 'reiniciadas', 'pic': 'por retrazar', 'lib': 'liberadas', 'inst': 'instaladas', 'ok': 'recibidas', 'obs': 'observadas', 'prob': 'problemas', 'res': 'problemas resueltos'}
def unir(a):
    obra = clave_de(a.clave_web, a.clave)
    acc = json.load(open(os.path.join(a.web, 'coord_acceso.json')))
    e = [x for x in acc['roles'] if x['rol'] == 'obra'][0]
    kc = base64.b64decode(descifrar(obra, base64.b64decode(e['w']))['k'])
    ruta = os.path.join(a.web, 'coordavance.enc')
    base = descifrar(kc, open(ruta, 'rb').read()) if os.path.exists(ruta) else {'tickets': []}
    rf = os.path.join(a.web, 'coordfotos.enc'); fotos = {}
    if os.path.exists(rf): fotos.update(descifrar(kc, open(rf, 'rb').read()))
    for f in sorted(glob.glob(os.path.join(a.web, 'coordfotos_[0-9][0-9].enc'))): fotos.update(descifrar(kc, open(f, 'rb').read()))
    antes = sum(len(v) for v in fotos.values())
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
            if t['tipo'] not in ('prob', 'res', 'rdi', 'cond'): est[g] = t['tipo']
    c = collections.Counter(est.values())
    L += ['', 'Tickets vigentes: %d · puertas con estado: %d' % (sum(1 for t in tk.values() if not t.get('borrado')), len(est)),
          'Estado actual: ' + (', '.join('%d %s' % (c[k], NOM[k]) for k in ('prog', 'tr1', 'des', 'pic', 'lib', 'inst', 'obs', 'ok') if c[k]) or '—')]
    out = {'modulo': 'coord', 'actualizado': datetime.datetime.now().astimezone().isoformat(), 'tickets': list(tk.values()), 'personas': sorted(personas), 'fuentes': fuentes[-500:]}
    open(ruta, 'wb').write(cifrar(kc, out))
    fotos = {k: liviana(v) for k, v in fotos.items()}; G = [{} for _ in range(NFOT)]
    for k, v in fotos.items(): G[grupo(k)][k] = v
    for i, g in enumerate(G): open(os.path.join(a.web, 'coordfotos_%02d.enc' % i), 'wb').write(cifrar(kc, g))
    if os.path.exists(rf): os.remove(rf)
    despues = sum(len(v) for v in fotos.values())
    L.append('Fotos: %.1f MB → %.1f MB, en %d archivos coordfotos_NN.enc' % (antes * 3 / 4 / 1e6, despues * 3 / 4 / 1e6, NFOT))
    L.append('Fotos guardadas: %d · interferencias para RDI: %d' % (len(fotos), sum(1 for t in tk.values() if t['tipo'] == 'rdi' and not t.get('borrado'))))
    print('\n'.join(L))
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave-web', default='tabiflow')
    u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra (variable TABIFLOW_CLAVE)')
    unir(a)
