export function getToken() {
  return localStorage.getItem("auth_token");
}

export function setToken(token) {
  localStorage.setItem("auth_token", token);
}

export function removeToken() {
  localStorage.removeItem("auth_token");
}

