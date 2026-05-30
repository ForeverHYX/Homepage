import type { Metadata } from "next";
import UploadManager from "./upload-client";

export const metadata: Metadata = {
  title: "Upload",
};

export default function UploadPage() {
  return <UploadManager />;
}
