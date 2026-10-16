// Read Along: listen to a note while the words being spoken are highlighted.
//
// The reading engine is a pinned copy of Read Along's engine.js
// (docs/assets/read-along/engine.js, from github.com/simone-belli/read-along).
// This file only adds the Notes-specific parts: a "Listen" button next to the
// page title, a player bar fixed to the bottom of the window, and the options
// that teach the engine Material's markup (KaTeX formulas, tag chips, collapsed
// sections, closed details).
//
// The player only appears on pages that overrides/main.html marks with
// <meta name="read-along">, i.e. content pages, not section hubs. Settings and
// the ElevenLabs key live in localStorage under `readalong.*`, shared with the
// Read Along site itself (same origin), and generated audio is cached there too.

const PLAYER_HTML = `
  <div class="ra-settings" data-ra="settings" hidden>
    <label>Engine
      <select data-ra="engine">
        <option value="eleven">ElevenLabs</option>
        <option value="system">System voice</option>
      </select>
    </label>
    <label>Voice <select data-ra="voice"></select></label>
    <label>Model
      <select data-ra="model">
        <option value="eleven_flash_v2_5">Flash v2.5 (½ credit/char)</option>
        <option value="eleven_multilingual_v2">Multilingual v2 (1 credit/char)</option>
      </select>
    </label>
    <span class="ra-note" data-ra="credits"></span>
    <span class="ra-spacer"></span>
    <span class="ra-note" data-ra="keyStatus"></span>
    <button type="button" class="md-button" data-ra="changeKey">Change key</button>
  </div>
  <div class="ra-settings" data-ra="keyRow" hidden>
    <label>ElevenLabs API key
      <input type="password" data-ra="apikey" autocomplete="off" spellcheck="false" placeholder="sk_…">
    </label>
    <button type="button" class="md-button md-button--primary" data-ra="saveKey">Save key</button>
    <button type="button" class="md-button" data-ra="cancelKey">Cancel</button>
    <span class="ra-note">Stored only in this browser.</span>
  </div>
  <div class="ra-row">
    <button type="button" class="ra-icon" data-ra="prev" title="Previous sentence (←)" aria-label="Previous sentence"></button>
    <button type="button" class="ra-icon ra-play" data-ra="play" title="Play / pause (Space)" aria-label="Play or pause"></button>
    <button type="button" class="ra-icon" data-ra="next" title="Next sentence (→)" aria-label="Next sentence"></button>
    <button type="button" class="ra-icon" data-ra="stop" title="Stop (Esc)" aria-label="Stop"></button>
    <input type="range" data-ra="scrub" min="0" max="0" value="0" step="1" aria-label="Position">
    <span class="ra-time" data-ra="time">0:00 / 0:00</span>
    <label class="ra-opt" title="Playback speed">
      <select data-ra="rate" aria-label="Speed">
        <option>0.8</option><option>0.9</option><option selected>1</option><option>1.1</option>
        <option>1.25</option><option>1.5</option><option>1.75</option><option>2</option>
      </select>×
    </label>
    <label class="ra-opt" title="Keep the current word in view"><input type="checkbox" data-ra="follow" checked> Follow</label>
    <label class="ra-opt" title="Pause before code blocks, display formulas and tables"><input type="checkbox" data-ra="pauseBlocks"> Pause at blocks</label>
    <button type="button" class="ra-icon" data-ra="gear" title="Settings" aria-label="Settings"></button>
    <button type="button" class="ra-icon" data-ra="close" title="Close the player" aria-label="Close the player"></button>
  </div>
  <div class="ra-status" data-ra="status" aria-live="polite"></div>
`;

// What the engine reads, in Material + KaTeX terms. Display formulas are their
// own block (`div.arithmatex`); everything else follows Read Along's defaults.
const ENGINE_OPTIONS = {
  blockSelector: "h1,h2,h3,h4,h5,h6,p,li,td,th,dt,dd,figcaption,summary,div.arithmatex",
  skipSelector: [
    "pre, script, style, svg",
    ".md-tags, .headerlink, .md-source-file, .md-content__button, .ra-listen",
    "details:not([open]) > :not(summary)", // closed details: read the title only
  ].join(", "),
  mathSelector: ".arithmatex",
  displayMathSelector: "div.arithmatex",
};

// KaTeX keeps the source in a MathML annotation; before KaTeX has run, the
// element still holds the raw `\(...\)` / `\[...\]` text.
function texOf(el) {
  const annotation = el.querySelector('annotation[encoding="application/x-tex"]');
  if (annotation) return annotation.textContent;
  return el.textContent.trim().replace(/^\\[([]/, "").replace(/\\[)\]]$/, "");
}

// Open a mobile collapsed section before reading into it (see
// collapsible-sections.js): drop `hidden` and fire `beforematch`, exactly as
// find-in-page does, so the heading's state follows.
function reveal(el) {
  const section = el.closest(".collapsible-section[hidden]");
  if (!section) return;
  section.removeAttribute("hidden");
  section.dispatchEvent(new Event("beforematch"));
}

function icon(icons, name) {
  const node = icons.content.querySelector(`[data-icon="${name}"] svg`);
  return node ? node.outerHTML : "";
}

document$.subscribe(() => {
  const icons = document.getElementById("read-along-icons");
  const article = document.querySelector("article.md-content__inner");
  const title = article && article.querySelector("h1");
  if (!icons || !title || !window.ReadAlong || article.querySelector(".ra-listen")) return;

  const listen = document.createElement("button");
  listen.type = "button";
  listen.className = "md-content__button md-icon ra-listen";
  listen.title = "Listen to this page";
  listen.setAttribute("aria-label", "Listen to this page");
  listen.innerHTML = icon(icons, "listen");
  title.before(listen);

  let player = null;
  let ra = null;

  function build() {
    player = document.createElement("div");
    player.className = "ra-player";
    player.hidden = true;
    player.setAttribute("role", "region");
    player.setAttribute("aria-label", "Read Along player");
    player.innerHTML = PLAYER_HTML;
    for (const name of ["prev", "next", "stop", "close"]) {
      player.querySelector(`[data-ra="${name}"]`).innerHTML = icon(icons, name);
    }
    player.querySelector('[data-ra="gear"]').innerHTML = icon(icons, "settings");
    document.body.append(player);

    const ui = {};
    player.querySelectorAll("[data-ra]").forEach((el) => {
      ui[el.dataset.ra] = el;
    });
    const header = document.querySelector(".md-header");

    ra = ReadAlong.create({
      ...ENGINE_OPTIONS,
      root: article,
      ui,
      tex: texOf,
      reveal,
      viewport: () => ({
        top: (header ? header.getBoundingClientRect().bottom : 0) + 16,
        bottom: player.getBoundingClientRect().top - 16,
      }),
      // Only while the player is open, and never for a focused collapsible
      // heading, which uses Space to toggle itself.
      keys: (event) => !player.hidden && !event.target.closest?.('[role="button"]'),
    });
    ui.close.addEventListener("click", close);
  }

  function open() {
    if (!player) build();
    player.hidden = false;
    document.body.classList.add("ra-open");
    ra.refresh(); // pick up details opened or closed since last time
    ra.setStatus(ra.summary());
    if (ra.needsKey()) {
      ra.openSettings('Paste your ElevenLabs API key to use ElevenLabs voices, or switch Engine to "System voice".');
    }
  }

  function close() {
    ra.stop();
    player.hidden = true;
    document.body.classList.remove("ra-open");
    listen.focus();
  }

  listen.addEventListener("click", () => {
    if (player && !player.hidden) close();
    else open();
  });
});
