import type { Metadata } from "next";
import { ResumeView } from "@/components/resume-view";

export const metadata: Metadata = {
  title: "Resume",
  description: "Resume of Yixun Hong — undergraduate student at Zhejiang University majoring in Information Security.",
};

export default function ResumePage() {
  return <ResumeView />;
}
