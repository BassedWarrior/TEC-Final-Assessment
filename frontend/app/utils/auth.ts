import { redirect } from "react-router"

export async function requireAuth() {
  try {
    const res = await fetch("/api/auth/me", {
      credentials: "include", // sends the httpOnly cookie automatically
    })
    if (!res.ok) throw new Error("Unauthorized")
    return await res.json()
  } catch {
    throw redirect("/login")
  }
}