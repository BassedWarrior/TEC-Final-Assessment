# Frontend

React Router v7 single-page application for the MLB Baseball Game Simulator. Provides a UI for browsing the weekly schedule, exploring player stats, running custom game simulations, and reviewing simulation history.

## Technology Stack

| Library | Purpose |
|---|---|
| **React 19** | UI framework |
| **React Router v7** | File-based routing + SSR support |
| **TypeScript** | Static typing |
| **TailwindCSS v4** | Utility-first styling |
| **Recharts** | Win-probability and per-inning stat graphs |
| **Vite** | Build tool and dev server |

---

## Project Structure

```
frontend/
├── app/
│   ├── root.tsx                  # App shell, global layout, UserContext provider
│   ├── routes.ts                 # Route definitions (React Router v7 config)
│   ├── app.css                   # Global styles
│   ├── styles/
│   │   └── theme.css             # CSS custom properties / design tokens
│   ├── routes/
│   │   ├── home.tsx              # Landing page (/)
│   │   ├── dashboard.tsx         # Public predictions dashboard (/dashboard)
│   │   ├── sandbox.tsx           # Custom simulation builder (/sandbox)
│   │   ├── player_stats.tsx      # Player statistics viewer (/statistics)
│   │   ├── history.tsx           # User's simulation history (/history)
│   │   ├── login.tsx             # Login (/login)
│   │   └── register.tsx          # Registration (/register)
│   ├── components/
│   │   ├── Sidebar.tsx           # Navigation sidebar
│   │   └── Graphs.tsx            # Recharts win-probability and inning graphs
│   ├── contexts/
│   │   └── UserContext.tsx       # Global user state + logout helper
│   ├── api/
│   │   ├── simulate.ts           # POST /simulations/simulate
│   │   ├── simulations.ts        # GET /simulations/history + /simulations/dashboard
│   │   ├── playerStats.ts        # GET /players/player-stats
│   │   └── schedule.ts           # GET /schedule
│   └── utils/
│       └── auth.ts               # requireAuth() server-side loader guard
├── public/
│   ├── favicon.ico
│   └── images/                   # Page background images
├── Dockerfile                    # Multi-stage Docker image
├── react-router.config.ts        # React Router build config
├── vite.config.ts                # Vite config with TailwindCSS plugin
├── tsconfig.json
├── package.json
├── .env.example
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```env
PORT=5173

# URL the browser uses to reach the API (public-facing)
VITE_API_URL=http://localhost:8000

# URL SSR loaders use to reach the API (server-side, bypasses Nginx/proxy)
# Only needed when the public URL is not reachable from the server process
VITE_INTERNAL_API_URL=http://localhost:8000
```

`VITE_API_URL` is embedded in the client bundle at build time. `VITE_INTERNAL_API_URL` is read at runtime by SSR loaders on the Node server — set it to the direct backend address when the backend is behind a proxy that isn't reachable server-side (common in multi-VM deployments).

---

## Installation

```bash
cd frontend
npm install
cp .env.example .env     # fill in VITE_API_URL
```

### Development server

```bash
npm run dev              # starts Vite with HMR at http://localhost:5173
```

### Production build

```bash
npm run build            # outputs to frontend/build/
npm run start            # serves SSR build on $PORT (default 3000)
```

### Type checking

```bash
npm run typecheck        # runs react-router typegen then tsc --noEmit
```

---

## Routes

| Path | Component | Auth required | Description |
|---|---|---|---|
| `/` | `home.tsx` | No | Landing page |
| `/dashboard` | `dashboard.tsx` | No | Public game predictions from the DB |
| `/statistics` | `player_stats.tsx` | No | Full 2024 MLB player stat table |
| `/sandbox` | `sandbox.tsx` | Yes | Custom lineup builder + simulation runner |
| `/history` | `history.tsx` | Yes | Previously run simulations for this user |
| `/login` | `login.tsx` | No | Login form |
| `/register` | `register.tsx` | No | Registration form |

Protected routes use `requireAuth(request)` in their loader, which reads the `access_token` cookie server-side and redirects to `/login` if absent or invalid.

---

## Pages

### Home (`/`)

Landing page with a brief project description and navigation to the main features.

### Dashboard (`/dashboard`)

Fetches pre-seeded match records from `GET /simulations/dashboard`. Displays:

- Win probability for each team
- Expandable per-inning stat graphs (runs, hits, HRs, strikeouts)
- Overall game averages table

No login required — intended for public access.

### Sandbox (`/sandbox`)

Interactive lineup builder. Requires authentication.

1. Fetches all batters and pitchers from `GET /players/player-stats`.
2. User searches and filters the player pool, then assigns 9 batters and a starting pitcher to each team.
3. Optional bullpen slots can be added.
4. On submit, calls `POST /simulations/simulate` with the assembled player IDs.
5. Displays the returned win probabilities and per-inning graphs using `<Graphs />`.

### Statistics (`/statistics`)

Fetches the full player roster and renders a sortable, searchable table of 2024 batting and pitching stats. Toggle between batters and pitchers with a tab switch.

Stats shown: `AVG`, `OBP`, `SLG`, `ISO`, `K%`, `BB%`, `HR%`, `PA count`.

### History (`/history`)

Fetches the authenticated user's simulation records from `GET /simulations/history`. Each card shows the team names, win probabilities, and an expandable graph of per-inning averages.

### Login / Register

Standard email + password forms. On success, the backend sets an httpOnly cookie and the `UserContext` is refreshed via `GET /auth/me`.

---

## Authentication

The application uses **httpOnly cookie** authentication. No JWT is stored in localStorage or sessionStorage.

### `UserContext` (`app/contexts/UserContext.tsx`)

Wraps the entire app. On mount it calls `GET /auth/me` with `credentials: "include"` to check for an existing session.

Provides:
- `user` — current user object or `null`
- `loading` — `true` while the initial `/auth/me` fetch is in-flight
- `refetchUser()` — re-run the `/auth/me` check (called after login/register)
- `logout()` — calls `POST /auth/logout` then clears local user state

### `requireAuth` (`app/utils/auth.ts`)

Used in route `loader` functions to enforce authentication server-side:

```ts
export async function loader({ request }: LoaderFunctionArgs) {
  await requireAuth(request);
  // ... fetch protected data
}
```

If the user is not authenticated it throws a redirect to `/login`.

---

## API Integration

All API calls go to `VITE_API_URL` (or `VITE_INTERNAL_API_URL` for SSR loaders) with `credentials: "include"` so the browser forwards the httpOnly cookie.

### `api/simulate.ts`

```ts
postSimulate(payload: SimulateRequest): Promise<MatchResponse>
```

### `api/simulations.ts`

```ts
getHistory(): Promise<MatchResponse[]>
getDashboard(): Promise<MatchResponse[]>
```

### `api/playerStats.ts`

```ts
getPlayerStats(isBatter?: boolean): Promise<PlayerResponse[]>
```

### `api/schedule.ts`

```ts
getSchedule(startDate?: string, endDate?: string): Promise<ScheduleResponse>
```

---

## Components

### `<Sidebar />`

Navigation sidebar with links to all main routes. Highlights the active route. Shows the current user's email and a logout button when authenticated.

### `<Graphs />`

Recharts-based visualization component. Accepts an array of inning objects and renders:

- A line chart of cumulative runs per inning (home vs. away)
- A bar chart of per-inning strikeouts and hits

---

## Docker

A multi-stage Dockerfile is provided (`frontend/Dockerfile`). It:

1. Installs all dev dependencies and runs `npm run build`.
2. Assembles a minimal production image with only the runtime Node modules and the built output.
3. Runs `npm run start` (`react-router-serve`) on port `3000`.

```bash
docker build -t baseball-frontend .
docker run -d -p 3000:3000 \
  -e VITE_API_URL=http://your-backend:8000 \
  baseball-frontend
```

> `VITE_API_URL` must be set at **build time** when using Vite's `import.meta.env` — pass it as a `--build-arg` or bake it into the `.env` before building if the URL is known ahead of time. For runtime injection, consider server-side env forwarding via `VITE_INTERNAL_API_URL`.

---

## Troubleshooting

**API requests fail with CORS error**
Ensure `FRONTEND_URL` in `backend/.env` includes the origin the browser is using (e.g. `http://localhost:5173`).

**Redirected to `/login` even after logging in**
The cookie domain must match the frontend origin. In local dev both must run on `localhost`. In production, both must be on the same domain or the cookie must be set with the correct `Domain` attribute.

**`npm run typecheck` fails with route type errors**
Run `npm run typecheck` once more — `react-router typegen` generates `.react-router/types/` on the first pass, and `tsc` needs those types on the second pass. The combined command handles this.
