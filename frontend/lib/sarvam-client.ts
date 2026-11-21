import type {
  SarvamAnalysisRequest,
  SarvamAnalysisResponse,
} from "./types";

export async function getSarvamAnalysis(
  request: SarvamAnalysisRequest,
): Promise<SarvamAnalysisResponse> {
  const response = await fetch("/api/sarvam/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  const body = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof body.error === "string" ? body.error : "Sarvam analysis failed.",
    );
  }

  return body as SarvamAnalysisResponse;
}