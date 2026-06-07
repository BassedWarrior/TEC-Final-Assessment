import { useNavigate } from "react-router"

const navItems = [
  { label: "Dashboard",  icon: "⊞", path: "/" },
  { label: "Simulate",   icon: "▶", path: "/simulate" },
  { label: "Statistics", icon: "≡", path: "/statistics" },
  { label: "History",    icon: "◷", path: "/history" },
]

interface SidebarProps {
  activePath: string
  username: string
}

export default function Sidebar({ activePath, username }: SidebarProps) {
  const navigate = useNavigate()

  return (
    <aside style={{ width: 200, flexShrink: 0, background: "#0d1117", borderRight: "0.5px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column", padding: "28px 0" }}>
      
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 20px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.07)", marginBottom: 20 }}>
        <div style={{ width: 32, height: 32, borderRadius: 6, background: "#070b7d", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700, color: "#fff", fontFamily: "'Playfair Display', serif" }}>M</div>
        <div>
          <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 700, color: "#f0ede6" }}>MLB  Predict</div>
          <div style={{ fontSize: 12, color: "rgba(255, 255, 255, 0.67)", letterSpacing: ".05em", textTransform: "uppercase" }}>2025 Season</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "0 12px", flex: 1 }} aria-label="Main navigation">
        <div style={{ fontSize: 14, color: "rgba(255, 255, 255, 0.78)", letterSpacing: ".12em", textTransform: "uppercase", padding: "0 8px", marginBottom: 6 }}>Menu</div>
        {navItems.map(item => {
          const active = activePath === item.path
          return (
            <div key={item.label} onClick={() => navigate(item.path)}
              role="menuitem" aria-current={active ? "page" : undefined}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 6, fontSize: 15, fontWeight: 500, color: active ? "#f0ede6" : "rgba(255, 255, 255, 0.78)", background: active ? "rgba(192,30,46,0.15)" : "transparent", cursor: "pointer", marginBottom: 2, transition: "all .15s" }}>
              <span style={{ fontSize: 15, width: 18, textAlign: "center", color: active ? "#e84057" : "inherit" }}>{item.icon}</span>
              {item.label}
            </div>
          )
        })}
      </nav>

      {/* User */}
      <div style={{ padding: "16px 12px 0", borderTop: "0.5px solid rgba(255,255,255,0.07)", marginTop: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px" }}>
          <div style={{ width: 30, height: 30, borderRadius: "50%", background: "rgba(60, 30, 192, 0.2)", border: "1px solid rgba(65, 30, 192, 0.4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, color: "rgb(112, 79, 230)" }}>
            {username.charAt(0).toUpperCase()}
          </div>
          <div>
            <div style={{ fontSize: 17, fontWeight: 500, color: "#f0ede6" }}>{username}</div>
          </div>
        </div>
        <div onClick={() => navigate("/login")}
          style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 6, fontSize: 15, fontWeight: 500, color: "rgba(145, 136, 250, 0.6)", cursor: "pointer" }}>
          ↩ Log out
        </div>
      </div>
    </aside>
  )
}