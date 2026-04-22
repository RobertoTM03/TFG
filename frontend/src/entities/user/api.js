import { apiClient } from "@/shared/api/client";

export function fetchMe() {
  return apiClient.get("/auth/me");
}
