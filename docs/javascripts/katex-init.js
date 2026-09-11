// Render the math that pymdownx.arithmatex (generic: true) emits.
//
// Only the \(...\) and \[...\] delimiters are enabled: arithmatex wraps every
// formula in those, and leaving `$` out means a literal dollar in prose is
// never mistaken for math. Code blocks are skipped by KaTeX's default
// ignoredTags, so shell prompts are safe either way.
document$.subscribe(() => {
  renderMathInElement(document.body, {
    delimiters: [
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
    ],
    throwOnError: false,
  });
});
