export function getUserInitials(user) {
  if (!user) return "?";
  return user.github_login?.slice(0, 2).toUpperCase() ?? "?";
}

export function getUserDisplayName(user) {
  return user?.github_login ?? "Unknown";
}
