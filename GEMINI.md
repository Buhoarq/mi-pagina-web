# Indicaciones para Gemini en este repositorio

- **TabiFlow (carpeta `tabiflow/`)**: tu única tarea es consolidar los archivos de avance y publicar `tabiflow/avance.enc` y `tabiflow/adjuntos.enc` (fotos y notas), y para PaviFlow `paviflow/avance.enc`; con los mismos archivos de TabiFlow, el plan semanal en `lastplanner/plan.enc` (ver `tabiflow/herramientas/GEMINI.md`).
  Lee y sigue al pie de la letra **`tabiflow/herramientas/GEMINI.md`**.
- No modifiques ningún otro archivo del repositorio (la app, el panel, el modelo y las demás páginas los mantiene Claude).
- Antes de trabajar: `git pull --rebase`. Nunca `git push --force`.
- Nunca escribas la clave de obra en archivos ni commits.

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
