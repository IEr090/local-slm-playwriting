// Route table of the Character Creator. The app combines the routes of every feature.

import type { RouteObject } from "react-router";
import { DetailPage } from "./pages/detail/DetailPage";
import { GeneratingPage } from "./pages/generating/GeneratingPage";
import { GridPage } from "./pages/grid/GridPage";
import { PromptPage } from "./pages/prompt/PromptPage";
import { paths } from "./paths";

export const characterRoutes: RouteObject[] = [
  { path: paths.prompt, element: <PromptPage /> },
  { path: paths.generating, element: <GeneratingPage /> },
  { path: paths.cast, element: <GridPage /> },
  { path: paths.characterPattern, element: <DetailPage /> },
];
