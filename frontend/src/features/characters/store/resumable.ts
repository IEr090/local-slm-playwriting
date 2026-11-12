// The cast generation is remembered in the tab: a page reload cancels the request (the backend stops when
// the request is cancelled), so the provider can start it again after the reload.

const KEY = "anton.cast.generation";

export interface PendingGeneration {
  premise: string;
  /** The cast is generated and saved; only the animation of the names was left. */
  answered: boolean;
}

export function pendingGeneration(): PendingGeneration | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as PendingGeneration) : null;
  } catch {
    return null;
  }
}

export function rememberGeneration(generation: PendingGeneration) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(generation));
  } catch {
    // without storage a reload simply does not resume
  }
}

export function forgetGeneration() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // nothing was stored
  }
}
