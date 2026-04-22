import { apiClient } from "@/shared/api/client";

export function fetchRepos() {
  return apiClient.get("/api/repos");
}

export function fetchInstallations() {
  return apiClient.get("/api/installations");
}

export function fetchAppInfo() {
  return apiClient.get("/api/app-info");
}
