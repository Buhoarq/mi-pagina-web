# TabiFlow · Instrucciones para Gemini (consolidar el avance)

Proyecto: **TabiFlow — Hospital de Coquimbo** (app de avance de tabiques). Autor: Renato Martínez Palominos.
Tu tarea es **solo una**: unir los archivos de avance que te entregue Renato y publicar el consolidado.

## Reglas (obligatorias)

1. **Solo puedes modificar `tabiflow/avance.enc`, `tabiflow/adjuntos.enc`, `paviflow/avance.enc`, `hormiflow/avance.enc` y `lastplanner/plan.enc`** (este último guarda las fotos y notas, desde la v5.0). No toques `index.html`, `panel.html`, `sw.js`,
   `modelo.enc`, `clave.json`, ni nada en `tabiflow/herramientas/`. Esos archivos los mantiene Claude.
   Si algo de eso parece necesitar cambios, avísale a Renato en vez de cambiarlo.
2. **Nunca escribas la clave de obra** en ningún archivo, commit, mensaje de commit ni log.
   Se usa solo como variable de entorno `TABIFLOW_CLAVE` durante la sesión.
3. **Nunca subas** los archivos `Avance_*.json`, reportes ni archivos descifrados al repositorio
   (contienen nombres y datos de la obra). Trabaja con ellos fuera del repositorio o en una carpeta ignorada.
4. **Antes de trabajar, baja siempre lo último:** `git pull --rebase`.
   Si al subir hay conflicto en `avance.enc`, **no lo resuelvas a mano**: vuelve a hacer `git pull --rebase`
   (descartando tu `avance.enc`) y repite la consolidación desde el paso 3.
5. No uses `git push --force` ni reescribas el historial.

## Pasos cada vez que Renato te pase archivos `Avance_*.json`

1. Ubícate en la raíz del repositorio `mi-pagina-web` y baja lo último:
   ```bash
   git pull --rebase
   ```
2. Requisito (una vez): `pip install cryptography`
3. Pide a Renato la clave de obra (si no la tienes en esta sesión) y defínela solo en el entorno:
   ```bash
   export TABIFLOW_CLAVE='(la clave que te dé Renato)'
   ```
4. Guarda los archivos recibidos en una carpeta **fuera** del repositorio (por ejemplo `../avances_recibidos/`) y consolida:
   ```bash
   python3 tabiflow/herramientas/consolidar.py unir --web tabiflow ../avances_recibidos/Avance_*.json
   ```
   El script:
   - une los registros sin duplicar (cada registro tiene un id único; si un archivo se envía dos veces no cambia nada),
   - lleva al modelo nuevo los registros hechos con el modelo anterior (usa `mapa_migracion.json`),
   - conserva la ponderación y la dotación ya publicadas,
   - une las fotos y notas por tabique (desde la v5.0): el índice queda en `avance.enc` y las imágenes en `adjuntos.enc`,
   - reescribe `tabiflow/avance.enc` y `tabiflow/adjuntos.enc` (cifrados) e imprime un reporte.
5. Revisa el reporte. Si dice `⚠` en algún archivo (no es de TabiFlow o no se pudo leer), avísale a Renato.
6. Sube **solo** el avance y las fotos:
   ```bash
   git add tabiflow/avance.enc tabiflow/adjuntos.enc
   git commit -m "Avance consolidado DD/MM/AAAA (nombres de quienes enviaron)"
   git push
   ```
   Verifica con `git status` que no quedó ningún otro archivo agregado.
7. Entrégale a Renato un resumen corto, sacado del reporte:
   - archivos procesados y registros nuevos/anulados por persona, y fotos/notas nuevas,
   - tabla de m² y % por nivel (solo los niveles con avance),
   - cantidad de **tabiques marcados por más de una persona** (se cuentan una vez),
   - **diferencias a revisar en terreno** (mismo tabique y día, distinta etapa),
   - **incoherencias** (una etapa con más % que la que la precede; la aislación solo exige la 1ª placa de la cara 1).

Los celulares y el panel ven el avance nuevo 1–2 minutos después del `git push` (GitHub Pages).

## Si algo sale mal

- **Un archivo anterior al 16-10-2026 aparece con "registros nuevos" pero los m² no cambian** → es normal: son registros del modelo
  anterior que se reacomodaron al modelo nuevo; no suman dos veces.

- **"Falta la clave de obra"** → define `TABIFLOW_CLAVE`.
- **Error al descifrar (InvalidTag)** → la clave es incorrecta. No sigas; pregúntale a Renato.
- **Registros "ignorados (tabique inexistente)"** → el archivo trae tabiques que no están en el modelo actual
  (por ejemplo, de un celular con una versión muy antigua). Infórmalo a Renato con el nombre del archivo.
- Ante cualquier duda, **no publiques** y consulta a Renato.

## PaviFlow (pavimentos) · desde el 16-10-2026

Los archivos que empiezan con `Avance_PaviFlow_` son del módulo de pavimentos. Se consolidan aparte y solo tocan `paviflow/avance.enc`:

```bash
python3 tabiflow/herramientas/consolidar_pavi.py unir --web paviflow --clave-web tabiflow ../avances_recibidos/Avance_PaviFlow_*.json
git add paviflow/avance.enc
git commit -m "Avance PaviFlow consolidado DD/MM/AAAA (nombres)"
git push
```
Usa la misma `TABIFLOW_CLAVE`. Nunca mezcles archivos de PaviFlow con el comando de TabiFlow (o al revés): cada script avisa con ⚠ si un archivo no le corresponde.

## Plan semanal (página Last Planner, `lastplanner/`) · desde el 17-10-2026

Los jefes de terreno envían archivos `Avance_Plan_….json` con **compromisos** y **causas** del plan semanal (no traen avance).
Después de consolidar el avance de TabiFlow como siempre, pasa **los mismos archivos** por este comando (solo toca `lastplanner/plan.enc`):

```bash
python3 tabiflow/herramientas/consolidar_plan.py unir --web lastplanner ../avances_recibidos/Avance_*.json
git add lastplanner/plan.enc
git commit -m "Plan semanal consolidado DD/MM/AAAA (nombres)"
git push
```
Los archivos `Avance_Plan_….json` de los jefes de terreno solo traen compromisos y causas (sin avance); pásalos también por este comando. Los archivos `Avance_PaviFlow_` el script los rechaza con ⚠.

---
© 2026 Renato Martínez Palominos – Todos los derechos reservados.

## PuertaFlow (puertas) · desde el 19-10-2026

Los archivos que empiezan con `Avance_PuertaFlow_` son del módulo de puertas. Se consolidan aparte y solo tocan `puertaflow/avance.enc`:

```bash
python3 tabiflow/herramientas/consolidar_puerta.py unir --web puertaflow --clave-web tabiflow ../avances_recibidos/Avance_PuertaFlow_*.json
git add puertaflow/avance.enc
git commit -m "Avance PuertaFlow consolidado DD/MM/AAAA (nombres)"
git push
```
Usa la misma `TABIFLOW_CLAVE`. `puertaflow/avance.enc` se suma a la lista de archivos que puedes modificar; no toques `puertaflow/puertas.enc` (es el modelo de puertas y lo mantiene Claude).

## PuertaFlow · Coordinación de refuerzos · desde el 19-10-2026

Los archivos que empiezan con `Coord_PuertaFlow_` son tickets de coordinación (trazadores, subcontrato de refuerzos y obra). Se consolidan aparte y solo tocan `puertaflow/coordavance.enc`:

```bash
python3 tabiflow/herramientas/consolidar_coord.py unir --web puertaflow --clave-web tabiflow ../avances_recibidos/Coord_PuertaFlow_*.json
git add puertaflow/coordavance.enc
git commit -m "Coordinación PuertaFlow consolidada DD/MM/AAAA (nombres)"
git push
```
Usa la misma `TABIFLOW_CLAVE`. `puertaflow/coordavance.enc` se suma a los archivos que puedes modificar; no toques `coord.enc` ni `coord_acceso.json` (los mantiene Claude).

Desde el 19-10-2026 el mismo comando también guarda las fotos de los tickets (interferencias para RDI) en `puertaflow/coordfotos.enc`. Súbelo junto a `coordavance.enc`:
```bash
git add puertaflow/coordavance.enc puertaflow/coordfotos.enc
```

## HormiFlow (hormigón armado) · desde el 20-10-2026

Los archivos que empiezan con `Avance_HormiFlow_` se consolidan aparte y solo tocan `hormiflow/avance.enc`:

```bash
python3 tabiflow/herramientas/consolidar_hormi.py unir --web hormiflow --clave-web tabiflow ../avances_recibidos/Avance_HormiFlow_*.json
git add hormiflow/avance.enc
git commit -m "Avance HormiFlow consolidado DD/MM/AAAA (nombres)"
git push
```

Desde la v0.2 cada envío llega con dos archivos: el `.json` (el único que se consolida) y un `Resumen_HormiFlow_….pdf` (solo para leer; no se procesa). Usa la misma `TABIFLOW_CLAVE`. No toques `hormiflow/hormi.enc` (lo mantiene Claude). Copia `consolidar_hormi.py` a `tabiflow/herramientas/` si aún no está.

## Publicar también en flujoplan.cl (desde el 25-10-2026) — OBLIGATORIO en cada consolidación

Mientras se migra, el avance se publica en **los dos sitios**: la página de GitHub (`mi-pagina-web`, donde ya trabajas) y **flujoplan.cl** (repositorio `Buhoarq/flujoplan`, privado; Firebase se actualiza solo al hacer push).
Después de cada `git push` en `mi-pagina-web`, copia **los mismos archivos de avance** a la carpeta `publicar/hcq/` del repositorio `flujoplan` (misma ruta) y súbelos:

```bash
# una vez: git clone https://github.com/Buhoarq/flujoplan.git ../flujoplan   (al lado de mi-pagina-web)
cd ../flujoplan && git pull --rebase
for f in tabiflow/avance.enc tabiflow/adjuntos.enc paviflow/avance.enc hormiflow/avance.enc lastplanner/plan.enc \
         puertaflow/avance.enc puertaflow/coordavance.enc puertaflow/coordfotos.enc ventanaintflow/avance.enc ventanaintflow/fotos.enc; do
  [ -f ../mi-pagina-web/$f ] && cp ../mi-pagina-web/$f publicar/hcq/$f
done
git add publicar/hcq/*/avance.enc publicar/hcq/tabiflow/adjuntos.enc publicar/hcq/lastplanner/plan.enc publicar/hcq/puertaflow/coord*.enc publicar/hcq/ventanaintflow/fotos.enc
git status          # solo deben aparecer archivos .enc de avance
git commit -m "Avance consolidado DD/MM/AAAA (nombres) · copia de mi-pagina-web"
git push
cd ../mi-pagina-web
```

Mismas reglas: solo esos archivos `.enc`, nunca la clave ni archivos descifrados, sin `--force`. Si `git status` muestra cualquier otro archivo, no lo subas y avísale a Renato.
(El panel de TabiFlow y VentanaIntFlow ya publican solos en los dos sitios; si Renato publicó desde ahí, el `cp` no cambia nada.)
