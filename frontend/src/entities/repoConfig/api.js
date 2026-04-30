import { apiClient } from "@/shared/api/client";

export function fetchRepoConfig(owner, repo) {
  return apiClient.get(`/api/repos/${owner}/${repo}/config`);
}

export function saveRepoConfig(owner, repo, config) {
  return apiClient.put(`/api/repos/${owner}/${repo}/config`, config);
}

export function fetchAppInfo() {
  return apiClient.get("/api/app-info");
}
