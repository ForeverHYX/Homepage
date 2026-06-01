import { unstable_cache } from "next/cache";
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
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const getHomePayload = unstable_cache(
  async () => requestJson<HomePayload>("/api/site/home"),
  ["home"],
  { revalidate: REVALIDATE_SECONDS }
);

export const getArticlesPayload = unstable_cache(
  async (tag?: string) => {
    const query = tag ? `?tag=${encodeURIComponent(tag)}` : "";
    return requestJson<ArticlesPayload>(`/api/site/articles${query}`);
  },
  ["articles"],
  { revalidate: REVALIDATE_SECONDS, tags: ["articles"] }
);

// Gallery: NO caching — always fetch fresh data from backend.
// Combined with `export const dynamic = "force-dynamic"` in page.tsx,
// this ensures /gallery always shows up-to-date data after star/unstar toggles.
export async function getGalleryPayload(focus?: string): Promise<GalleryPayload> {
  const query = focus ? `?focus=${encodeURIComponent(focus)}` : "";
  return requestJson<GalleryPayload>(`/api/site/gallery${query}`);
}

export const getArticleDetailPayload = unstable_cache(
  async (slug: string) =>
    requestJson<ArticleDetailPayload>(
      `/api/site/articles/${encodeURIComponent(slug)}`
    ),
  ["article-detail"],
  { revalidate: REVALIDATE_SECONDS }
);
