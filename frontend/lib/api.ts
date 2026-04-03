import { cache } from "react";
import type {
  ArticleDetailPayload,
  ArticlesPayload,
  GalleryPayload,
  HomePayload,
} from "@/lib/types";

const API_BASE_URL =
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000";
const REVALIDATE_SECONDS = 60;

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    next: {
      revalidate: REVALIDATE_SECONDS,
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const getHomePayload = cache(async () =>
  requestJson<HomePayload>("/api/site/home")
);

export const getArticlesPayload = cache(async (tag?: string) => {
  const query = tag ? `?tag=${encodeURIComponent(tag)}` : "";
  return requestJson<ArticlesPayload>(`/api/site/articles${query}`);
});

export const getGalleryPayload = cache(async (focus?: string) => {
  const query = focus ? `?focus=${encodeURIComponent(focus)}` : "";
  return requestJson<GalleryPayload>(`/api/site/gallery${query}`);
});

export const getArticleDetailPayload = cache(async (slug: string) =>
  requestJson<ArticleDetailPayload>(
    `/api/site/articles/${encodeURIComponent(slug)}`
  )
);
