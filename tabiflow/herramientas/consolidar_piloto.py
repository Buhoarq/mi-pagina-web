#!/usr/bin/env python3
"""PilotoFlow (FlujoPlan) · une los archivos Avance_PilotoFlow_*.json en pilotoflow/avance.enc (registros sin fotos)
y pilotoflow/fotos.enc (fotos de la bitácora, clave «id#n», aparte para que el avance sea liviano).
Misma regla que el botón «Publicar» de la app: por id de registro; un registro anulado anula el publicado.
Uso (desde la raíz del repositorio):
  python3 herramientas/consolidar_piloto.py unir --web publicar/hcq/pilotoflow --clave-web publicar/hcq/tabiflow ../recibidos/Avance_PilotoFlow_*.json
La clave de obra se toma de la variable de entorno TABIFLOW_CLAVE (nunca la escribas en el repositorio).
© 2026 Renato Martínez Palominos – Todos los derechos reservados."""
import argparse, json, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consolidar import clave_de, cifrar, descifrar
KINDS = ('av', 'fr', 'bit', 'tema', 'mat')
def unir(a):
    key = clave_de(a.clave_web, a.clave)
    prog = descifrar(key, open(os.path.join(a.web, 'piloto.enc'), 'rb').read())
    tareas = {t['id']: t for t in prog['tareas']}
    ruta, rutaf = os.path.join(a.web, 'avance.enc'), os.path.join(a.web, 'fotos.enc')
    base = descifrar(key, open(ruta, 'rb').read()) if os.path.exists(ruta) else {'eventos': []}
    fotos = descifrar(key, open(rutaf, 'rb').read()).get('fotos', {}) if os.path.exists(rutaf) else {}
    ev = {e['id']: e for e in base.get('eventos', [])}
    personas = set(base.get('personas', [])); fuentes = list(base.get('fuentes', []))
    L = ['Consolidación PilotoFlow · ' + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), '']
    for f in a.archivos:
        try: d = json.load(open(f, encoding='utf8'))
        except Exception as e: L.append('⚠ %s: no se pudo leer (%s)' % (os.path.basename(f), e)); continue
        if d.get('app') != 'PilotoFlowHCQ': L.append('⚠ %s: no es un archivo de PilotoFlow' % os.path.basename(f)); continue
        n = collections.Counter(); anul = 0
        for e in d.get('eventos', []):
            if e.get('k') not in KINDS: continue
            x = ev.get(e['id'])
            if x is None:
                if e.get('borrado'): continue
                e = dict(e)
                for k in ('enviado', 'recibido', 'publicado'): e.pop(k, None)
                fs = e.pop('f', None) or []
                for i, u in enumerate(fs): fotos[e['id'] + '#' + str(i)] = u
                if fs: e['nf'] = len(fs)
                ev[e['id']] = e; n[e['k']] += 1
                if e.get('por'): personas.add(e['por'])
            elif e.get('borrado') and not x.get('borrado'): x['borrado'] = True; x['borradoTs'] = e.get('borradoTs'); anul += 1
        fuentes.append({'archivo': os.path.basename(f), 'por': d.get('persona'), 'exportado': d.get('exportado')})
        L.append('- ✓ %s (%s): %s%s' % (os.path.basename(f), d.get('persona'), ', '.join('%d %s' % (v, {'av': 'avances', 'fr': 'fechas reales', 'bit': 'registros de bitácora', 'tema': 'temas', 'mat': 'materiales'}[k]) for k, v in n.items()) or 'sin registros nuevos', (', %d anulados' % anul) if anul else ''))
    # resumen: % vigente de las tareas con registro
    ult = {}
    for e in ev.values():
        if e.get('borrado') or e['k'] != 'av': continue
        o = ult.get(e['t'])
        if o is None or e['ts'] > o['ts']: ult[e['t']] = e
    L += ['', 'Registros vigentes: %d · fotos: %d · personas: %s' % (sum(1 for e in ev.values() if not e.get('borrado')), len(fotos), ', '.join(sorted(personas)) or '—'), '',
          '| Tarea | % | Por | Fecha |', '|---|---:|---|---|']
    for t, e in sorted(ult.items(), key=lambda x: x[1]['ts'], reverse=True)[:40]:
        L.append('| %s | %.0f %% | %s | %s |' % (tareas.get(t, {}).get('n', t), 100 * float(e['v']), e.get('por', ''), e.get('dia', '')))
    ahora = datetime.datetime.now().astimezone().isoformat()
    open(ruta, 'wb').write(cifrar(key, {'modulo': 'piloto', 'piloto': prog['piloto']['id'], 'actualizado': ahora, 'eventos': list(ev.values()), 'personas': sorted(personas), 'fuentes': fuentes}))
    open(rutaf, 'wb').write(cifrar(key, {'modulo': 'piloto', 'actualizado': ahora, 'fotos': fotos}))
    print('\n'.join(L))
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('unir'); u.add_argument('--web', required=True); u.add_argument('--clave-web', default='tabiflow')
    u.add_argument('--clave', default=os.environ.get('TABIFLOW_CLAVE')); u.add_argument('archivos', nargs='*')
    a = ap.parse_args()
    if not a.clave: sys.exit('Falta la clave de obra: defínela en la variable de entorno TABIFLOW_CLAVE.')
    unir(a)
