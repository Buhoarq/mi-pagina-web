#!/usr/bin/env python3
"""TabiFlow HCQ · consolidación diaria del avance de tabiques.

  python3 tabiflow/herramientas/consolidar.py unir --web tabiflow archivo1.json archivo2.json ...
      (la clave de obra se toma de la variable de entorno TABIFLOW_CLAVE; nunca la escribas en el repositorio)
      Une los archivos de avance enviados por cada persona con el consolidado publicado,
      sin duplicar (cada registro tiene id único), y deja un reporte de diferencias.

Cifrado: AES-GCM 256, clave derivada con PBKDF2-SHA256 (compatible con WebCrypto de la app).
"""
import argparse, base64, gzip, json, os, sys, datetime, collections
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 250000
_m = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mapa_migracion.json')
MAPA = json.load(open(_m)) if os.path.exists(_m) else {}
ETAPAS = ['est', 'c1p1', 'c1p2', 'c1p3', 'pb', 'ais', 'c2p1', 'c2p2', 'c2p3', 'fen']
NOMBRE = {'est': 'Estructura', 'c1p1': 'C1·P1', 'c1p2': 'C1·P2', 'c1p3': 'C1·P3', 'pb': 'Plomo', 'ais': 'Aislación',
          'c2p1': 'C2·P1', 'c2p2': 'C2·P2', 'c2p3': 'C2·P3', 'fen': 'Fenólico',
          'c1': 'Cara 1', 'c2': 'Cara 2'}
FAMS = ['est', 'c1', 'pb', 'ais', 'c2', 'fen']
FAM = {'est': 'est', 'c1p1': 'c1', 'c1p2': 'c1', 'c1p3': 'c1', 'pb': 'pb', 'ais': 'ais', 'c2p1': 'c2', 'c2p2': 'c2', 'c2p3': 'c2', 'fen': 'fen'}

def seq_de(t):
    """Etapas del tabique según su tipo: placas por cara (np) y plomo (pb). np=0 → separador fenólico."""
    if not t.get('np'):
        return ['fen']
    s = ['est'] + ['c1p%d' % i for i in range(1, t['np'] + 1)] + (['pb'] if t.get('pb') else []) + ['ais'] + ['c2p%d' % i for i in range(1, t['np'] + 1)]
    return s

def normalizar(e, tab, tramos):
    """Registros de versiones anteriores: 'c1'/'c2' → todas las placas de esa cara; GUID de un tabique dividido → cada tramo."""
    gs = [e['g']] if e['g'] in tab else tramos.get(e['g'], [])
    out = []
    for i, g in enumerate(gs):
        sq = tab[g][1]['seq']
        ets = [x for x in sq if x.startswith(e['et'] + 'p')] if e['et'] in ('c1', 'c2') else [e['et']]
        for et in ets:
            if et not in sq: continue
            x = dict(e)
            if len(gs) > 1 or len(ets) > 1 or g != e['g']:
                x['id'] = e['id'] + ('.%d' % (i + 1) if len(gs) > 1 else '') + ('.' + et if (len(ets) > 1 or et != e['et']) else '')
                x['g'] = g; x['et'] = et
            out.append(x)
    return out

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
    tramos = {}
    for g, (nv, t) in tab.items():
        t['seq'] = seq_de(t)
        if t.get('gb'): tramos.setdefault(t['gb'], []).append(g)
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
        lista = []
        for e in d.get('eventos', []):
            # registros hechos sobre el modelo anterior (GUID que ya no existe): se llevan al tabique nuevo
            if e.get('g') not in tab and e.get('g') not in tramos and e.get('g') in MAPA:
                for h in MAPA[e['g']]:
                    sq = tab[h][1]['seq']; et = e.get('et')
                    if et not in sq and str(et)[:3] in ('c1p', 'c2p') and tab[h][1]['np']: et = et[:3] + str(tab[h][1]['np'])
                    if et in sq: lista.append(dict(e, g=h, et=et, id=e['id'] + '~' + h[-6:] + '.' + et, mig={'g': e['g'], 'et': e.get('et'), 'v': 'mapa'}))
                continue
            lista.append(e)
        for e in lista:
            e.pop('_base', None)
            if (e.get('g') not in tab and e.get('g') not in tramos) or e.get('et') not in ETAPAS + ['c1', 'c2']:
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

    vig = [x for e in eventos.values() if not e.get('borrado') for x in normalizar(e, tab, tramos)]
    # ---- duplicados y diferencias (solo informativo: la app ya cuenta cada tabique y etapa una vez) ----
    por_ge = collections.defaultdict(list)
    for e in vig: por_ge[(e['g'], e['et'])].append(e)
    confirmados = [(k, v) for k, v in por_ge.items() if len({x.get('por') for x in v}) > 1]
    por_gd = collections.defaultdict(lambda: collections.defaultdict(int))
    for e in vig:
        if not e.get('auto'):
            por_gd[(e['g'], e['dia'])][e.get('por')] = max(por_gd[(e['g'], e['dia'])][e.get('por')], tab[e['g']][1]['seq'].index(e['et']))
    difs = [(k, v) for k, v in por_gd.items() if len(set(v.values())) > 1]
    # ---- totales ----
    mejor = {}
    for e in vig:
        k = (e['g'], e['et'])
        if k not in mejor or e['f'] > mejor[k]: mejor[k] = e['f']
    # por familia: cara 1 / cara 2 = promedio de sus placas; denominador = tabiques que tienen esa familia
    tot = collections.defaultdict(float); tot_n = collections.defaultdict(float)
    tot_modelo = collections.defaultdict(float); tot_fam = collections.defaultdict(float)
    for g, (nv, t) in tab.items():
        tot_modelo[nv] += t['A']
        fams = collections.defaultdict(list)
        for et in t['seq']: fams[FAM[et]].append(et)
        for fm, ets in fams.items():
            tot_fam[(nv, fm)] += t['A']
            f = sum(mejor.get((g, et), 0) for et in ets) / len(ets)
            tot[(nv, fm)] += t['A'] * f
    personas = sorted({e.get('por') or '—' for e in vig})
    ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
    salida = {'actualizado': ahora, 'eventos': list(eventos.values()), 'jornadas': list(jornadas.values()), 'personas': personas, 'fuentes': fuentes,
              'dotacion': base.get('dotacion', {}), 'config': base.get('config', {})}
    open(os.path.join(a.web, 'avance.enc'), 'wb').write(cifrar(key, salida))

    # ---- reporte para Renato ----
    def rec(g):
        nv, t = tab[g]; return '%s · %s%s · %s' % (nv, t['t'], (' tramo %d/%d' % (t['tr'], t['ntr'])) if t.get('tr') else '', ' / '.join(t['r'][:2]) or 'sin recinto')
    L = ['# Consolidación TabiFlow HCQ — %s' % datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    L += ['## Archivos procesados'] + ['- ' + r for r in resumen] + ['']
    L += ['## Avance acumulado (m², sin duplicar)', '', '| Nivel | m² modelo | ' + ' | '.join(NOMBRE.get(e, e) if e not in ('pb','fen','est','ais') else NOMBRE[e] for e in FAMS) + ' |', '|---|---:|' + '---:|' * len(FAMS)]
    for n in modelo['niveles']:
        nv = n['id']
        L.append('| %s | %.0f | ' % (nv, tot_modelo[nv]) + ' | '.join(('%.0f (%.1f%%)' % (tot[(nv, e)], 100 * tot[(nv, e)] / tot_fam[(nv, e)])) if tot_fam[(nv, e)] else '·' for e in FAMS) + ' |')
    L += ['', 'Registros vigentes: %d · personas: %s' % (len(vig), ', '.join(personas) or '—'), '']
    L += ['## Tabiques marcados por más de una persona (se cuentan una sola vez): %d' % len(confirmados)]
    for (g, et), v in sorted(confirmados, key=lambda x: x[0])[:60]:
        L.append('- %s — %s: %s' % (rec(g), NOMBRE[et], ', '.join('%s %s %d%%' % (x.get('por'), x['dia'][5:], round(x['f'] * 100)) for x in sorted(v, key=lambda x: x['ts']))))
    L += ['', '## Diferencias a revisar en terreno (mismo tabique y día, distinta etapa): %d' % len(difs)]
    for (g, dia), v in sorted(difs, key=lambda x: x[0][1])[:80]:
        L.append('- %s · %s — %s' % (dia, rec(g), ', '.join('%s: %s' % (p, NOMBRE[tab[g][1]['seq'][i]]) for p, i in v.items())))
    # ---- incoherencias: etapa posterior con más % que una anterior ----
    inc = []
    for g in {e['g'] for e in vig}:
        sq = tab[g][1]['seq']
        # requisito: etapa anterior, salvo la aislación que solo requiere C1·P1
        pre = {et: ('c1p1' if et == 'ais' and 'c1p1' in sq else sq[i - 1]) for i, et in enumerate(sq) if i > 0}
        if any(mejor.get((g, et), 0) > mejor.get((g, p), 0) + 1e-9 for et, p in pre.items()): inc.append(g)
    L += ['', '## Incoherencias (etapa posterior con más %% que una anterior): %d' % len(inc)]
    for g in inc[:80]:
        L.append('- %s — %s' % (rec(g), ' · '.join('%s %d%%' % (NOMBRE[e], round(mejor.get((g, e), 0) * 100)) for e in tab[g][1]['seq'])))
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
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('--reporte'); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra: defínela en la variable de entorno TABIFLOW_CLAVE (no la escribas en el repositorio).')
    unir(a)
