// Wikipedia-style collapsed sections on the mobile layout.
//
// Each `##` section's content is wrapped in a `.collapsible-section` div. Below
// 76.25em — where Material hides the sidebar behind the drawer — those divs
// start hidden and their heading becomes the toggle, so a phone opens on the
// page intro plus a stack of section titles. Everything above the first `##`
// (title, tag chips, lead paragraphs) is never touched.
//
// The state lives in the DOM (`hidden` on the body, `aria-expanded` on the
// heading) and is added or removed by the media query listener, so the desktop
// layout keeps its original markup and resizing works in both directions.

const MOBILE_QUERY = "screen and (max-width: 76.234375em)";

// Move each `##` section's content into a wrapper right after its heading.
// Only direct children of the article are considered, so an `h2` nested inside
// a card grid or an admonition is left alone. Returns the non-empty sections.
function wrapSections(article) {
  const sections = [];
  let body = null;

  Array.from(article.children).forEach((node) => {
    if (node.tagName === "H2") {
      const heading = node;
      if (!heading.id) heading.id = `section-${sections.length + 1}`;
      body = document.createElement("div");
      body.className = "collapsible-section";
      body.id = `${heading.id}--body`;
      heading.after(body);
      sections.push({ heading, body });
    } else if (body) {
      body.append(node);
    }
  });

  return sections.filter(({ body: sectionBody }) => {
    if (sectionBody.childElementCount) return true;
    sectionBody.remove(); // a heading with nothing under it gets no toggle
    return false;
  });
}

function setExpanded(section, expanded) {
  section.heading.setAttribute("aria-expanded", String(expanded));
  if (expanded) {
    section.body.removeAttribute("hidden");
  } else {
    // "until-found" keeps the text reachable by browser find-in-page, which
    // then reveals it and fires `beforematch`. Browsers without support treat
    // it as a plain `hidden`.
    section.body.setAttribute("hidden", "until-found");
  }
}

// Apply or strip the collapsible state for the current viewport width.
function applyLayout(sections, isMobile) {
  sections.forEach((section) => {
    const { heading, body } = section;
    if (isMobile) {
      heading.classList.add("is-collapsible");
      heading.setAttribute("role", "button");
      heading.setAttribute("tabindex", "0");
      heading.setAttribute("aria-controls", body.id);
      setExpanded(section, false);
    } else {
      heading.classList.remove("is-collapsible");
      heading.removeAttribute("role");
      heading.removeAttribute("tabindex");
      heading.removeAttribute("aria-controls");
      heading.removeAttribute("aria-expanded");
      body.removeAttribute("hidden");
    }
  });
}

function bindToggle(section) {
  const { heading, body } = section;
  const toggle = () => {
    if (!heading.classList.contains("is-collapsible")) return;
    setExpanded(section, heading.getAttribute("aria-expanded") !== "true");
  };

  heading.addEventListener("click", toggle);
  heading.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault(); // Space would otherwise scroll the page
    toggle();
  });

  // The browser drops `hidden` itself when find-in-page reveals the section;
  // this keeps the chevron and aria state in step.
  body.addEventListener("beforematch", () => {
    heading.setAttribute("aria-expanded", "true");
  });
}

// Open the section a `#fragment` points at — covers pasted deep links, search
// results, and table-of-contents taps inside the drawer.
function expandForHash(sections) {
  if (!window.location.hash) return;
  const id = decodeURIComponent(window.location.hash.slice(1));
  const target = document.getElementById(id); // ids like `tag:cli` break selectors
  if (!target) return;

  const section = sections.find(
    (candidate) => candidate.heading === target || candidate.body.contains(target),
  );
  if (!section || section.heading.getAttribute("aria-expanded") === "true") return;

  setExpanded(section, true);
  target.scrollIntoView();
}

document$.subscribe(() => {
  const article = document.querySelector("article.md-content__inner");
  if (!article || article.dataset.sectionsWrapped) return;
  article.dataset.sectionsWrapped = "true";

  const sections = wrapSections(article);
  if (!sections.length) return;
  sections.forEach(bindToggle);

  const mobile = window.matchMedia(MOBILE_QUERY);
  applyLayout(sections, mobile.matches);
  mobile.addEventListener("change", (event) => applyLayout(sections, event.matches));

  const openHash = () => {
    if (mobile.matches) expandForHash(sections);
  };
  requestAnimationFrame(openHash); // after the theme's own scroll-to-anchor
  window.addEventListener("hashchange", openHash);
  // A fragment link to the current hash fires no `hashchange`, so catch the
  // click too: re-tapping a table-of-contents entry must still open it.
  document.addEventListener("click", (event) => {
    if (event.target.closest?.('a[href^="#"]')) requestAnimationFrame(openHash);
  });
});
