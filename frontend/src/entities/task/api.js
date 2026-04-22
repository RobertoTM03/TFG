import { apiClient } from "@/shared/api/client";

export function fetchTasks(params = {}) {
  const query = new URLSearchParams({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 10,
    sort_by: params.sortBy ?? "created_at",
    sort_order: params.sortOrder ?? "desc",
    ...(params.repositoryFullName
      ? { repository_full_name: params.repositoryFullName }
      : {}),
  }).toString();
  return apiClient.get(`/api/tasks?${query}`);
}

export function fetchTask(taskId) {
  return apiClient.get(`/api/tasks/${taskId}`);
}

export function triggerValidation(owner, repo, crossCheck = true) {
  return apiClient.post(
    `/api/repos/${owner}/${repo}/validate?cross_check=${crossCheck}`,
    {},
  );
}
