import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "./AppLayout";

import { LandingPage } from "@/pages/LandingPage/LandingPage";
import { AuthCallbackPage } from "@/pages/AuthCallbackPage/AuthCallbackPage";
import { DashboardPage } from "@/pages/DashboardPage/DashboardPage";
import { ReposPage } from "@/pages/ReposPage/ReposPage";
import { RepoDetailPage } from "@/pages/RepoDetailPage/RepoDetailPage";
import { TasksPage } from "@/pages/TasksPage/TasksPage";
import { TaskDetailPage } from "@/pages/TaskDetailPage/TaskDetailPage";
import { ContributorPage } from "@/pages/ContributorPage/ContributorPage";
import { ContributorsPage } from "@/pages/ContributorsPage/ContributorsPage";

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/auth/callback", element: <AuthCallbackPage /> },
  {
    element: <AppLayout />,
    children: [
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/repos", element: <ReposPage /> },
      { path: "/repos/:owner/:repo", element: <RepoDetailPage /> },
      { path: "/tasks", element: <TasksPage /> },
      { path: "/tasks/:taskId", element: <TaskDetailPage /> },
      { path: "/contributors", element: <ContributorsPage /> },
      { path: "/contributors/:githubLogin", element: <ContributorPage /> },
      { path: "*", element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);
