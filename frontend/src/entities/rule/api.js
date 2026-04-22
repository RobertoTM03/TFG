import { apiClient } from "@/shared/api/client";

export function fetchRules(owner, repo, params = {}) {
  const query = new URLSearchParams({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    sort_by: params.sortBy ?? "position",
    sort_order: params.sortOrder ?? "asc",
  }).toString();
  return apiClient.get(`/api/repos/${owner}/${repo}/rules?${query}`);
}

export function createRule(owner, repo, ruleText) {
  return apiClient.post(`/api/repos/${owner}/${repo}/rules`, {
    rule_text: ruleText,
  });
}

export function deleteRule(owner, repo, ruleId) {
  return apiClient.delete(`/api/repos/${owner}/${repo}/rules/${ruleId}`);
}
