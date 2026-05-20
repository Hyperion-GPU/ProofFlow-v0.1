// Approve Gate webview script. Communicates with extension host via
// vscode.postMessage / message events. No bundler — keep dependency free.

(function () {
  const vscode = acquireVsCodeApi();
  let currentAction = null;
  let inlineTarget = null;

  document.getElementById("approve").addEventListener("click", () => {
    vscode.postMessage({ type: "approve" });
  });
  document.getElementById("reject").addEventListener("click", () => {
    vscode.postMessage({ type: "reject" });
  });
  document.getElementById("open-inline").addEventListener("click", () => {
    if (!inlineTarget) return;
    vscode.postMessage({ type: "openSource", payload: inlineTarget });
  });

  window.addEventListener("message", (event) => {
    const msg = event.data;
    if (!msg) return;
    if (msg.type === "loading") {
      setHeader("Loading…", []);
      return;
    }
    if (msg.type === "render") {
      currentAction = msg.action || null;
      render(currentAction, msg.packet, msg.meta || {});
    }
  });

  vscode.postMessage({ type: "ready" });

  function render(action, _packet, meta) {
    if (!action) {
      setHeader("Action not found", []);
      document.getElementById("preview-body").textContent =
        "The action may have already been resolved or removed.";
      document.getElementById("approve").disabled = true;
      return;
    }
    setHeader(action.title || action.id, [action.kind, action.status]);

    const previewBody = document.getElementById("preview-body");
    previewBody.innerHTML = "";
    const preview = action.preview || {};
    const rows = [];
    if (preview.from_path) rows.push(["From", preview.from_path]);
    if (preview.to_path) rows.push(["To", preview.to_path]);
    if (preview.dir_path) rows.push(["Dir", preview.dir_path]);
    if (action.reason) rows.push(["Reason", action.reason]);
    if (rows.length === 0 && !preview.content) {
      previewBody.textContent = "No structured preview.";
    } else {
      for (const [k, v] of rows) {
        const row = document.createElement("div");
        row.className = "row";
        const strong = document.createElement("strong");
        strong.textContent = k;
        const span = document.createElement("span");
        span.textContent = v;
        row.appendChild(strong);
        row.appendChild(span);
        previewBody.appendChild(row);
      }
      if (preview.content) {
        const pre = document.createElement("pre");
        pre.textContent = preview.content;
        previewBody.appendChild(pre);
      }
    }

    const inlineBtn = document.getElementById("open-inline");
    inlineTarget = pickInlineTarget(action, meta);
    if (inlineTarget) {
      inlineBtn.classList.remove("hidden");
      inlineBtn.textContent = `Open ${inlineTarget.path}${
        inlineTarget.startLine ? `:${inlineTarget.startLine}` : ""
      }`;
    } else {
      inlineBtn.classList.add("hidden");
    }

    const riskList = document.getElementById("risk-list");
    riskList.innerHTML = "";
    const claims = (meta.risk_claims || []).slice();
    if (claims.length === 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No medium/high risk claims for this case.";
      riskList.appendChild(li);
    } else {
      for (const claim of claims) {
        riskList.appendChild(renderClaim(claim));
      }
    }

    document.getElementById("approve").disabled =
      action.status !== "pending_decision" && action.status !== "pending";
  }

  function renderClaim(claim) {
    const li = document.createElement("li");
    li.className = `severity-${claim.severity}`;

    const head = document.createElement("div");
    head.className = "claim-head";
    const text = document.createElement("strong");
    text.textContent = claim.claim_text;
    const badge = document.createElement("span");
    badge.className = "severity-badge";
    badge.textContent = claim.severity;
    head.appendChild(text);
    head.appendChild(badge);
    li.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${claim.evidence.length} evidence • ${claim.status}`;
    li.appendChild(meta);

    if (claim.evidence.length > 0) {
      const ev = claim.evidence[0];
      if (ev.source_ref || (ev.source_location && ev.source_location.path)) {
        const refLine = document.createElement("div");
        refLine.className = "meta";
        refLine.textContent = ev.source_ref || ev.source_location.path;
        li.appendChild(refLine);
      }
    }

    const actionsRow = document.createElement("div");
    actionsRow.className = "actions";
    const explainBtn = document.createElement("button");
    explainBtn.className = "secondary";
    explainBtn.textContent = "Explain";
    explainBtn.addEventListener("click", () => {
      vscode.postMessage({ type: "explain", payload: { claimId: claim.id } });
    });
    actionsRow.appendChild(explainBtn);

    const ev = claim.evidence[0];
    if (ev && ev.source_location && ev.source_location.path) {
      const openBtn = document.createElement("button");
      openBtn.className = "link-like";
      openBtn.textContent = `Open ${ev.source_location.path}:${ev.source_location.start_line}`;
      openBtn.addEventListener("click", () => {
        vscode.postMessage({
          type: "openSource",
          payload: {
            path: ev.source_location.path,
            startLine: ev.source_location.start_line,
          },
        });
      });
      actionsRow.appendChild(openBtn);
    }
    li.appendChild(actionsRow);
    return li;
  }

  function pickInlineTarget(action, meta) {
    const preview = action.preview || {};
    if (preview.from_path) {
      return { path: preview.from_path, startLine: 0 };
    }
    if (preview.to_path) {
      return { path: preview.to_path, startLine: 0 };
    }
    const claims = meta.risk_claims || [];
    for (const claim of claims) {
      for (const ev of claim.evidence) {
        if (ev.source_location && ev.source_location.path) {
          return {
            path: ev.source_location.path,
            startLine: ev.source_location.start_line,
          };
        }
      }
    }
    return null;
  }

  function setHeader(title, badges) {
    document.getElementById("action-title").textContent = title;
    const meta = document.getElementById("action-meta");
    meta.innerHTML = "";
    for (const b of badges) {
      if (!b) continue;
      const span = document.createElement("span");
      span.className = "badge";
      span.textContent = b;
      meta.appendChild(span);
    }
  }
})();
