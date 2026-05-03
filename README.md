# Editor simple con Textual

Editor de texto en terminal con keybindings tipo Vim, paleta de comandos
fuzzy con autocompletado, modeline al estilo LazyVim y persistencia JSON
con `id` estable por línea. Panel lateral de archivos integrado.

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

| Archivo                                              | Responsabilidad                                                        |
| ---------------------------------------------------- | ---------------------------------------------------------------------- |
| [app.py](app.py)                                     | Composición, lifecycle, registro de comandos.                          |
| [editor_keybindings.py](editor_keybindings.py)       | Dispatcher Vim (modos, motion, verbos).                                |
| [editor_register.py](editor_register.py)             | Registro interno yank/paste.                                           |
| [editor_commands.py](editor_commands.py)             | Registro pluggable de comandos `:`.                                    |
| [editor_command_palette.py](editor_command_palette.py) | Modal con fuzzy + autocompletado + bridge ↓↑.                      |
| [editor_theme_picker.py](editor_theme_picker.py)     | Modal para elegir tema de color (21 integrados de Textual).           |
| [editor_themes.py](editor_themes.py)                 | Wrapper: toggle dark/light, lista de temas disponibles.               |
| [editor_layout.py](editor_layout.py)                 | Panel manager: registra/mostrar/ocultar/toggle paneles.               |
| [editor_panel_files.py](editor_panel_files.py)       | Panel izquierdo: árbol de archivos .json del vault.                   |
| [editor_rename.py](editor_rename.py)                 | Modal para renombrar el JSON.                                          |
| [editor_status.py](editor_status.py)                 | Modeline (mode chip + cursor + dirty + mensaje).                       |
| [editor_storage.py](editor_storage.py)               | Carga/guardado atómico + IDs de línea estables + list_documents.      |
| [editor_styles.py](editor_styles.py)                 | CSS del editor (variables de tema — sin paletas fijas).                |
| [config.yaml](config.yaml)                           | Configuración por usuario.                                             |
| [files/](files/)                                     | Vault: directorio con todos los documentos JSON.                       |
| [tests/](tests/)                                     | Pytest unitarios + Pilot integration.                                  |

## Modos

- `normal` (por defecto al arrancar): navegación + verbos Vim.
- `insert`: escribir texto normal. `i`, `a`, `I`, `A`, `o`, `O` entran.
- `visual`: selección por caracteres (`v`).
- `visual_line`: selección por líneas (`V`).

## Atajos

| Tecla                  | Acción                                                              |
| ---------------------- | ------------------------------------------------------------------- |
| `Esc`                  | Volver a normal.                                                    |
| `i` / `a` / `I` / `A`  | Entrar en insert (cursor / a la derecha / inicio / fin).            |
| `o` / `O`              | Línea nueva debajo / encima.                                         |
| `h` `j` `k` `l`        | Mover cursor.                                                       |
| `0` / `$`              | Inicio / fin de línea.                                              |
| `gg` / `G`             | Inicio / fin del documento.                                          |
| `w` `b` `e`            | Siguiente / anterior / fin de palabra.                              |
| `W` `B` `E`            | Igual pero con WORD (delimitada por blanco).                        |
| `dd`                   | Borrar línea (la copia al registro).                                |
| `yy`                   | Copiar línea al registro.                                           |
| `p` / `P`              | Pegar después / antes del cursor.                                   |
| `x`                    | Borrar carácter (lo copia al registro).                             |
| `u` / `Ctrl+R`         | Undo / redo.                                                        |
| `:`                    | Abrir paleta de comandos (fuzzy + autocompletado).                  |

En `visual` o `visual_line`: `y` copia la selección, `d` la corta. El
registro es interno; no toca el portapapeles del sistema.

## Hotkeys globales (footer)

| Tecla         | Acción                                      |
| ------------- | ------------------------------------------- |
| `Ctrl+P`      | Abrir paleta de comandos.                   |
| `Ctrl+S`      | Guardar el documento ahora.                 |
| `Ctrl+B`      | Mostrar / ocultar panel de archivos.        |
| `Ctrl+Q`      | Salir.                                      |

En terminales que reenvían `super` (Ghostty, Wezterm, iTerm2 con config),
también funciona `Cmd+B` además de `Ctrl+B`.

## Panel de archivos

El panel izquierdo muestra un árbol de los archivos `.json` dentro de
`files/` (el vault). Click en un archivo lo abre en el editor, guardando
primero cualquier cambio pendiente. El panel se muestra/oculta con
`Ctrl+B` o el comando `:pane-files-toggle`.

## Paleta de comandos

Pulsa `:` o `Ctrl+P` para abrir el modal. Escribe para filtrar; el input
muestra texto fantasma con autocompletado. Pulsa `→` (o `End`) para
aceptar el fantasma, `↓` para mover el foco a la lista, `Enter` para
ejecutar el primer match (o el resaltado si tienes el foco en la lista),
`Esc` para cancelar.

**Convención de nombres:** tres prefijos separan dominios distintos.

| Prefijo   | Dominio        | Ejemplos                                        |
| --------- | -------------- | ---------------------------------------------- |
| `theme-`  | Temas/color    | `theme-toggle`, `theme-pick`                   |
| `pane-`   | Layout/paneles | `pane-files-toggle`, `pane-files-show`         |
| `doc-`    | Documento I/O  | `doc-save`, `doc-rename`                       |

Comandos disponibles:

| Comando              | Descripción                                                     |
| -------------------- | --------------------------------------------------------------- |
| `theme-toggle`       | Alterna entre tema oscuro y claro (textual-dark / textual-light). |
| `theme-pick`         | Abre el selector visual de los 21 temas integrados de Textual.  |
| `doc-save`           | Guarda forzosamente ahora (también `Ctrl+S`).                   |
| `doc-rename`         | Renombra el archivo JSON en disco.                              |
| `pane-files-toggle`  | Muestra / oculta el panel de archivos.                          |
| `pane-files-show`    | Muestra el panel de archivos.                                   |
| `pane-files-hide`    | Oculta el panel de archivos.                                    |

Cada comando se enciende/apaga en [config.yaml](config.yaml) (`enabled`).

## Temas de color

El editor usa los 21 temas integrados de Textual. Cambiar tema repinta
todo automáticamente — fondo, borde, colores del editor, barra de
estado. Los temas disponibles incluyen:

`textual-dark` (por defecto), `textual-light`, `tokyo-night`, `nord`,
`dracula`, `gruvbox-dark`, `catppuccin-mocha`, `catppuccin-latte`,
`monokai`, `solarized-light`, `solarized-dark`, y más.

Usa `:theme-pick` para ver todos.

## Persistencia JSON

El vault vive en `files/`. Cada archivo `.json` es un documento; el
editor abre `files/document.json` al arrancar.

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
- `tests/test_storage.py` — load/save atómico, IDs estables, rename, list_documents.
- `tests/test_config.py` — merge + validación + warnings.
- `tests/test_word_motion.py` — w/b/e/W/B/E.
- `tests/test_command_palette.py` — Pilot: modal abre, filtra, selecciona.
- `tests/test_app_pilot.py` — Pilot end-to-end del editor completo.

## Ejecutar

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```