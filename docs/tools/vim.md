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

Insert entries: `i` before cursor · `a` after · `I` line start · `A` line end · `o` new line below · `O` new line above.

## The grammar: `operator + count + motion`

Many commands parse as a sentence — `[count] operator [count] motion/text-object` — so they **compose**:

- **Operators**: `d` delete · `c` change (delete + insert) · `y` yank (copy) · `>`/`<` indent · `=` auto-indent · `gu`/`gU` lower/upper.
- **Motions**: `w`/`b`/`e` word fwd/back/end · `0`/`$` line start/end · `gg`/`G` file top/bottom · `f x` to next `x` · `t x` till `x` · `}` paragraph · `%` matching bracket.
- **Text objects** (range by structure): `iw`/`aw` inner/a word · `i"` inside quotes · `i(` / `ib` inside parens · `a(` incl. parens · `i{` braces · `it`/`at` HTML tag · `ip` paragraph.

```
dw      delete word            d3w / 3dw  delete three words
ci"     change inside quotes   ca(        change a (…) block, parens included
dd      delete line            yy         yank line      >>  indent line
di{     empty a brace block    dt,        delete till next comma   cip  change paragraph
```

Doubling an operator (`dd`, `yy`, `>>`) targets the whole line.

## Everyday commands

- **Repeat**: `.` repeats the last change — pair with search (`n` then `.`) as surgical find-and-replace.
- **Undo/redo**: `u` undo · `Ctrl-r` redo (Vim keeps a branching undo *tree*).
- **Paste**: `p` after cursor · `P` before · `3p` paste ×3. Yank/paste use **registers**; `"+y` / `"+p` use the system clipboard.
- **Counts multiply**: `5j` down 5 lines · `2dd` delete 2 lines.
- **Marks**: `ma` set mark `a` · `` `a `` jump to it.
- **Macros**: `qa` record into `a`, `q` stop, `@a` replay, `@@` repeat, `10@a` run 10×.

## Search & substitute

```vim
/pattern      search forward (n / N = next / prev)      *  search word under cursor
?pattern      search backward
:s/old/new/g          substitute on current line (g = all matches)
:%s/old/new/g         substitute in whole file (% = all lines)
:%s/old/new/gc        …with confirm on each
```

Patterns are [regex](regexp.md). A [Visual](#modes) selection + `:s` scopes the substitute to the selection.

## Windows, buffers, tabs

- **Buffers** (open files): `:e file` · `:ls` · `:bn`/`:bp`.
- **Splits**: `:sp` horizontal · `:vsp` vertical · move with `Ctrl-w` then `h`/`j`/`k`/`l`.
- **Tabs**: `:tabnew` · `gt`/`gT`.

## Exit (the famous one)

```vim
:w      save              :q      quit            :wq  /  :x  /  ZZ   save & quit
:q!     quit, discard changes                     :qa                quit all
```

## Config & learning

- Config: `~/.vimrc` (Vim) or `~/.config/nvim/init.lua` (Neovim). Common: `set number`, `syntax on`, `set expandtab shiftwidth=4`.
- `:help <topic>` opens the built-in manual. Run **`vimtutor`** in a terminal for a 30-minute guided intro — the best way to start.
