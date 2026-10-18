#!/usr/bin/env python3
"""Last Planner (TabiFlow v6.1 β) · Plan semanal (Last Planner): consolida compromisos y causas, y administra las claves de subcontrato.
Uso (desde la raíz del repositorio; la clave de obra va en la variable TABIFLOW_CLAVE, nunca en el repositorio):

  python3 tabiflow/herramientas/consolidar_plan.py unir --web lastplanner ../avances_recibidos/Avance_*.json
      Une los compromisos y causas de los archivos "Avance_….json" en lastplanner/plan.enc (sin duplicar, por id).
      El avance (eventos) de esos mismos archivos se sigue consolidando con consolidar.py en tabiflow/avance.enc.

  python3 tabiflow/herramientas/consolidar_plan.py sub-agregar --web lastplanner "Nombre del subcontrato"
      Crea (o renueva) la clave propia de ese subcontrato e imprime la clave para entregársela en persona.

  python3 tabiflow/herramientas/consolidar_plan.py sub-quitar --web lastplanner "Nombre del subcontrato"
  python3 tabiflow/herramientas/consolidar_plan.py sub-lista --web lastplanner

La clave de subcontrato da acceso de consulta filtrado a sus propios compromisos (filtro de la app, no aislamiento total).
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, base64, json, os, sys, datetime, secrets
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar, derivar, ITER

def leer_plan(key, web):
    ruta = os.path.join(web, 'plan.enc')
    if os.path.exists(ruta):
        return descifrar(key, open(ruta, 'rb').read())
    return {'compromisos': [], 'causas': [], 'subcontratos': [], 'fuentes': []}

def guardar_plan(key, web, plan):
    plan['actualizado'] = datetime.datetime.now().astimezone().isoformat()
    open(os.path.join(web, 'plan.enc'), 'wb').write(cifrar(key, plan))

def leer_subs(web):
    ruta = os.path.join(web, 'subclaves.json')
    return json.load(open(ruta)) if os.path.exists(ruta) else {'subs': []}

def unir(a):
    key = clave_de(a.clave_web, a.clave)
    plan = leer_plan(key, a.web)
    comp = {c['id']: c for c in plan.get('compromisos', [])}
    causas = {c['id']: c for c in plan.get('causas', [])}
    fuentes = plan.get('fuentes', [])
    L = ['Consolidación del plan semanal · ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    for ruta in a.archivos:
        try:
            d = json.load(open(ruta, encoding='utf8'))
        except Exception as ex:
            L.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(ruta), ex)); continue
        if d.get('app') != 'TabiFlowHCQ':
            L.append('⚠ %s: no es un archivo de TabiFlow HCQ' % os.path.basename(ruta)); continue
        nuevos = quitados = nc = 0
        for c in d.get('compromisos', []):
            ex = comp.get(c['id'])
            if ex is None:
                comp[c['id']] = c; nuevos += 1
            elif c.get('borrado') and not ex.get('borrado'):
                ex['borrado'] = True; ex['borradoTs'] = c.get('borradoTs'); quitados += 1
        for x in d.get('causas', []):
            ex = causas.get(x['id'])
            if ex is None or (x.get('ts') or '') > (ex.get('ts') or ''):
                causas[x['id']] = x; nc += 1
        fuentes.append({'archivo': os.path.basename(ruta), 'por': d.get('por'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s): %d compromisos nuevos, %d quitados, %d causas' % (os.path.basename(ruta), d.get('por'), nuevos, quitados, nc))
    plan['compromisos'] = list(comp.values()); plan['causas'] = list(causas.values()); plan['fuentes'] = fuentes[-500:]
    subs = set(plan.get('subcontratos', [])) | {c.get('sub') for c in comp.values() if c.get('sub') and not c.get('borrado')}
    plan['subcontratos'] = sorted(subs)
    guardar_plan(key, a.web, plan)
    por_sem = {}
    for c in comp.values():
        if not c.get('borrado'): por_sem[c['sem']] = por_sem.get(c['sem'], 0) + 1
    L += ['', 'Compromisos vigentes por semana: ' + (', '.join('%s: %d' % kv for kv in sorted(por_sem.items())) or '—'),
          'Subcontratos: ' + (', '.join(plan['subcontratos']) or '—')]
    print('\n'.join(L))

def sub_agregar(a):
    obra = a.clave
    key = clave_de(a.clave_web, obra)
    nombre = a.nombre.strip()
    sc = leer_subs(a.web)
    sc['subs'] = [s for s in sc['subs'] if s.get('n') != _huella(nombre)]
    clave_sub = 'sub-' + '-'.join(secrets.token_hex(2) for _ in range(3))
    salt = os.urandom(16)
    k = derivar(clave_sub, salt)
    sc['subs'].append({'n': _huella(nombre), 'salt': base64.b64encode(salt).decode(), 'iter': ITER,
                       'w': base64.b64encode(cifrar(k, {'pass': obra, 'sub': nombre})).decode()})
    json.dump(sc, open(os.path.join(a.web, 'subclaves.json'), 'w'))
    plan = leer_plan(key, a.web)
    plan['subcontratos'] = sorted(set(plan.get('subcontratos', [])) | {nombre})
    guardar_plan(key, a.web, plan)
    print('Subcontrato "%s" · clave: %s   (entrégala en persona; no la publiques)' % (nombre, clave_sub))

def _huella(nombre):
    import hashlib
    return hashlib.sha256(('tabiflow-sub|' + nombre.strip().lower()).encode('utf8')).hexdigest()[:12]

def sub_quitar(a):
    sc = leer_subs(a.web); n0 = len(sc['subs'])
    sc['subs'] = [s for s in sc['subs'] if s.get('n') != _huella(a.nombre)]
    json.dump(sc, open(os.path.join(a.web, 'subclaves.json'), 'w'))
    print('Claves quitadas: %d' % (n0 - len(sc['subs'])))

def sub_lista(a):
    key = clave_de(a.clave_web, a.clave)
    plan = leer_plan(key, a.web)
    hs = {s['n'] for s in leer_subs(a.web)['subs']}
    for n in plan.get('subcontratos', []):
        print(('🔑 ' if _huella(n) in hs else '   ') + n)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    for nom, fn in (('unir', unir), ('sub-agregar', sub_agregar), ('sub-quitar', sub_quitar), ('sub-lista', sub_lista)):
        p = sp.add_parser(nom); p.set_defaults(fn=fn)
        p.add_argument('--web', default='lastplanner'); p.add_argument('--clave-web', default='tabiflow')
        p.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE'))
        if nom == 'unir': p.add_argument('archivos', nargs='*')
        if nom in ('sub-agregar', 'sub-quitar'): p.add_argument('nombre')
    a = ap.parse_args()
    if not a.clave and a.cmd != 'sub-quitar': sys.exit('Falta la clave de obra (variable TABIFLOW_CLAVE)')
    a.fn(a)
