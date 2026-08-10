# Vim — modal editing cheat sheet

**Vim** (Vi IMproved) is a **modal** editor: most of the time you're in *Normal mode*, where keys are commands (verbs and motions), not text. You enter *Insert mode* only to type. It's preinstalled on virtually every Unix/Linux/macOS box and is [Git](../git/git.md)'s default editor for commit messages and interactive rebases, so surviving in it is a baseline skill.

!!! note "The one habit that unlocks Vim"
    Live in **Normal mode**. Dip into Insert, type, then `Esc` straight back. When anything seems broken or a `:` command does nothing, you're likely stuck in Insert mode — press `Esc` first.

## Modes

| Mode | Enter with | For |
|------|-----------|-----|
| Normal | `Esc` (default) | Commands: motions, operators, `:` |
| Insert | `i` `a` `o` `I` `A` `O` | Typing text |
| Visual | `v` (char) `V` (line) `Ctrl-v` (block) | Selecting a region |
| Command-line (Ex) | `:` | File/search/config ops |

The keys that enter Insert mode differ by where they drop the cursor:

| Key | Enters Insert… |
|-----|----------------|
| `i` | before the cursor |
| `a` | after the cursor |
| `I` | at line start |
| `A` | at line end |
| `o` | on a new line below |
| `O` | on a new line above |

## The grammar: `operator + count + motion`

Many commands parse as a sentence — `[count] operator [count] motion/text-object` — so they **compose**.

**Operators** (the verb — what to do to a range):

| Key | Action |
|-----|--------|
| `d` | delete |
| `c` | change (delete, then insert) |
| `y` | yank (copy) |
| `>` / `<` | indent / dedent |
| `=` | auto-indent |
| `gu` / `gU` | lowercase / uppercase |

**Motions** (define the range by movement):

| Key | Moves to |
|-----|----------|
| `w` / `b` / `e` | next word / back a word / end of word |
| `0` / `$` | start / end of line |
| `gg` / `G` | top / bottom of file |
| `f x` / `t x` | onto / just before next `x` |
| `}` | next paragraph |
| `%` | matching bracket |

**Text objects** (define the range by structure — the real superpower):

| Object | Selects |
|--------|---------|
| `iw` / `aw` | inner word / a word (incl. surrounding space) |
| `i"` | inside quotes |
| `i(` / `ib` | inside parentheses |
| `a(` | a `(…)` block, parens included |
| `i{` | inside braces |
| `it` / `at` | inside / around an HTML tag |
| `ip` | paragraph |

Combining a verb with a motion or object gives you the actual edits:

| Command | Meaning |
|---------|---------|
| `dw` | delete word |
| `d3w` / `3dw` | delete three words |
| `ci"` | change inside quotes |
| `ca(` | change a `(…)` block, parens included |
| `di{` | empty a brace block |
| `dt,` | delete till next comma |
| `cip` | change this paragraph |
| `dd` / `yy` / `>>` | delete / yank / indent the whole line |

Doubling an operator (`dd`, `yy`, `>>`) targets the whole line.

## Everyday commands

| Command | Action |
|---------|--------|
| `.` | repeat the last change (pair with `n` after a search for surgical find-and-replace) |
| `u` / `Ctrl-r` | undo / redo (Vim keeps a branching undo *tree*) |
| `p` / `P` | paste after / before the cursor (`3p` pastes ×3) |
| `"+y` / `"+p` | yank / paste via the system clipboard |
| `5j` / `2dd` | counts multiply a command: down 5 lines / delete 2 lines |
| `ma` / `` `a `` | set mark `a` / jump to it |
| `qa` … `q` / `@a` / `@@` | record macro into `a` / replay it / repeat last (`10@a` runs it 10×) |

## Search & substitute

| Command | Action |
|---------|--------|
| `/pattern` / `?pattern` | search forward / backward |
| `n` / `N` | next / previous match |
| `*` | search for the word under the cursor |
| `:s/old/new/g` | substitute on the current line (`g` = all matches, not just the first) |
| `:%s/old/new/g` | substitute in the whole file (`%` = all lines) |
| `:%s/old/new/gc` | …with confirmation on each match |

Patterns are [regex](regexp.md). A [Visual](#modes) selection + `:s` scopes the substitute to the selection.

## Windows, buffers, tabs

| Command | Action |
|---------|--------|
| `:e file` / `:ls` | open a file into a buffer / list buffers |
| `:bn` / `:bp` | next / previous buffer |
| `:sp` / `:vsp` | split horizontally / vertically |
| `Ctrl-w` then `h` `j` `k` `l` | move between splits |
| `:tabnew` / `gt` / `gT` | new tab / next / previous tab |

## Exit (the famous one)

| Command | Action |
|---------|--------|
| `:w` | save |
| `:q` | quit |
| `:wq` / `:x` / `ZZ` | save & quit |
| `:q!` | quit, discarding changes |
| `:qa` | quit all windows |

## Config & learning

- Config lives in `~/.vimrc` (Vim) or `~/.config/nvim/init.lua` (Neovim). Common lines: `set number`, `syntax on`, `set expandtab shiftwidth=4`.
- `:help <topic>` opens the built-in manual. Run **`vimtutor`** in a terminal for a 30-minute guided intro — the best way to start.
