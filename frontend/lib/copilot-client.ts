import type { UserRole } from "./types";

export type VerifiedChatCapability = {
  investigation_id: string;
  authorized: true;
  context_verified: true;
  enabled: true;
};

export type CopilotMessage = { role: "user"; content: string };

export type CopilotRequest = {
  project_id: string;
  investigation_id: string;
  question: string;
  history: CopilotMessage[];
};

/** Fail closed unless an authenticated backend supplies capability for this exact investigation. */
export function canSendCopilotMessage(input: {
  authenticated: boolean;
  role: UserRole | null;
  investigationId: string | null;
  capability: VerifiedChatCapability | null;
}): boolean {
  const { authenticated, role, investigationId, capability } = input;
  return Boolean(
    authenticated && role && investigationId && capability?.enabled &&
    capability.authorized && capability.context_verified &&
    capability.investigation_id === investigationId,
  );
}

/** Sends identifiers and user-authored text only; the backend must assemble context. */
export function createCopilotRequest(input: {
  projectId: string;
  investigationId: string;
  question: string;
  history?: CopilotMessage[];
}): CopilotRequest {
  return {
    project_id: input.projectId,
    investigation_id: input.investigationId,
    question: input.question,
    history: input.history ?? [],
  };
}
