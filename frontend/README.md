# MLB Prediction App - Frontend

This is the frontend application for the MLB Prediction System. It provides an interface for viewing game predictions, simulating matchups, browsing player statistics, and managing simulation history.

## Technology Stack

- React 18 with TypeScript
- React Router v6 for navigation
- Vite for build tooling and development server
- Custom CSS

## Pages

### Dashboard
Displays MLB game predictions for the current week. Shows upcoming games with win probability percentages, team matchups, dates, and times. Features include:
- Sortable game list by probability
- Expandable game details with inning-by-inning graphs
- Live game status indicators
- Summary statistics (games this week, live games, model accuracy)

### Sandbox
Interactive lineup builder that allows users to simulate custom matchups. Features include:
- Drag-and-drop player pool with search and filtering
- Build complete 9-player batting orders for home and away teams
- Configure pitching staffs (add/remove pitcher slots)
- Run simulations to generate game results
- View simulated inning-by-inning graphs

### Statistics
Comprehensive player statistics viewer for all MLB players. Features include:
- Toggle between batters and pitchers views
- Sortable columns (AVG, OBP, SLG, ISO, K%, BB%, etc.)
- Search by player name or team
- Filter by team or experience (rookie/veteran)
- Detailed player panel with advanced metrics on click
- Summary statistics showing league averages

### History
Obtains past player simulations from the data base
- Stores and display previously run sandbox simulations for later review and analysis

## Prerequisites

- Node.js 18 or higher
- npm or yarn package manager
- Backend server running on port 8000 (or configured endpoint)

## Installation

1. Clone the repository and navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

or

```bash
yarn install
```

3. Create a `.env` file in the root of the frontend directory:

```bash
VITE_API_URL=http://localhost:8000
```

## Running the Development Server

Start the development server:

```bash
npm run dev
```

or

```bash
yarn dev
```

The application will be available at `http://localhost:5173` (default vite port ) but can be also accessed through the network address which will be shown inside the terminal once the server is running.

## Building for Production

Create a production build:

```bash
npm run build
```

or

```bash
yarn build
```

The built files will be in the `dist` directory.

## Preview Production Build

To preview the production build locally:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API service modules
│   │   ├── schedule.ts   # Schedule API endpoints
│   │   └── playerStats.ts # Player statistics endpoints
│   ├── components/       # Reusable UI components
│   │   ├── Layout/       # Page layout components
│   │   └── Graphs.tsx    # Game visualization component
│   ├── data/             # Static data and types
│   │   ├── mockData.ts   # Mock game data (fallback)
│   │   ├── mockPlayers.ts # Mock player data (fallback)
│   │   └── teamMeta.ts   # Team metadata (abbreviations, colors)
│   ├── pages/            # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Sandbox.tsx
│   │   ├── Statistics.tsx
│   │   ├── History.tsx
│   │   ├── Login.tsx
│   │   └── Register.tsx
│   ├── utils/            # Utility functions
│   │   ├── auth.ts       # Authentication helpers
│   └── main.tsx          # Application entry point
├── public/               # Static assets
├── .env                  # Environment variables
├── index.html            # HTML template
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── vite.config.ts        # Vite configuration
```

## API Endpoints

The frontend expects the following backend endpoints:

- `GET /schedule` - Returns weekly MLB game schedule
- `GET /players/player-stats` - Returns player statistics (batters and pitchers)
- `POST /auth/login` - User authentication
- `POST /auth/register` - User registration
- `GET /auth/me` - Get current user information
- `POST /simulations/simulate` - Simulate a match using the model
- `GET /simulations/history` - Get current users previous simulations

## Authentication

The application uses cookie-based authentication. The `requireAuth` utility function protects routes that require a logged-in user. Login, registration and Dashboard pages are publicly accessible.