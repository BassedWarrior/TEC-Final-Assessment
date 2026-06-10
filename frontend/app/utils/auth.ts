import { redirect } from "react-router"

export async function requireAuth(request: Request) {
  const cookieHeader = request.headers.get("Cookie")

  try {
    const res = await fetch("http://localhost:8000/auth/me", {
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