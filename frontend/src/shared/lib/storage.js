export function getToken() {
  return localStorage.getItem("auth_token");
}

export function setToken(token) {
  localStorage.setItem("auth_token", token);
}

export function removeToken() {
  localStorage.removeItem("auth_token");
}

export function getRepoSettings(owner, repo) {
  const key = `repo_settings_${owner}_${repo}`;
  try {
    return JSON.parse(localStorage.getItem(key)) ?? defaultRepoSettings();
  } catch {
    return defaultRepoSettings();
  }
}

export function setRepoSettings(owner, repo, settings) {
  const key = `repo_settings_${owner}_${repo}`;
  localStorage.setItem(key, JSON.stringify(settings));
}

export function defaultRepoSettings() {
  return {
    maxEvaluationsPerPR: 3,
    approvalThreshold: 0.8,
    enableCrossCheck: true,
    notifyOnFail: true,
  };
}
