"use client";

import { useEffect, useState } from "react";
import type { DailyItem, DailyPayload } from "@/lib/types";

type DailyActionsProps = {
  item: DailyItem;
  feedbackConfig: DailyPayload["feedback_config"];
  runDate: string;
};

type FeedbackRating = "like" | "dislike";
type FeedbackUiState = {
  likes: Record<string, string[]>;
  hidden: Record<string, string[]>;
};

const localFeedbackKey = "homepage_daily_feedback_events";
const feedbackUiStateKey = "homepage_daily_feedback_ui_state";

export function DailyActions({ item, feedbackConfig, runDate }: DailyActionsProps) {
  const [feedbackState, setFeedbackState] = useState<FeedbackRating | "">("");
  const [busy, setBusy] = useState<FeedbackRating | "">("");

  useEffect(() => {
    const state = readFeedbackUiState();
    const id = item.id;
    if ((state.hidden[runDate] || []).includes(id)) {
      hideParentCard(id);
      return;
    }
    if ((state.likes[runDate] || []).includes(id)) {
      setFeedbackState("like");
    }
  }, [item.id, runDate]);

  const submitFeedback = async (rating: FeedbackRating) => {
    if (rating === "like" && feedbackState === "like") return;
    setBusy(rating);
    const event = {
      paper_id: item.id,
      rating,
      source: "page",
      section: item.section || null,
      title: item.title,
      abstract: item.abstract,
      authors: item.authors,
      affiliations: [],
      categories: item.categories,
      item_type: item.item_type,
      repository_url: item.repository_url || null,
      paper_links: item.paper_links,
    };

    try {
      await postFeedback(feedbackConfig, event);
    } catch {
      storeLocalFeedback(event);
    } finally {
      markFeedbackState(item.id, rating, runDate);
      setFeedbackState(rating);
      if (rating === "dislike") hideParentCard(item.id);
      setBusy("");
    }
  };

  const codeUrl = item.code_urls[0] || item.repository_url;

  return (
    <div className="daily-actions">
      {item.item_type === "paper" && item.pdf_url ? (
        <a className="daily-action-button action-glass daily-action-pdf" href={item.pdf_url} target="_blank" rel="noreferrer">
          <span className="daily-action-icon"><PdfIcon /></span>
          <span className="daily-action-label">PDF</span>
        </a>
      ) : null}
      {item.item_type === "repository" && codeUrl ? (
        <a className="daily-action-button action-glass daily-action-code" href={codeUrl} target="_blank" rel="noreferrer">
          <span className="daily-action-icon"><CodeIcon /></span>
          <span className="daily-action-label">Code</span>
        </a>
      ) : null}
      <button
        type="button"
        className={`daily-action-button action-glass feedback daily-action-like${feedbackState === "like" ? " is-active" : ""}`}
        onClick={() => submitFeedback("like")}
        disabled={Boolean(busy)}
      >
        <span className="daily-action-icon"><LikeIcon /></span>
        <span className="daily-action-label">{busy === "like" ? "Saving..." : feedbackState === "like" ? "Liked" : "Like"}</span>
      </button>
      <button
        type="button"
        className="daily-action-button action-glass feedback daily-action-dislike"
        onClick={() => submitFeedback("dislike")}
        disabled={Boolean(busy)}
      >
        <span className="daily-action-icon"><DislikeIcon /></span>
        <span className="daily-action-label">{busy === "dislike" ? "Saving..." : "Dislike"}</span>
      </button>
    </div>
  );
}

function PdfIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M9 15h6" />
      <path d="M9 18h3" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function LikeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 10v11" />
      <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h3l3.92-6.26A2 2 0 0 1 14.65 5" />
    </svg>
  );
}

function DislikeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 14V3" />
      <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-3l-3.92 6.26A2 2 0 0 1 9.35 19" />
    </svg>
  );
}

async function postFeedback(
  feedbackConfig: DailyPayload["feedback_config"],
  event: Record<string, unknown>,
) {
  const supabaseUrl = feedbackConfig?.supabase_url;
  const supabaseAnonKey = feedbackConfig?.supabase_anon_key;
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error("Supabase config unavailable");
  }

  const response = await postSupabaseFeedbackPayload(supabaseUrl, supabaseAnonKey, feedbackPayload(event));
  if (response.ok) return;
  const legacyResponse = await postSupabaseFeedbackPayload(supabaseUrl, supabaseAnonKey, legacyFeedbackPayload(event));
  if (!legacyResponse.ok) {
    throw new Error(`Feedback rejected: ${response.status}`);
  }
}

async function postSupabaseFeedbackPayload(
  supabaseUrl: string,
  supabaseAnonKey: string,
  payload: Record<string, unknown>,
) {
  return fetch(`${supabaseUrl.replace(/\/$/, "")}/rest/v1/feedback_events`, {
    method: "POST",
    headers: {
      apikey: supabaseAnonKey,
      Authorization: `Bearer ${supabaseAnonKey}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(payload),
  });
}

function feedbackPayload(event: Record<string, unknown>) {
  return {
    paper_id: String(event.paper_id || ""),
    rating: event.rating,
    source: event.source || "page",
    section: event.section || null,
    title: String(event.title || ""),
    abstract: String(event.abstract || ""),
    authors: Array.isArray(event.authors) ? event.authors : [],
    affiliations: Array.isArray(event.affiliations) ? event.affiliations : [],
    categories: Array.isArray(event.categories) ? event.categories : [],
    item_type: event.item_type === "repository" ? "repository" : "paper",
    repository_url: event.repository_url || null,
    paper_links: Array.isArray(event.paper_links) ? event.paper_links : [],
  };
}

function legacyFeedbackPayload(event: Record<string, unknown>) {
  return {
    paper_id: String(event.paper_id || ""),
    rating: event.rating,
    source: event.source || "page",
    section: event.section || null,
    title: String(event.title || ""),
    abstract: String(event.abstract || ""),
    authors: Array.isArray(event.authors) ? event.authors : [],
    affiliations: Array.isArray(event.affiliations) ? event.affiliations : [],
    categories: Array.isArray(event.categories) ? event.categories : [],
  };
}

function storeLocalFeedback(event: Record<string, unknown>) {
  const existing = readJsonArray(localFeedbackKey);
  localStorage.setItem(
    localFeedbackKey,
    JSON.stringify([...existing, { ...feedbackPayload(event), created_at: new Date().toISOString() }]),
  );
}

function markFeedbackState(itemId: string, rating: FeedbackRating, runDate: string) {
  const state = readFeedbackUiState();
  state.likes[runDate] = state.likes[runDate] || [];
  state.hidden[runDate] = state.hidden[runDate] || [];
  state.likes[runDate] = state.likes[runDate].filter((value) => value !== itemId);
  state.hidden[runDate] = state.hidden[runDate].filter((value) => value !== itemId);
  if (rating === "like") state.likes[runDate].push(itemId);
  if (rating === "dislike") state.hidden[runDate].push(itemId);
  localStorage.setItem(feedbackUiStateKey, JSON.stringify(state));
}

function readFeedbackUiState(): FeedbackUiState {
  try {
    const state = JSON.parse(localStorage.getItem(feedbackUiStateKey) || "{}");
    return {
      likes: state && typeof state.likes === "object" && !Array.isArray(state.likes) ? state.likes : {},
      hidden: state && typeof state.hidden === "object" && !Array.isArray(state.hidden) ? state.hidden : {},
    };
  } catch {
    return { likes: {}, hidden: {} };
  }
}

function readJsonArray(key: string) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function hideParentCard(itemId: string) {
  const card = document.getElementById(`paper-${itemId.replace(/[/:]/g, "-")}`);
  if (!card) return;
  card.classList.add("is-feedback-hidden");
  card.hidden = true;
}
