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

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getHomePayload() {
  return requestJson<HomePayload>("/api/site/home");
}

export function getArticlesPayload(tag?: string) {
  const query = tag ? `?tag=${encodeURIComponent(tag)}` : "";
  return requestJson<ArticlesPayload>(`/api/site/articles${query}`);
}

export function getGalleryPayload(focus?: string) {
  const query = focus ? `?focus=${encodeURIComponent(focus)}` : "";
  return requestJson<GalleryPayload>(`/api/site/gallery${query}`);
}

export function getArticleDetailPayload(slug: string) {
  return requestJson<ArticleDetailPayload>(`/api/site/articles/${encodeURIComponent(slug)}`);
}
