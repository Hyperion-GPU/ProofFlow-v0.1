// Vanilla webview script for the ProofFlow Case Detail panel.
// Talks to the extension host via vscode.postMessage / window.message events.
// No bundler — keep this file ES2017+ compatible and dependency-free.

(function () {
  const vscode = acquireVsCodeApi();
  let currentPacket = null;
  let activeTab = "overview";

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-tab");
      if (!target) return;
      activeTab = target;
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.toggle("active", t === tab));
      document
        .querySelectorAll(".panel")
        .forEach((p) =>
          p.classList.toggle(
            "active",
            p.getAttribute("data-panel") === target
          )
        );
    });
  });

  document.getElementById("export-packet").addEventListener("click", () => {
    vscode.postMessage({ type: "exportPacket" });
  });

  window.addEventListener("message", (event) => {
    const msg = event.data;
    if (!msg) return;
    if (msg.type === "loading") {
      setHeader("Loading…", "", "", "");
      return;
    }
    if (msg.type === "packet") {
      currentPacket = msg.packet;
      render(currentPacket);
    }
  });

  vscode.postMessage({ type: "ready" });

  function render(packet) {
    const c = packet.case;
    setHeader(
      c.title || c.id,
      c.kind || "",
      c.status || "",
      formatTime(c.updated_at)
    );
    renderOverview(packet);
    renderEvidenceClaims(packet);
    renderActions(packet);
    renderRiskHints(packet);
  }

  function setHeader(title, kind, status, updated) {
    document.getElementById("case-title").textContent = title;
    document.getElementById("case-kind").textContent = kind;
    document.getElementById("case-status").textContent = status;
    document.getElementById("case-updated").textContent = updated
      ? `updated ${updated}`
      : "";
  }

  function renderOverview(packet) {
    const meta = packet.case && packet.case.metadata ? packet.case.metadata : {};
    const contract =
      meta.work_contract || meta.contract || pickContractFromMeta(meta);
    const contractCard = document.getElementById("overview-contract");
    const fields = document.getElementById("contract-fields");
    fields.innerHTML = "";
    if (contract && Object.keys(contract).length > 0) {
      contractCard.classList.remove("hidden");
      addContractField(fields, "Objective", contract.objective);
      addContractList(fields, "Allowed scope", contract.allowed_scope);
      addContractList(fields, "Forbidden actions", contract.forbidden_actions);
      addContractList(fields, "Required tests", contract.required_tests);
      addContractList(fields, "Done criteria", contract.done_criteria);
      addContractList(
        fields,
        "Evidence requirements",
        contract.evidence_requirements
      );
    } else {
      contractCard.classList.add("hidden");
    }

    const budgets = packet.artifacts.filter(
      (a) => a.role === "cost_budget" || a.kind === "cost_budget"
    );
    const budgetCard = document.getElementById("overview-budgets");
    const budgetList = document.getElementById("budget-list");
    budgetList.innerHTML = "";
    if (budgets.length > 0) {
      budgetCard.classList.remove("hidden");
      for (const b of budgets) {
        const li = document.createElement("li");
        li.textContent = `${b.name}: ${b.uri}`;
        budgetList.appendChild(li);
      }
    } else {
      budgetCard.classList.add("hidden");
    }

    const decisions = packet.artifacts.filter(
      (a) => a.role === "algorithm_decision" || a.kind === "algorithm_decision"
    );
    const decisionCard = document.getElementById("overview-decisions");
    const decisionList = document.getElementById("decision-list");
    decisionList.innerHTML = "";
    if (decisions.length > 0) {
      decisionCard.classList.remove("hidden");
      for (const d of decisions) {
        const li = document.createElement("li");
        li.textContent = `${d.name}: ${d.uri}`;
        decisionList.appendChild(li);
      }
    } else {
      decisionCard.classList.add("hidden");
    }

    const empty = document.getElementById("overview-empty");
    const anyVisible =
      !contractCard.classList.contains("hidden") ||
      !budgetCard.classList.contains("hidden") ||
      !decisionCard.classList.contains("hidden");
    empty.style.display = anyVisible ? "none" : "block";
  }

  function pickContractFromMeta(meta) {
    if (
      typeof meta.objective === "string" ||
      Array.isArray(meta.allowed_scope)
    ) {
      return meta;
    }
    return null;
  }

  function addContractField(container, label, value) {
    if (typeof value !== "string" || !value) return;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    container.appendChild(dt);
    container.appendChild(dd);
  }

  function addContractList(container, label, value) {
    if (!Array.isArray(value) || value.length === 0) return;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    const ul = document.createElement("ul");
    for (const entry of value) {
      const li = document.createElement("li");
      li.textContent = String(entry);
      ul.appendChild(li);
    }
    dd.appendChild(ul);
    container.appendChild(dt);
    container.appendChild(dd);
  }

  function renderEvidenceClaims(packet) {
    const evidenceList = document.getElementById("evidence-list");
    const claimList = document.getElementById("claim-list");
    evidenceList.innerHTML = "";
    claimList.innerHTML = "";

    const allEvidence = [];
    for (const claim of packet.claims) {
      for (const e of claim.evidence) {
        allEvidence.push({ evidence: e, claim });
      }
    }

    if (allEvidence.length === 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No evidence recorded.";
      evidenceList.appendChild(li);
    } else {
      for (const { evidence: e, claim } of allEvidence) {
        const li = document.createElement("li");
        li.className = `severity-${claim.severity}`;
        li.dataset.evidenceId = e.id;
        li.dataset.claimId = claim.id;

        const head = document.createElement("strong");
        head.textContent =
          (e.content || "").split(/\r?\n/)[0]?.slice(0, 100) || e.id;
        li.appendChild(head);

        const meta = document.createElement("span");
        meta.className = "meta";
        meta.textContent = `${e.evidence_type}${
          e.source_ref ? ` • ${e.source_ref}` : ""
        }`;
        li.appendChild(meta);

        if (e.source_location && e.source_location.path) {
          const btn = document.createElement("button");
          btn.className = "link-like";
          btn.textContent = `Open ${e.source_location.path}:${e.source_location.start_line}`;
          btn.addEventListener("click", () => {
            vscode.postMessage({
              type: "openSource",
              payload: {
                path: e.source_location.path,
                startLine: e.source_location.start_line,
              },
            });
          });
          li.appendChild(btn);
        }

        li.addEventListener("mouseenter", () => highlightClaim(claim.id, true));
        li.addEventListener("mouseleave", () =>
          highlightClaim(claim.id, false)
        );
        evidenceList.appendChild(li);
      }
    }

    if (packet.claims.length === 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No claims recorded.";
      claimList.appendChild(li);
    } else {
      for (const claim of packet.claims) {
        const li = document.createElement("li");
        li.className = `severity-${claim.severity}`;
        li.dataset.claimId = claim.id;

        const head = document.createElement("strong");
        head.textContent = claim.claim_text;
        li.appendChild(head);

        const meta = document.createElement("span");
        meta.className = "meta";
        meta.textContent = `${claim.severity} • ${claim.evidence.length} evidence • ${claim.status}`;
        li.appendChild(meta);

        li.addEventListener("mouseenter", () => highlightEvidence(claim.id, true));
        li.addEventListener("mouseleave", () => highlightEvidence(claim.id, false));
        claimList.appendChild(li);
      }
    }
  }

  function highlightClaim(claimId, on) {
    document.querySelectorAll(`#claim-list li[data-claim-id="${claimId}"]`).forEach((el) => {
      el.classList.toggle("evidence-bound", on);
    });
  }

  function highlightEvidence(claimId, on) {
    document
      .querySelectorAll(`#evidence-list li[data-claim-id="${claimId}"]`)
      .forEach((el) => {
        el.classList.toggle("evidence-bound", on);
      });
  }

  function renderActions(packet) {
    const list = document.getElementById("action-list");
    list.innerHTML = "";
    if (!packet.actions || packet.actions.length === 0) {
      const li = document.createElement("li");
      li.className = "empty";
      li.textContent = "No actions.";
      list.appendChild(li);
      return;
    }
    for (const a of packet.actions) {
      const li = document.createElement("li");
      const head = document.createElement("strong");
      head.textContent = a.title || a.id;
      li.appendChild(head);
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = a.status;
      li.appendChild(meta);
      list.appendChild(li);
    }
  }

  function renderRiskHints(packet) {
    const empty = document.getElementById("hints-empty");
    const list = document.getElementById("hint-list");
    list.innerHTML = "";
    const evaluations = (packet.runs || []).filter((r) =>
      (r.run_type || "").toLowerCase().includes("evaluat")
    );
    if (evaluations.length === 0) {
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    for (const run of evaluations) {
      const meta = run.metadata || {};
      const hints = Array.isArray(meta.risk_hints) ? meta.risk_hints : [];
      const failedDone = Array.isArray(meta.failed_done_criteria)
        ? meta.failed_done_criteria
        : [];
      const header = document.createElement("li");
      header.innerHTML = `<strong>Run ${run.id}</strong> — ${run.status}<span class="meta"> ${formatTime(run.created_at)}</span>`;
      list.appendChild(header);
      if (failedDone.length > 0) {
        const fdLi = document.createElement("li");
        fdLi.innerHTML = `<span class="meta">Failed done criteria:</span> ${failedDone.map(escapeHtml).join(", ")}`;
        list.appendChild(fdLi);
      }
      if (hints.length === 0) {
        const noneLi = document.createElement("li");
        noneLi.className = "meta";
        noneLi.textContent = "No risk hints in this run.";
        list.appendChild(noneLi);
      } else {
        for (const hint of hints) {
          const li = document.createElement("li");
          li.className = `hint-row severity-${hint.severity || "info"}`;
          const desc = document.createElement("div");
          desc.className = "desc";
          desc.innerHTML = `<strong>${escapeHtml(hint.hint_code || "")}</strong><br/><span class="meta">${escapeHtml(hint.message || "")}</span>`;
          const btn = document.createElement("button");
          btn.className = "secondary";
          btn.textContent = "Explain";
          btn.addEventListener("click", () => {
            vscode.postMessage({
              type: "explainRiskHint",
              payload: {
                hintCode: hint.hint_code,
                evaluationRunId: run.id,
              },
            });
          });
          li.appendChild(desc);
          li.appendChild(btn);
          list.appendChild(li);
        }
      }
    }
  }

  function formatTime(value) {
    if (!value) return "";
    return String(value).replace("T", " ").replace(/\..*$/, "");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();
