import dotenv from "dotenv";
import { defineConfig } from "vite"
import { reactRouter } from "@react-router/dev/vite"

dotenv.config();
const PORT = process.env.PORT

export default defineConfig({
  plugins: [
    reactRouter(),
  ],
  server: {
    host: "0.0.0.0",
    port: PORT,
  },
  base: "/",
})