import { redirect } from "react-router"

const API_URL = import.meta.env.VITE_INTERNAL_API_URL ?? import.meta.env.VITE_API_URL

export async function requireAuth(request: Request) {
  const cookieHeader = request.headers.get("Cookie")

  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: {
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      },
    })
    if (!res.ok) throw redirect("/login")
    return await res.json()
  } catch (e) {
    if (e instanceof Response) throw e
    throw redirect("/login")
  }
}