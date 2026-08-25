# Flags note pages whose prose runs on without a visual break.
#
# Usage: awk -f find-walls.awk $(find docs -name '*.md' -not -name 'README.md')
#        awk -v verbose=1 -f find-walls.awk <files>   # report every file, not just hits
#
# A "run" is consecutive prose paragraphs separated by nothing but blank lines.
# Anything that breaks the page up visually — a heading, code block, list,
# table, or admonition — ends the run. Reported as paragraphs/lines, with the
# line number where the worst run starts. Flagged at >=3 paragraphs spanning
# >=12 lines, or a page over 40 lines with no `##` at all.
#
# Written for portable awk (no gawk extensions), so each file is reported when
# the next one starts.

function endrun() {
  if (paras > maxparas || (paras == maxparas && plines > maxlines)) {
    maxparas = paras; maxlines = plines; maxat = runstart
  }
  paras = 0; plines = 0; inpara = 0
}

function report() {
  if (prev == "") return
  hit = (maxparas >= 3 && maxlines >= 12) || (lines > 40 && heads == 0)
  if (!hit && !verbose) return
  printf "%-56s %4d lines %3d headings   worst run: %d paras / %d lines at :%d%s\n", \
    prev, lines, heads, maxparas, maxlines, maxat, (hit ? "  <-- reshape" : "")
}

FNR == 1 {
  report()
  prev = FILENAME; fence = 0; heads = 0
  paras = 0; plines = 0; inpara = 0; runstart = 0
  maxparas = 0; maxlines = 0; maxat = 0
}

{ lines = FNR }

# Fenced code: toggle, and the whole block breaks any run in progress.
/^[[:space:]]*```/ { fence = !fence; if (fence) endrun(); next }
fence { next }

/^#{1,6} /       { heads += ($0 ~ /^#{2,6} /); endrun(); next }
/^(!!!|\?\?\?)/  { endrun(); next }
/^[[:space:]]*([-*+]|[0-9]+\.)[[:space:]]/ { endrun(); next }
/^[[:space:]]*[|>]/                        { endrun(); next }

# Indented continuation (admonition body, nested list text) — not a new run.
/^[[:space:]][[:space:]][[:space:]][[:space:]]/ { next }

/^[[:space:]]*$/ { inpara = 0; next }

{
  if (!inpara) { inpara = 1; paras++; if (paras == 1) runstart = FNR }
  plines++
}

END { endrun(); report() }
