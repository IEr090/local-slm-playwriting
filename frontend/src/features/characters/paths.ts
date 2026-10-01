// URLs of the Character Creator pages.

export const paths = {
  prompt: "/",
  generating: "/generating",
  cast: "/cast",
  character: (id: string) => `/cast/${id}`,
  /** Pattern for matchPath / the route table. */
  characterPattern: "/cast/:id",
} as const;
