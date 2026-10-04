/** Client-safe consultant contract. Never put prompts, knowledge or secrets here. */

export const CONSULTANT_ENDPOINT = "/api/consultant";
export const MAX_MESSAGE_CHARS = 500;
export const MAX_HISTORY_MESSAGES = 10;
export const MAX_HISTORY_CHARS = 6000;
export const MAX_ASSISTANT_CHARS = 2000;

export type ConsultantRole = "user" | "assistant";

export type ConsultantTurn = {
  role: ConsultantRole;
  text: string;
};

export type ConsultantRequestBody = {
  message: string;
  history: ConsultantTurn[];
};

export type ConsultantReply = {
  text: string;
  cta: boolean;
};

export type ConsultantErrorCode =
  | "invalid_request"
  | "forbidden"
  | "payload_too_large"
  | "rate_limited"
  | "unavailable";

export type ConsultantErrorBody = { error: ConsultantErrorCode };
