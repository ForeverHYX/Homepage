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
  filter_tag: string | null;
  sorted_tags: Array<[string, number]>;
};

export type GalleryAlbum = {
  path_name: string;
  rel_path: string;
  title: string;
  desc: string;
  date_str: string;
  author: string;
  images: string[];
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
