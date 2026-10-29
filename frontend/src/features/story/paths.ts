// URLs of the Story Bible pages.

export const paths = {
  play: "/play",
  act: (n: number) => `/play/acts/${n}`,
  /** Pattern for matchPath / the route table. */
  actPattern: "/play/acts/:n",
} as const;
