# Medlang

Editor de texto en terminal con keybindings tipo Vim, paleta de comandos
fuzzy con autocompletado, modeline al estilo LazyVim, leader key
(WhichKey) y persistencia JSON con `id` estable por línea. Panel
lateral de archivos integrado.

Construido sobre [Textual 8.x](https://textual.textualize.io/).

## Filosofía

Cada módulo declara en su docstring tres cosas:

1. **Scope** — qué hace.
2. **Boundaries** — qué NO hace y de qué depende.
3. **Freeze criteria** — cuándo puede considerarse "congelado" y dejar de
   tocarse para añadir features.

Esto sigue los cuatro principios conductuales (Karpathy): pensar antes
de codificar, simplicidad primero, cambios quirúrgicos, criterios de
éxito verificables.

## Estructura

```
medlang/
├── app.py                  composición + lifecycle
├── config.py               carga + validación de config.yaml
├── styles.tcss             CSS global (theme variables)
├── messages.py             mensajes Textual custom
├── commands.py             registro pluggable de comandos
├── storage.py              I/O JSON atómica + IDs estables
├── register.py             yank/paste interno
├── status_bar.py           modeline
├── layout.py               panel manager
├── themes.py               wrapper de temas Textual
├── hotkey_config.py        hotkeys de config.yaml
├── vim/                    dispatch Vim (modes, keybindings)
├── modals/                 7 modales con BaseModalScreen
├── widgets/                widgets Textual (file panel)
├── features/               comandos por dominio (theme, doc, pane, hotkey, leader)
├── files/                  vault de documentos JSON
└── tests/{unit,integration}
```

Cada subdirectorio tiene su propio `AGENTS.md` con el patrón de uso.

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
| `J`                    | Unir línea actual con la siguiente.                                  |
| `u` / `Ctrl+R`         | Undo / redo.                                                        |
| `:`                    | Abrir paleta de comandos (fuzzy + autocompletado).                  |
| `space`                | Abrir WhichKey (overlay con comandos disponibles).                  |

En `visual` o `visual_line`: `y` copia la selección, `d` la corta. El
registro es interno; no toca el portapapeles del sistema.

## Hotkeys globales

| Tecla       | Acción                          |
| ----------- | ------------------------------- |
| `Ctrl+P`    | Abrir paleta de comandos.       |
| `Ctrl+S`    | Guardar el documento ahora.     |
| `Ctrl+Q`    | Salir.                          |

Resto de operaciones globales mediante el leader `space`:

| Combo       | Acción                          |
| ----------- | ------------------------------- |
| `space n`   | Nuevo documento.                |
| `space o`   | Abrir documento del vault.      |
| `space s`   | Guardar.                        |
| `space d`   | Borrar documento (con picker).  |
| `space p`   | Abrir paleta de comandos.       |
| `space b`   | Mostrar/ocultar panel archivos. |
| `space h`   | Foco en panel archivos.         |
| `space l`   | Foco en editor.                 |
| `space ?`   | Mostrar todos los hotkeys.      |

## Panel de archivos

Panel izquierdo con árbol filtrado a `.json` dentro de `files/` (vault).
Click o `Enter` abre el archivo seleccionado, guardando primero
cualquier cambio pendiente. `j`/`k` navegan, `space` abre WhichKey.

## Paleta de comandos

`:` o `Ctrl+P` abre el modal. Escribe para filtrar; el input muestra
texto fantasma con autocompletado. `→` (o `End`) acepta el fantasma,
`↓` mueve foco a la lista, `Enter` ejecuta el primer match (o el
resaltado si tienes el foco en la lista), `Esc` cancela.

**Convención de nombres:**

| Prefijo   | Dominio        | Ejemplos                                        |
| --------- | -------------- | ----------------------------------------------- |
| `theme-`  | Temas/color    | `theme-toggle`, `theme-pick`                    |
| `pane-`   | Layout/paneles | `pane-files-toggle`, `pane-focus-files`         |
| `doc-`    | Documento I/O  | `doc-save`, `doc-rename`, `doc-new`, `doc-open`, `doc-delete` |
| `hotkey`  | Bindings       | `hotkeys`, `hotkey-set`                         |

## Temas de color

21 temas integrados de Textual (incluye `textual-dark` por defecto,
`tokyo-night`, `nord`, `dracula`, `gruvbox-dark`, `catppuccin-mocha`,
`catppuccin-latte`, `monokai`, `solarized-light`, `solarized-dark`).

`:theme-pick` para verlos todos. `:theme-toggle` alterna dark/light.

## Persistencia JSON

Vault en `files/`. Cada `.json` es un documento; el editor abre
`files/document.json` al arrancar.

Cada línea se serializa como `{"id": "uuid", "text": "..."}`. Los IDs
son estables: una línea sin cambios conserva su id entre sesiones. La
escritura es atómica (archivo temporal + rename) — un crash a mitad de
guardado no corrompe el documento.

## Ejecutar

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

## Tests

```bash
.venv/bin/python -m pytest tests/ -q                # full suite
.venv/bin/python -m pytest tests/unit -q            # unit only
.venv/bin/python -m pytest tests/integration -q     # Pilot only
```

133+ tests cubriendo storage, register, commands, config, themes,
layout, modes, leader, messages, command palette, keybindings, app
lifecycle, WhichKey y feature registration.
