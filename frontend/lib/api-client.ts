import type { Analysis } from "./types";

export function getApiUrl(): string | null {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  return apiUrl ?? null;
}

export async function postAnalyze(payload: FormData): Promise<Analysis> {
  const apiUrl = getApiUrl();
  if (!apiUrl) {
    throw new Error("The analysis API is not configured.");
  }
  const response = await fetch(`${apiUrl}/analyze`, {
    method: "POST",
    body: payload,
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail ?? "Analysis failed. Please check the images and try again.");
  }
  return body as Analysis;
}