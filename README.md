# Editor simple con Textual

Editor de texto en terminal con keybindings tipo Vim, paleta de comandos
fuzzy con autocompletado, modeline al estilo LazyVim y persistencia JSON
con `id` estable por línea.

## Filosofía

Cada módulo declara en su docstring tres cosas:

1. **Scope** — qué hace.
2. **Boundaries** — qué NO hace y de qué depende.
3. **Freeze criteria** — cuándo puede considerarse "congelado" y dejar de
   tocarse para añadir features.

Esto sigue los cuatro principios conductuales (Karpathy): pensar antes de
codificar, simplicidad primero, cambios quirúrgicos, criterios de éxito
verificables.

## Módulos

| Archivo                                         | Responsabilidad                                                      |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| [app.py](app.py)                                | Composición, lifecycle, registro de comandos.                        |
| [editor_keybindings.py](editor_keybindings.py)  | Dispatcher Vim (modos, motion, verbos).                              |
| [editor_register.py](editor_register.py)        | Registro interno yank/paste.                                         |
| [editor_commands.py](editor_commands.py)        | Registro pluggable de comandos `:`.                                  |
| [editor_command_palette.py](editor_command_palette.py) | Modal con fuzzy + autocompletado + bridge ↓↑.                  |
| [editor_palettes.py](editor_palettes.py)        | Modal para escoger paleta de color.                                  |
| [editor_rename.py](editor_rename.py)            | Modal para renombrar el JSON.                                        |
| [editor_status.py](editor_status.py)            | Modeline (mode chip + cursor + dirty + mensaje).                     |
| [editor_storage.py](editor_storage.py)          | Carga/guardado atómico + IDs de línea estables.                      |
| [editor_styles.py](editor_styles.py)            | CSS + paletas + toggle claro/oscuro.                                 |
| [config.yaml](config.yaml)                      | Configuración por usuario.                                           |
| [document.json](document.json)                  | Documento persistido.                                                |
| [tests/](tests/)                                | Pytest unitarios + Pilot integration.                                |

## Modos

- `normal` (por defecto al arrancar): navegación + verbos Vim.
- `insert`: escribir texto normal. `i`, `a`, `I`, `A`, `o`, `O` entran.
- `visual`: selección por caracteres (`v`).
- `visual_line`: selección por líneas (`V`).

## Atajos

| Tecla                | Acción                                                |
| -------------------- | ----------------------------------------------------- |
| `Esc`                | Volver a normal.                                      |
| `i` / `a` / `I` / `A` | Entrar en insert (cursor / a la derecha / inicio / fin). |
| `o` / `O`            | Línea nueva debajo / encima.                          |
| `h` `j` `k` `l`      | Mover cursor.                                         |
| `0` / `$`            | Inicio / fin de línea.                                |
| `gg` / `G`           | Inicio / fin del documento.                           |
| `w` `b` `e`          | Siguiente / anterior / fin de palabra.                |
| `W` `B` `E`          | Igual pero con WORD (delimitada por blanco).          |
| `dd`                 | Borrar línea (la copia al registro).                  |
| `yy`                 | Copiar línea al registro.                             |
| `p` / `P`            | Pegar después / antes del cursor.                     |
| `x`                  | Borrar carácter (lo copia al registro).               |
| `u` / `Ctrl+R`       | Undo / redo.                                          |
| `:`                  | Abrir paleta de comandos (fuzzy + autocompletado).    |

En `visual` o `visual_line`: `y` copia la selección, `d` la corta. El
registro es interno; no toca el portapapeles del sistema.

## Hotkeys globales (footer)

| Tecla     | Acción                          |
| --------- | ------------------------------- |
| `Ctrl+P`  | Abrir paleta de comandos.       |
| `Ctrl+S`  | Guardar el documento ahora.     |
| `Ctrl+Q`  | Salir.                          |

## Paleta de comandos

Pulsa `:` o `Ctrl+P` para abrir el modal. Escribe para filtrar; el input
muestra texto fantasma con autocompletado. Pulsa `→` (o `End`) para
aceptar el fantasma, `↓` para mover el foco a la lista, `Enter` para
ejecutar el primer match (o el resaltado si tienes el foco en la lista),
`Esc` para cancelar.

Comandos incluidos:

- `light-dark-mode`: alterna claro / oscuro.
- `palette`: abre el selector de paletas (modal análogo).
- `rename`: renombra el archivo JSON en disco.
- `save`: guarda forzosamente (también con `Ctrl+S`).

Cada comando se enciende/apaga en [config.yaml](config.yaml) (`enabled`).

## Persistencia JSON

Cada línea se serializa como `{"id": "uuid", "text": "..."}`. Los IDs son
estables: una línea que no cambia conserva su id entre sesiones. La
escritura es atómica (archivo temporal + rename) para que un crash a
mitad de guardado no corrompa el documento.

## Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

Cobertura:

- `tests/test_register.py` — yank/paste linewise+charwise, edge cases.
- `tests/test_commands.py` — registry: registrar, fuzzy, ejecutar, errores.
- `tests/test_storage.py` — load/save atómico, IDs estables, rename.
- `tests/test_config.py` — merge + validación + warnings.
- `tests/test_word_motion.py` — w/b/e/W/B/E.
- `tests/test_command_palette.py` — Pilot: modal abre, filtra, selecciona.
- `tests/test_app_pilot.py` — Pilot end-to-end del editor completo.

## Ejecutar

```bash
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```
