import { apiClient } from "../../shared/api/client";

/**
 * Fetch all students who have submitted PRs to a repository.
 * Returns one entry per pr_author with aggregated stats.
 * @param {string} owner
 * @param {string} repo
 * @returns {Promise<Array>}
 */
export async function fetchRepoStudents(owner, repo) {
  return apiClient.get(`/api/repos/${owner}/${repo}/students`);
}

/**
 * Fetch all students across ALL repositories of the professor,
 * including average score (0-10) and global submission counts.
 * @returns {Promise<Array>}
 */
export async function fetchAllStudents() {
  return apiClient.get("/api/students");
}

/**
 * Fetch per-repository score breakdown for a student.
 * Returns best score, pass/partial/fail counts per repo.
 * @param {string} githubLogin
 * @returns {Promise<Object>}
 */
export async function fetchStudentSummary(githubLogin) {
  return apiClient.get(
    `/api/students/${encodeURIComponent(githubLogin)}/summary`,
  );
}

/**
 * Fetch all evaluation tasks for a student across all of the
 * authenticated professor's repositories.
 * @param {string} githubLogin
 * @param {{ page?: number, pageSize?: number, repositoryFullName?: string, status?: string }} params
 */
export async function fetchStudentTasks(githubLogin, params = {}) {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", params.page);
  if (params.pageSize) qs.set("page_size", params.pageSize);
  if (params.repositoryFullName)
    qs.set("repository_full_name", params.repositoryFullName);
  if (params.status) qs.set("status", params.status);
  const query = qs.toString() ? `?${qs}` : "";
  return apiClient.get(
    `/api/students/${encodeURIComponent(githubLogin)}/tasks${query}`,
  );
}
