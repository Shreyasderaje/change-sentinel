import { NextResponse } from "next/server";

export const runtime = "nodejs";

const SARVAM_API_URL = "https://api.sarvam.ai/v1/chat/completions";
const SARVAM_MODEL = "sarvam-105b";

interface SarvamAnalyzeRequest {
  regions: Array<{
    region_id: number;
    bbox_xywh: number[];
    centroid_xy: number[];
    area_pixels: number;
    pixel_count: number;
    mean_difference: number;
    centroid_lonlat: number[] | null;
  }>;
  stats: {
    candidate_region_count: number;
    changed_pixels: number;
    percent_flagged: number;
    mean_difference: number;
    max_difference: number;
    total_pixels: number;
  };
  geo_note: string;
  alignment_note: string;
}

interface SarvamAnalyzeResponse {
  summary: string;
  risk_assessment: string;
  recommended_actions: string[];
}

function safeErrorMessage(message: string): string {
  // Never leak raw upstream error details to the client
  if (message.includes("api-subscription-key") || message.includes("SARVAM_API_KEY")) {
    return "Authentication with the analysis service failed.";
  }
  if (message.includes("401") || message.includes("unauthorized")) {
    return "Authentication with the analysis service failed.";
  }
  if (message.includes("429") || message.includes("rate limit")) {
    return "The analysis service is rate-limited. Please try again later.";
  }
  if (message.includes("500") || message.includes("502") || message.includes("503")) {
    return "The analysis service is temporarily unavailable. Please try again later.";
  }
  return "Failed to generate AI assessment. Please try again.";
}

export async function POST(request: Request): Promise<NextResponse> {
  const apiKey = process.env.SARVAM_API_KEY;

  if (!apiKey) {
    return NextResponse.json(
      { error: "The analysis service is not configured." },
      { status: 500 },
    );
  }

  let body: SarvamAnalyzeRequest;
  try {
    body = (await request.json()) as SarvamAnalyzeRequest;
  } catch {
    return NextResponse.json(
      { error: "Invalid request body." },
      { status: 400 },
    );
  }

  // Validate required fields
  if (
    !body ||
    !Array.isArray(body.regions) ||
    !body.stats ||
    typeof body.geo_note !== "string" ||
    typeof body.alignment_note !== "string"
  ) {
    return NextResponse.json(
      { error: "Invalid request data." },
      { status: 400 },
    );
  }

  try {
    const sarvamResponse = await fetch(SARVAM_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-subscription-key": apiKey,
      },
      body: JSON.stringify({
        model: SARVAM_MODEL,
        messages: [
          {
            role: "system",
            content:
              "You are a geospatial intelligence analyst reviewing candidate visual change detections from satellite imagery pairs. " +
              "Provide a concise, structured assessment: a summary of findings, a risk assessment, and recommended actions. " +
              "Treat all detections as candidates requiring human verification, not confirmed events. " +
              "Respond in JSON with keys: summary, risk_assessment, recommended_actions.",
          },
          {
            role: "user",
            content:
              "Analyze the following change detection results from the Change Sentinel system:\n\n" +
              JSON.stringify(body, null, 2),
          },
        ],
        max_tokens: 1024,
        temperature: 0.2,
      }),
    });

    const responseBody = await sarvamResponse.json();

    if (!sarvamResponse.ok) {
      const upstreamMessage =
        typeof responseBody.error?.message === "string"
          ? responseBody.error.message
          : JSON.stringify(responseBody);
      return NextResponse.json(
        { error: safeErrorMessage(upstreamMessage) },
        { status: 502 },
      );
    }

    const content =
      typeof responseBody.choices?.[0]?.message?.content === "string"
        ? responseBody.choices[0].message.content
        : "{}";

    let parsed: SarvamAnalyzeResponse;
    try {
      parsed = JSON.parse(content) as SarvamAnalyzeResponse;
    } catch {
      parsed = {
        summary: content,
        risk_assessment: "Unable to parse structured response.",
        recommended_actions: ["Review results manually."],
      };
    }

    return NextResponse.json(parsed);
  } catch {
    return NextResponse.json(
      { error: "Failed to connect to the analysis service." },
      { status: 502 },
    );
  }
}