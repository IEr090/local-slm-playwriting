// Long requests the user started that a page reload would cancel (the backend stops when the request is
// cancelled): they are remembered in the tab, so the provider can start them again after the reload.

const KEY = "anton.story.resumable";

/** "text:N" (writing the text of act N) or "record:N" (approving it). */
export type ResumableJob = `text:${number}` | `record:${number}`;

export function resumableJobs(): ResumableJob[] {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? "[]") as ResumableJob[];
  } catch {
    return [];
  }
}

function store(jobs: ResumableJob[]) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(jobs));
  } catch {
    // without storage a reload simply does not resume
  }
}

export function rememberJob(job: ResumableJob) {
  store([...resumableJobs().filter((item) => item !== job), job]);
}

export function forgetJob(job: ResumableJob) {
  store(resumableJobs().filter((item) => item !== job));
}

export function forgetAllJobs() {
  store([]);
}
