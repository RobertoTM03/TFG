export function parseOwnerRepo(fullName) {
  const [owner, repo] = (fullName ?? "").split("/");
  return { owner, repo };
}

export function getInstallUrl(appSlug) {
  return `https://github.com/apps/${appSlug}/installations/new`;
}

export function getRepoUrl(fullName) {
  return `https://github.com/${fullName}`;
}
