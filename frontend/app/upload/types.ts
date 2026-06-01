export interface FileItem {
  name: string;
  type: "file" | "dir";
  size?: number;
  url?: string;
  is_gallery?: boolean;
  path: string;
  title?: string;
  description?: string;
  date?: string;
  author?: string;
}

export function getIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  return ["jpg", "jpeg", "png", "gif", "webp"].includes(ext) ? "img" : "file";
}
