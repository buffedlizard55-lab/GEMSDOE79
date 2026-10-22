/* Exact-file identity only. No upload, raster decoding, selector or slot use. */
"use strict";
(function () {
  const MAX_BYTES = 16 * 1024 * 1024;
  const refusal = (state, message) => ({state, matched: false, submission_approved: false, message});

  async function checkDownload(file, manifest, cryptoProvider = globalThis.crypto) {
    // Limit memory before reading a user-selected file. Unknown files are NOT
    // called invalid GeoTIFFs: only the published exact bytes can be identified.
    if (!Array.isArray(manifest) || manifest.length !== 2 ||
        !manifest.every(row => row && ["TIFF", "ZIP"].includes(row.kind) &&
          Number.isSafeInteger(row.bytes) && row.bytes > 0 && row.bytes <= MAX_BYTES &&
          typeof row.sha256 === "string" && /^[a-f0-9]{64}$/.test(row.sha256)) ||
        new Set(manifest.map(row => row.kind)).size !== 2) {
      return refusal("unverified", "UNVERIFIED — published file identity is unavailable. No submission approval.");
    }
    if (!file) return refusal("idle", "Choose the downloaded TIFF or ZIP. Nothing is uploaded.");
    if (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > MAX_BYTES ||
        !manifest.some(row => row.bytes === file.size)) {
      return refusal("unknown", "UNKNOWN FILE — size differs from the published files. This is not a raster-format diagnosis. No submission approval.");
    }
    if (!cryptoProvider || !cryptoProvider.subtle || typeof cryptoProvider.subtle.digest !== "function") {
      return refusal("unverified", "UNVERIFIED — SHA-256 is unavailable. Open this site over HTTPS or use the project CLI. No submission approval.");
    }
    try {
      const bytes = await file.arrayBuffer();
      if (!(bytes instanceof ArrayBuffer) || bytes.byteLength !== file.size) {
        return refusal("unverified", "UNVERIFIED — the file could not be read completely. No submission approval.");
      }
      const digest = await cryptoProvider.subtle.digest("SHA-256", bytes);
      const sha256 = Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, "0")).join("");
      const known = manifest.find(row => row.sha256 === sha256 && row.bytes === file.size);
      if (!known) return {...refusal("unknown", "UNKNOWN FILE — bytes differ from both published files. No format or submission approval."), sha256};
      return {state: "match", matched: true, submission_approved: false, sha256, kind: known.kind,
        message: "IDENTITY MATCH — exact published " + known.kind + " bytes. Identity is not an R1–R8 format PASS or portal acceptance. This checker grants no submission permission; follow the gate decision above."};
    } catch (_) {
      return refusal("unverified", "UNVERIFIED — file reading or SHA-256 failed. No submission approval.");
    }
  }

  function bindChecker(panel, checker = checkDownload) {
    const input = panel.querySelector("input[type=file]");
    const output = panel.querySelector("[data-download-result]");
    if (!input || !output) return;
    let sequence = 0;
    input.addEventListener("change", async () => {
      const ticket = ++sequence;
      output.dataset.state = "checking";
      output.textContent = "Checking local file identity… No submission approval.";
      panel.setAttribute("aria-busy", "true");
      let result;
      try {
        result = await checker(input.files[0], JSON.parse(panel.dataset.downloadManifest));
      } catch (_) {
        result = refusal("unverified", "UNVERIFIED — file identity could not be checked. No submission approval.");
      }
      // A slow previous read must never overwrite a more recent choice/reset.
      if (ticket !== sequence) return;
      output.textContent = result.message;
      output.dataset.state = result.state;
      panel.setAttribute("aria-busy", "false");
    });
  }

  if (typeof module !== "undefined" && module.exports) module.exports = {checkDownload, bindChecker};
  if (typeof document !== "undefined") {
    for (const panel of document.querySelectorAll("[data-download-manifest]")) bindChecker(panel);
  }
})();
