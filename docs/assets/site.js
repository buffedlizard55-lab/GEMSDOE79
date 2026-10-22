"use strict";
const toast = (message) => {
  const node = document.getElementById("toast");
  if (!node) return;
  node.textContent = message;
  window.clearTimeout(window.gemsToastTimer);
  window.gemsToastTimer = window.setTimeout(() => { node.textContent = ""; }, 3500);
};
for (const button of document.querySelectorAll("[data-copy]")) {
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copy);
    if (!target) return;
    const value = target.textContent.trim();
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
      } else {
        const helper = document.createElement("textarea");
        helper.value = value; helper.setAttribute("readonly", "");
        helper.style.position = "fixed"; helper.style.opacity = "0";
        document.body.appendChild(helper); helper.select();
        const ok = document.execCommand("copy"); helper.remove();
        if (!ok) throw new Error("Clipboard unavailable");
      }
      toast("Copied.");
    } catch (_) {
      toast("Clipboard unavailable. The complete text remains visible above.");
    }
  });
}
const search = document.getElementById("history-search");
if (search) search.addEventListener("input", () => {
  const query = search.value.toLocaleLowerCase().trim();
  for (const row of document.querySelectorAll("[data-search-row]")) {
    row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
  }
});
const feed = document.getElementById("feed-status");
if (feed) {
  fetch("evidence/source_health.json", {cache: "no-cache"})
    .then((response) => {
      if (!response.ok) throw new Error("Feed unavailable");
      return response.json();
    })
    .then((data) => {
      feed.textContent = "Last direct-fetch attempt: " + data.attempted_utc + ". Scientific claims last reviewed: " + data.scientific_claims_reviewed_date + ".";
      const body = document.getElementById("health-rows");
      for (const row of data.sources || []) {
        const tr = document.createElement("tr");
        for (const value of [row.id, row.state.replaceAll("_", " "), row.http_status ?? "Not obtained"]) {
          const td = document.createElement("td"); td.textContent = String(value); tr.appendChild(td);
        }
        body.appendChild(tr);
      }
      const board = data.leaderboard_observation;
      if (board) {
        const when = board.observed_utc || board.observed_date || "date unavailable";
        const hasTop = board.public_dti !== null && board.public_dti !== undefined && board.public_dti !== "" && Number.isFinite(Number(board.public_dti));
        const hasFloor = board.rank_50_public_dti !== null && board.rank_50_public_dti !== undefined && board.rank_50_public_dti !== "" && Number.isFinite(Number(board.rank_50_public_dti));
        const top = hasTop ? Number(board.public_dti).toFixed(4) : "not recorded";
        const leader = board.first_place_participant ? " (" + board.first_place_participant + ")" : "";
        const floor = hasFloor
          ? "; visible rank-50 value " + Number(board.rank_50_public_dti).toFixed(4) +
            (board.rank_50_participant ? " (" + board.rank_50_participant + ")" : "")
          : "";
        document.getElementById("feed-observation").textContent =
          "Recorded public-leaderboard observation: #1 " + top + leader + floor +
          " (" + when + "). Not this candidate’s score and not a submission-page receipt. The fetch-attempt table reports reachability separately; its failure does not refresh leaderboard content.";
      }
    })
    .catch(() => {
      feed.textContent = "Source-health feed could not be loaded. No fresh source or leaderboard verification is claimed.";
    });
}
