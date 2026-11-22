import type { FieldReviewState, RegionReview } from "./types";

/** Immutable page-local draft update. There is deliberately no persistence call. */
export function updateReviewDraft(
  current: FieldReviewState,
  review: RegionReview,
): FieldReviewState {
  return { ...current, [review.region_id]: review };
}

export function countReviewDrafts(state: FieldReviewState) {
  const values = Object.values(state);
  return {
    reviewed: values.filter((review) => review.status !== "pending").length,
    approved: values.filter((review) => review.status === "approved").length,
    rejected: values.filter((review) => review.status === "rejected").length,
    flagged: values.filter((review) => review.status === "flagged").length,
  };
}
