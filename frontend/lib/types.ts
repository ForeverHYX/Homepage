export type HomePayload = {
  about: {
    email: string;
    github: string;
    location: string;
    name: string;
    role: string;
  };
  avatar_url: string;
  sections: Array<{
    title: string;
    body_html: string;
    accent_color: string;
  }>;
  sections_html: string;
  news_html: string;
  all_news_html: string;
};

export type ArticleSummary = {
  slug: string;
  title: string;
  date: string;
  author: string;
  summary: string;
  tags: string[];
  mtime?: number;
};

export type ArticlesPayload = {
  articles: ArticleSummary[];
  filter_tags: string[];
  sorted_tags: Array<[string, number]>;
};

export type DailyItem = {
  id: string;
  rank: number;
  item_type: "paper" | "repository";
  type_label: string;
  title: string;
  abstract: string;
  authors: string[];
  display_authors: string[];
  categories: string[];
  section: string;
  section_label: string;
  keywords: string[];
  tldr: string;
  paper_url: string;
  pdf_url: string;
  code_urls: string[];
  code_search_url: string;
  repository_full_name: string;
  repository_description: string;
  repository_url: string;
  repository_homepage: string;
  repository_topics: string[];
  repository_stars: number;
  display_repository_stars: string;
  repository_forks: number;
  display_repository_forks: string;
  repository_stars_today: number;
  repository_language: string;
  paper_links: Array<{
    label: string;
    url: string;
  }>;
  score: number;
  ai_score?: number;
};

export type DailyPayload = {
  run_date: string;
  source_url: string;
  items: DailyItem[];
  filter_keywords: string[];
  active_item_type: "" | "paper" | "repository";
  sorted_keywords: Array<[string, number]>;
  feedback_config: {
    supabase_url?: string;
    supabase_anon_key?: string;
  };
};

export type GalleryAlbum = {
  path_name: string;
  rel_path: string;
  title: string;
  desc: string;
  date_str: string;
  author: string;
  images: string[];
  full_images: string[];
  sort_ts: number;
  title_style: string;
  meta_style: string;
  desc_style: string;
  card_padding: string;
  card_margin: string;
  nav_margin: string;
  wrapper_class: string;
};

export type GalleryPayload = {
  albums: GalleryAlbum[];
  is_focused: boolean;
  focus: string | null;
};

export type ArticleDetailPayload = {
  slug: string;
  title: string;
  html_body: string;
  toc_html: string;
  date_str: string;
  author: string;
  word_count: number;
  read_time: number;
  tags_html: string;
  tags: string[];
  icon_clock: string;
};

export type SearchEntry = {
  type: string;
  title: string;
  desc: string;
  tags?: string[];
  date: string;
  url: string;
};
