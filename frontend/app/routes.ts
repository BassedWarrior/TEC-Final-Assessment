import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("dashboard", "routes/dashboard.tsx"),
  route("login", "routes/login.tsx"),
  route("statistics", "routes/player_stats.tsx"),
  route("register", "routes/create_account.tsx")
] satisfies RouteConfig;