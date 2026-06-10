import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router"

const navItems = [
  { label: "Dashboard",  icon: "⊞", path: "/" },
  { label: "Statistics", icon: "≡", path: "/statistics" },
  { label: "Sandbox",   icon: "▶", path: "/sandbox" },
  { label: "History",    icon: "◷", path: "/history" },
]

interface SidebarProps {
  activePath: string
}

export default function Sidebar({ activePath }: SidebarProps) {
  const navigate = useNavigate()

  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [collapsed, setCollapsed] = useState(false)
  const sidebarRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sidebarRef.current?.parentElement) return

    const parent = sidebarRef.current.parentElement

    const observer = new ResizeObserver(entries => {
      const width = entries[0].contentRect.width

      setCollapsed(width < 1200)
    })

    observer.observe(parent)

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await fetch("http://localhost:8000/auth/me", {
          credentials: "include",
        })

        if (res.ok) {
          const data = await res.json()
          setUserEmail(data.email)
        } else {
          setUserEmail(null)
        }
      } catch (err) {
        console.error("Failed to fetch user:", err)
        setUserEmail(null)
      } finally {
        setLoading(false)
      }
    }

    fetchUser()
  }, [])

  const handleLogin = () => {
    navigate("/login")
  }

  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/auth/logout", {
        method: "POST",
        credentials: "include",
      })
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      // Always navigate to root, even if the request failed.
      // This way users are redirected to the main dashboard.
      setUserEmail(null)
      navigate("/", { replace: true })
    }
  }

  // Deterministic hash for consistent email-based color
  function hashCode(str: string): number {
    let hash = 0

    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i)
      hash |= 0 // Convert to 32-bit integer
    }

    return Math.abs(hash)
  }

  return (
    <aside 
    ref={sidebarRef}
    style={{
      width: collapsed ? 72 : 200,
      flexShrink: 0,
      background: "#0d1117",
      borderRight: "0.5px solid rgba(255,255,255,0.07)",
      display: "flex",
      flexDirection: "column",
      padding: "28px 0",
      transition: "width .25s ease",
      height: "100vh",
  }}
    >
      {/* Brand */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          gap: 10,
          padding: collapsed ? "0 0 24px" : "0 20px 24px",
          borderBottom: "0.5px solid rgba(255,255,255,0.07)",
          marginBottom: 20,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 6,
            background: "#070b7d",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            fontWeight: 700,
            color: "#fff",
            fontFamily: "'Playfair Display', serif",
          }}
        >
          M
        </div>

        {!collapsed && (
          <div>
            <div
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: 15,
                fontWeight: 700,
                color: "#f0ede6",
              }}
            >
              MLB Predict
            </div>

            <div
              style={{
                fontSize: 12,
                color: "rgba(255,255,255,0.67)",
                letterSpacing: ".05em",
                textTransform: "uppercase",
              }}
            >
              2025 Season
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav
        style={{
          padding: collapsed ? "0 8px" : "0 12px",
          flex: 1,
        }}
        aria-label="Main navigation"
      >
        {!collapsed && (
          <div
            style={{
              fontSize: 14,
              color: "rgba(255,255,255,0.78)",
              letterSpacing: ".12em",
              textTransform: "uppercase",
              padding: "0 8px",
              marginBottom: 6,
            }}
          >
            Menu
          </div>
        )}

        {navItems.map((item) => {
          const active = activePath === item.path

          return (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              aria-current={active ? "page" : undefined}
              title={collapsed ? item.label : undefined}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: collapsed ? "center" : "flex-start",
                gap: 10,
                padding: "9px 10px",
                width: "100%",
                background: "transparent",
                border: "none",
                borderRadius: 6,
                fontSize: 15,
                fontWeight: 500,
                color: active
                  ? "#f0ede6"
                  : "rgba(255,255,255,0.78)",
                background: active
                  ? "rgba(192,30,46,0.15)"
                  : "transparent",
                cursor: "pointer",
                marginBottom: 2,
                transition: "all .15s",
              }}
            >
              <span
                style={{
                  fontSize: 15,
                  width: 18,
                  textAlign: "center",
                  color: active ? "#e84057" : "inherit",
                }}
              >
                {item.icon}
              </span>

              {!collapsed && item.label}
            </button>
          )
        })}
      </nav>

      {/* User Section */}
      <div
        style={{
          padding: collapsed ? "16px 8px 0" : "16px 12px 0",
          borderTop: "0.5px solid rgba(255,255,255,0.07)",
          marginTop: 12,
        }}
      >
        {loading ? (
          !collapsed && (
            <div
              style={{
                padding: "8px 10px",
                fontSize: 14,
                color: "rgba(255,255,255,0.5)",
              }}
            >
              Loading...
            </div>
          )
        ) : userEmail ? (
          <>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "8px 10px",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: 50,
                  height: 50,
                  borderRadius: "50%",
                  background: `hsl(${hashCode(userEmail) % 360}, 70%, 35%)`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 18,
                  fontWeight: 600,
                  color: "#fff",
                  marginBottom: collapsed ? 0 : 8,
                }}
              >
                {userEmail.charAt(0).toUpperCase()}
              </div>

              {!collapsed && (
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 500,
                    color: "#f0ede6",
                    wordBreak: "break-word",
                    overflowWrap: "break-word",
                    maxWidth: "100%",
                    lineHeight: 1.3,
                  }}
                >
                  {userEmail}
                </div>
              )}
            </div>

            {!collapsed && (
              <button onClick={handleLogout}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  padding: "8px 10px",
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 15,
                  fontWeight: 500,
                  color: "rgba(249, 248, 255, 0.87)",
                  cursor: "pointer",
                  marginTop: 4,
                }}>
                ↩ Log out
              </button>
            )}
          </>
        ) : (
          !collapsed && (
            <button onClick={handleLogin}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 10px",
                width: "100%",
                background: "transparent",
                border: "none",
                borderRadius: 6,
                fontSize: 15,
                fontWeight: 500,
                color: "rgba(249, 248, 255, 0.87)",
                cursor: "pointer",
              }}>
              ↪ Log In
            </button>
          )
        )}
      </div>
    </aside>
  )
}
