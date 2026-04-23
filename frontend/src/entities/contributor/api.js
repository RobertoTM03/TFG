import { apiClient } from "@/shared/api/client";

export async function fetchRepoContributors(owner, repo) {
  return apiClient.get(`/api/repos/${owner}/${repo}/contributors`);
}

export async function fetchAllContributors() {
  return apiClient.get("/api/contributors");
}

export async function fetchContributorSummary(githubLogin) {
  return apiClient.get(
    `/api/contributors/${encodeURIComponent(githubLogin)}/summary`,
  );
}

export async function fetchContributorTasks(githubLogin, params = {}) {
  const { page = 1, pageSize = 10, repositoryFullName, status } = params;
  const query = new URLSearchParams({ page, page_size: pageSize });
  if (repositoryFullName) query.set("repository_full_name", repositoryFullName);
  if (status) query.set("status", status);
  return apiClient.get(
    `/api/contributors/${encodeURIComponent(githubLogin)}/tasks?${query}`,
  );
}
