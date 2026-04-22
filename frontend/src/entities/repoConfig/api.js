import { apiClient } from "@/shared/api/client";

export function fetchRepoConfig(owner, repo) {
  return apiClient.get(`/api/repos/${owner}/${repo}/config`);
}

export function saveRepoConfig(owner, repo, config) {
  return apiClient.put(`/api/repos/${owner}/${repo}/config`, config);
}
