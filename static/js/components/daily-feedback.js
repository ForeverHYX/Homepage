(function () {
  "use strict";

  var localFeedbackKey = "homepage_daily_feedback_events";
  var feedbackUiStateKey = "homepage_daily_feedback_ui_state";

  function initDailyFeedback() {
    var configEl = document.getElementById("dailyFeedbackConfig");
    var cards = document.querySelectorAll(".daily-card[data-feedback-payload]");
    if (!configEl || !cards.length) return;
    if (configEl.getAttribute("data-feedback-enabled") !== "true") return;

    var config = {
      runDate: configEl.getAttribute("data-run-date") || "unknown",
      supabaseUrl: configEl.getAttribute("data-supabase-url") || "",
      supabaseAnonKey: configEl.getAttribute("data-supabase-anon-key") || "",
    };

    cards.forEach(function (card) {
      applyStoredFeedbackState(card, config.runDate);
      card.addEventListener("click", function (event) {
        var button = event.target.closest(".daily-feedback-button");
        if (!button) return;
        event.preventDefault();
        submitFeedback(card, button, config);
      });
    });
  }

  function applyStoredFeedbackState(card, runDate) {
    var payload = parsePayload(card.getAttribute("data-feedback-payload") || "{}");
    var paperId = paperIdFor(payload);
    if (!paperId) return;
    var state = readFeedbackUiState();
    if ((state.hidden[runDate] || []).indexOf(paperId) !== -1) {
      hideCard(card);
      return;
    }
    if ((state.likes[runDate] || []).indexOf(paperId) !== -1) {
      markCardLiked(card);
    }
  }

  function submitFeedback(card, button, config) {
    var rating = button.getAttribute("data-feedback-rating") || "";
    if (rating !== "like" && rating !== "dislike") return;
    if (rating === "like" && button.classList.contains("is-active")) return;

    var payload = parsePayload(card.getAttribute("data-feedback-payload") || "{}");
    payload.rating = rating;
    payload.source = "page";

    button.disabled = true;
    setFeedbackButtonLabel(button, "Saving...");

    postFeedback(config, payload)
      .catch(function () {
        storeLocalFeedback(payload);
      })
      .then(function () {
        markFeedbackState(card, payload, rating, config.runDate);
      })
      .finally(function () {
        button.disabled = false;
      });
  }

  function postFeedback(config, payload) {
    if (!config.supabaseUrl || !config.supabaseAnonKey) {
      return Promise.reject(new Error("Supabase config unavailable"));
    }

    return postSupabaseFeedbackPayload(config, feedbackPayload(payload)).then(function (response) {
      if (response.ok) return undefined;
      return postSupabaseFeedbackPayload(config, legacyFeedbackPayload(payload)).then(function (legacyResponse) {
        if (legacyResponse.ok) return undefined;
        throw new Error("Feedback rejected: " + response.status);
      });
    });
  }

  function postSupabaseFeedbackPayload(config, payload) {
    return fetch(config.supabaseUrl.replace(/\/$/, "") + "/rest/v1/feedback_events", {
      method: "POST",
      headers: {
        apikey: config.supabaseAnonKey,
        Authorization: "Bearer " + config.supabaseAnonKey,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify(payload),
    });
  }

  function feedbackPayload(payload) {
    return {
      paper_id: String(payload.paper_id || ""),
      rating: payload.rating,
      source: payload.source || "page",
      section: payload.section || null,
      title: String(payload.title || ""),
      abstract: String(payload.abstract || ""),
      authors: arrayValue(payload.authors),
      affiliations: arrayValue(payload.affiliations),
      categories: arrayValue(payload.categories),
      item_type: payload.item_type === "repository" ? "repository" : "paper",
      repository_url: payload.repository_url || null,
      paper_links: arrayValue(payload.paper_links),
    };
  }

  function legacyFeedbackPayload(payload) {
    return {
      paper_id: String(payload.paper_id || ""),
      rating: payload.rating,
      source: payload.source || "page",
      section: payload.section || null,
      title: String(payload.title || ""),
      abstract: String(payload.abstract || ""),
      authors: arrayValue(payload.authors),
      affiliations: arrayValue(payload.affiliations),
      categories: arrayValue(payload.categories),
    };
  }

  function markFeedbackState(card, payload, rating, runDate) {
    var paperId = paperIdFor(payload);
    if (!paperId) return;
    var state = readFeedbackUiState();
    state.likes[runDate] = state.likes[runDate] || [];
    state.hidden[runDate] = state.hidden[runDate] || [];
    state.likes[runDate] = state.likes[runDate].filter(function (value) { return value !== paperId; });
    state.hidden[runDate] = state.hidden[runDate].filter(function (value) { return value !== paperId; });
    if (rating === "like") {
      state.likes[runDate].push(paperId);
      markCardLiked(card);
    }
    if (rating === "dislike") {
      state.hidden[runDate].push(paperId);
      hideCard(card);
    }
    localStorage.setItem(feedbackUiStateKey, JSON.stringify(state));
    window.dispatchEvent(new CustomEvent("daily-feedback-state-change", {
      detail: { paperId: paperId, rating: rating, runDate: runDate }
    }));
  }

  function markCardLiked(card) {
    var likeButton = card.querySelector('.daily-feedback-button[data-feedback-rating="like"]');
    var dislikeButton = card.querySelector('.daily-feedback-button[data-feedback-rating="dislike"]');
    card.classList.add("is-liked");
    if (likeButton) {
      likeButton.classList.add("is-active");
      setFeedbackButtonLabel(likeButton, "Liked");
    }
    if (dislikeButton) {
      dislikeButton.classList.remove("is-active");
      setFeedbackButtonLabel(dislikeButton, "Dislike");
    }
  }

  function setFeedbackButtonLabel(button, label) {
    var labelEl = button.querySelector(".daily-action-label");
    if (labelEl) {
      labelEl.textContent = label;
      return;
    }
    button.textContent = label;
  }

  function hideCard(card) {
    card.classList.add("is-feedback-hidden");
    card.hidden = true;
  }

  function parsePayload(raw) {
    try {
      var parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (error) {
      return {};
    }
  }

  function storeLocalFeedback(payload) {
    var existing = readJsonArray(localFeedbackKey);
    existing.push(Object.assign({}, feedbackPayload(payload), { created_at: new Date().toISOString() }));
    localStorage.setItem(localFeedbackKey, JSON.stringify(existing));
  }

  function readFeedbackUiState() {
    try {
      var state = JSON.parse(localStorage.getItem(feedbackUiStateKey) || "{}");
      return {
        likes: state && typeof state.likes === "object" && !Array.isArray(state.likes) ? state.likes : {},
        hidden: state && typeof state.hidden === "object" && !Array.isArray(state.hidden) ? state.hidden : {},
      };
    } catch (error) {
      return { likes: {}, hidden: {} };
    }
  }

  function readJsonArray(key) {
    try {
      var value = JSON.parse(localStorage.getItem(key) || "[]");
      return Array.isArray(value) ? value : [];
    } catch (error) {
      return [];
    }
  }

  function paperIdFor(payload) {
    return String(payload.paper_id || "").trim();
  }

  function arrayValue(value) {
    return Array.isArray(value) ? value : [];
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDailyFeedback, { passive: true });
  } else {
    initDailyFeedback();
  }
})();
