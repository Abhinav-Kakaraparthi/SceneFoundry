const credentialKey = "scenefoundry.googleCredential";

export function readCredential(): string | null {
  const credential = window.sessionStorage.getItem(credentialKey);
  return credential?.trim() || null;
}

export function saveCredential(credential: string): void {
  const normalized = credential.trim();
  if (!normalized) {
    throw new Error("Google credential cannot be empty.");
  }
  window.sessionStorage.setItem(credentialKey, normalized);
}

export function clearCredential(): void {
  window.sessionStorage.removeItem(credentialKey);
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const credential = readCredential();
  const headers = new Headers(init.headers);

  if (credential) {
    headers.set("Authorization", `Bearer ${credential}`);
  }

  const response = await window.fetch(input, {
    ...init,
    headers,
  });

  if (response.status === 401 && credential) {
    clearCredential();
    window.dispatchEvent(new Event("scenefoundry:unauthorized"));
  }

  return response;
}
