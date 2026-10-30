// Route table of the Story Bible. The app combines the routes of every feature.

import type { RouteObject } from "react-router";
import { ActPage } from "./pages/act/ActPage";
import { PlayPage } from "./pages/play/PlayPage";
import { paths } from "./paths";

export const storyRoutes: RouteObject[] = [
  { path: paths.play, element: <PlayPage /> },
  { path: paths.actPattern, element: <ActPage /> },
];
