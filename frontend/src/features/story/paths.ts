// URLs of the Story Bible pages.

export const paths = {
  play: "/play",
  /** The whole finished play to read and edit. */
  read: "/play/read",
  act: (n: number) => `/play/acts/${n}`,
  /** Pattern for matchPath / the route table. */
  actPattern: "/play/acts/:n",
} as const;
