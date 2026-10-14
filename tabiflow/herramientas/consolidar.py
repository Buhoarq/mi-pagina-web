#!/usr/bin/env python3
"""TabiFlow HCQ · consolidación diaria del avance de tabiques.

  python3 consolidar.py init --web DIR --clave CLAVE --modelo hcq_datos.json
      Crea clave.json, modelo.enc y un avance.enc vacío (cifrados con la clave de obra).

  python3 consolidar.py unir --web DIR --clave CLAVE archivo1.json archivo2.json ...
      Une los archivos de avance enviados por cada persona con el consolidado publicado,
      sin duplicar (cada registro tiene id único), y deja un reporte de diferencias.

Cifrado: AES-GCM 256, clave derivada con PBKDF2-SHA256 (compatible con WebCrypto de la app).
"""
import argparse, base64, gzip, json, os, sys, datetime, collections
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 250000
ETAPAS = ['est', 'c1', 'ais', 'c2']
NOMBRE = {'est': 'Estructura', 'c1': '1ª cara', 'ais': 'Aislación', 'c2': '2ª cara'}

def derivar(clave, salt):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(clave.encode('utf8'))

def cifrar(key, obj):
    datos = gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf8'), 9)
    iv = os.urandom(12)
    return iv + AESGCM(key).encrypt(iv, datos, None)

def descifrar(key, buf):
    return json.loads(gzip.decompress(AESGCM(key).decrypt(buf[:12], buf[12:], None)).decode('utf8'))

def clave_de(web, clave):
    info = json.load(open(os.path.join(web, 'clave.json')))
    key = derivar(clave, base64.b64decode(info['salt']))
    descifrar(key, base64.b64decode(info['check']))  # valida la clave
    return key

def init(a):
    salt = os.urandom(16)
    key = derivar(a.clave, salt)
    info = {'salt': base64.b64encode(salt).decode(), 'iter': ITER, 'check': base64.b64encode(cifrar(key, {'ok': True})).decode()}
    json.dump(info, open(os.path.join(a.web, 'clave.json'), 'w'))
    modelo = json.load(open(a.modelo, encoding='utf8'))
    open(os.path.join(a.web, 'modelo.enc'), 'wb').write(cifrar(key, modelo))
    vacio = {'actualizado': None, 'eventos': [], 'jornadas': [], 'personas': [], 'fuentes': []}
    open(os.path.join(a.web, 'avance.enc'), 'wb').write(cifrar(key, vacio))
    print('listo: clave.json, modelo.enc (%.2f MB), avance.enc' % (os.path.getsize(os.path.join(a.web, 'modelo.enc')) / 1e6))

def unir(a):
    key = clave_de(a.web, a.clave)
    base = descifrar(key, open(os.path.join(a.web, 'avance.enc'), 'rb').read())
    modelo = descifrar(key, open(os.path.join(a.web, 'modelo.enc'), 'rb').read())
    tab = {t['g']: (n['id'], t) for n in modelo['niveles'] for t in n['tab']}
    eventos = {e['id']: e for e in base.get('eventos', [])}
    jornadas = {j['id']: j for j in base.get('jornadas', [])}
    fuentes = base.get('fuentes', [])
    vistos = {f.get('firma') for f in fuentes}
    resumen = []
    for ruta in a.archivos:
        try:
            d = json.load(open(ruta, encoding='utf8'))
        except Exception as ex:
            resumen.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(ruta), ex)); continue
        if d.get('app') != 'TabiFlowHCQ':
            resumen.append('⚠ %s: no es un archivo de TabiFlow HCQ' % os.path.basename(ruta)); continue
        por = (d.get('por') or '').strip() or '—'
        nuevos = borrados = ignorados = 0
        for e in d.get('eventos', []):
            e.pop('_base', None)
            if e.get('g') not in tab or e.get('et') not in ETAPAS:
                ignorados += 1; continue
            e['por'] = e.get('por') or por
            ex = eventos.get(e['id'])
            if ex is None:
                eventos[e['id']] = e; nuevos += 1
                if e.get('borrado'): borrados += 1
            elif e.get('borrado') and not ex.get('borrado'):
                ex['borrado'] = True; ex['borradoTs'] = e.get('borradoTs'); borrados += 1
        for j in d.get('jornadas', []):
            jid = j['id'].split('|')[0] + '|' + (j.get('por') or por)
            j = dict(j, id=jid, por=j.get('por') or por)
            ex = jornadas.get(jid)
            if ex is None or (j.get('cerrada') and not ex.get('cerrada')) or len(j.get('log', [])) > len(ex.get('log', [])):
                jornadas[jid] = j
        firma = '%s|%s|%s' % (por, d.get('disp'), d.get('exportado'))
        if firma not in vistos:
            fuentes.append({'archivo': os.path.basename(ruta), 'por': por, 'disp': d.get('disp'), 'exportado': d.get('exportado'), 'firma': firma})
            vistos.add(firma)
        resumen.append('✓ %s (%s): %d registros nuevos, %d anulados%s' % (os.path.basename(ruta), por, nuevos, borrados, (', %d ignorados (tabique inexistente)' % ignorados) if ignorados else ''))

    vig = [e for e in eventos.values() if not e.get('borrado')]
    # ---- duplicados y diferencias (solo informativo: la app ya cuenta cada tabique y etapa una vez) ----
    por_ge = collections.defaultdict(list)
    for e in vig: por_ge[(e['g'], e['et'])].append(e)
    confirmados = [(k, v) for k, v in por_ge.items() if len({x.get('por') for x in v}) > 1]
    por_gd = collections.defaultdict(lambda: collections.defaultdict(int))
    for e in vig:
        if not e.get('auto'):
            por_gd[(e['g'], e['dia'])][e.get('por')] = max(por_gd[(e['g'], e['dia'])][e.get('por')], ETAPAS.index(e['et']))
    difs = [(k, v) for k, v in por_gd.items() if len(set(v.values())) > 1]
    # ---- totales ----
    mejor = {}
    for e in vig:
        k = (e['g'], e['et'])
        if k not in mejor or e['f'] > mejor[k]: mejor[k] = e['f']
    tot = collections.defaultdict(float); tot_n = collections.defaultdict(float)
    tot_modelo = collections.defaultdict(float)
    for g, (nv, t) in tab.items(): tot_modelo[nv] += t['A']
    for (g, et), f in mejor.items():
        nv, t = tab[g]; tot[(nv, et)] += t['A'] * f
    personas = sorted({e.get('por') or '—' for e in vig})
    ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
    salida = {'actualizado': ahora, 'eventos': list(eventos.values()), 'jornadas': list(jornadas.values()), 'personas': personas, 'fuentes': fuentes,
              'dotacion': base.get('dotacion', {}), 'config': base.get('config', {})}
    open(os.path.join(a.web, 'avance.enc'), 'wb').write(cifrar(key, salida))

    # ---- reporte para Renato ----
    def rec(g):
        nv, t = tab[g]; return '%s · %s · %s' % (nv, t['t'], ' / '.join(t['r'][:2]) or 'sin recinto')
    L = ['# Consolidación TabiFlow HCQ — %s' % datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    L += ['## Archivos procesados'] + ['- ' + r for r in resumen] + ['']
    L += ['## Avance acumulado (m², sin duplicar)', '', '| Nivel | m² modelo | ' + ' | '.join(NOMBRE[e] for e in ETAPAS) + ' |', '|---|---:|' + '---:|' * 4]
    for n in modelo['niveles']:
        nv = n['id']
        L.append('| %s | %.0f | ' % (nv, tot_modelo[nv]) + ' | '.join('%.0f (%.1f%%)' % (tot[(nv, e)], 100 * tot[(nv, e)] / tot_modelo[nv] if tot_modelo[nv] else 0) for e in ETAPAS) + ' |')
    L += ['', 'Registros vigentes: %d · personas: %s' % (len(vig), ', '.join(personas) or '—'), '']
    L += ['## Tabiques marcados por más de una persona (se cuentan una sola vez): %d' % len(confirmados)]
    for (g, et), v in sorted(confirmados, key=lambda x: x[0])[:60]:
        L.append('- %s — %s: %s' % (rec(g), NOMBRE[et], ', '.join('%s %s %d%%' % (x.get('por'), x['dia'][5:], round(x['f'] * 100)) for x in sorted(v, key=lambda x: x['ts']))))
    L += ['', '## Diferencias a revisar en terreno (mismo tabique y día, distinta etapa): %d' % len(difs)]
    for (g, dia), v in sorted(difs, key=lambda x: x[0][1])[:80]:
        L.append('- %s · %s — %s' % (dia, rec(g), ', '.join('%s: %s' % (p, NOMBRE[ETAPAS[i]]) for p, i in v.items())))
    # ---- incoherencias: etapa posterior con más % que una anterior ----
    inc = []
    for g in {e['g'] for e in vig}:
        mx = 0; bad = False
        for et in reversed(ETAPAS):
            f = mejor.get((g, et), 0)
            if f + 1e-9 < mx: bad = True
            mx = max(mx, f)
        if bad: inc.append(g)
    L += ['', '## Incoherencias (etapa posterior con más %% que una anterior): %d' % len(inc)]
    for g in inc[:80]:
        L.append('- %s — %s' % (rec(g), ' · '.join('%s %d%%' % (NOMBRE[e], round(mejor.get((g, e), 0) * 100)) for e in ETAPAS)))
    dot = base.get('dotacion', {})
    if dot:
        L += ['', '## Dotación registrada (últimos 14 días)'] + ['- %s: %s tabiqueros' % (k, dot[k].get('n')) for k in sorted(dot)[-14:]]
    rep = '\n'.join(L)
    if a.reporte:
        open(a.reporte, 'w', encoding='utf8').write(rep)
    print(rep)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    i = sp.add_parser('init'); i.add_argument('--web', required=True); i.add_argument('--clave', required=True); i.add_argument('--modelo', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave', required=True); u.add_argument('--reporte'); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    {'init': init, 'unir': unir}[a.cmd](a)
