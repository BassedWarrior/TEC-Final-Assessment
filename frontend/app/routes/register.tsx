import { useState } from "react"
import { useNavigate } from "react-router"

export default function Register() {
  const navigate = useNavigate()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confpassword, setConfirmPassword] = useState("")

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")


  const handleCreate = async () => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if(! pattern.test(username)){
      setError("Username must be a valid email")
      return
    }

    if(password.length < 8){
      setError("Password must be at least 8 characters long ")
      return
    }

    if(confpassword != password) {
      setError("Passwords do not match")
      return
    }

    if (!username || !password) {
      setError("Please enter both email and password")
      return
    }

    setLoading(true)
    setError("")

    const formData = new URLSearchParams()
    formData.append("username", username)  // email here
    formData.append("password", password)

    try {
      const response = await fetch("http://localhost:8000/auth/register", {
        method: "POST",
        headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
        credentials: "include",  // ← CRITICAL: sends and receives cookies
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Registration failed")
      }

      // No need to store token – the httpOnly cookie is automatically saved
      navigate("/")
    } catch (err: any) {
      setError(err.message || "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  const mba_red = "#89082d"
  const light_blue = "rgb(50, 38, 209)"

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'DM Sans', sans-serif", background: "#080c10" }}>

      {/* Left panel */}
      <div style={{ flex: "1.1", position: "relative", display: "flex", flexDirection: "column", justifyContent: "flex-end", padding: 48, overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, backgroundImage: "url('https://img.mlbstatic.com/mlb-mobile/oms/1920x1080_MLBTV__laa_1_kgtcth')", backgroundSize: "cover", backgroundPosition: "center top", filter: "brightness(0.7) saturate(0.7)" }} />
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(8,12,16,0.97) 0%, rgba(8, 12, 16, 0.11) 60%, transparent 100%)" }} />
        <div style={{ position: "relative", zIndex: 2 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(24, 15, 124, 0.4)", border: "0.5px solid mba_red", borderRadius: 4, padding: "4px 10px", fontSize: 15, fontWeight: 500, color: "white", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 14 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: light_blue }} /> MLB Predictions
          </div>
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 48, fontWeight: 900, color: "#f0ede6", lineHeight: 1.1, marginBottom: 12, letterSpacing: "-.02em" }}>
            Play ball.<br /><span style={{ color: "white"}}>Predict smarter.</span>
          </h1>
          <p style={{ fontSize: 18, fontWeight: 500, color: "rgba(255, 255, 255, 0.81)", lineHeight: 1.6, maxWidth: 300 }}>
            Machine learning predictions for every game of the season.
          </p>
          <div style={{ display: "flex", gap: 32, marginTop: 28, paddingTop: 24, borderTop: "0.5px solid rgba(255, 255, 255, 0.48)" }}>
            {[["2,430", "Games analyzed"], ["~65%", "Model accuracy"], ["30", "MLB teams"]].map(([val, lbl]) => (
              <div key={lbl} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 25, fontWeight: 500, color: "rgba(225, 222, 234, 0.79)" }}>{val}</span>
                <span style={{ fontSize: 15, fontWeight: 800, color: "rgba(233, 87, 87, 0.95)", textTransform: "uppercase", letterSpacing: ".08em" }}>{lbl}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div style={{ width: 600, flexShrink: 0, background: "#0d1117", borderLeft: "0.5px solid mba_blue", display: "flex", flexDirection: "column", justifyContent: "center", padding: "40px 44px" }}>
        <p style={{ fontSize: 17, fontWeight: 500, color: "rgba(219, 218, 238, 0.5)", letterSpacing: ".14em", textTransform: "uppercase", marginBottom: 8 }}>Welcome</p>
        <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 35, fontWeight: 700, color: "white", marginBottom: 32 }}>Sign Up</h2>

        {[
          { label: "Email", type: "text", val: username, set: setUsername, placeholder: "email@example.com" },
          { label: "Password", type: "password", val: password, set: setPassword, placeholder: "••••••••" },
          { label: "Confirm Password", type: "password", val: confpassword, set: setConfirmPassword, placeholder: "••••••••" },

        ].map(f => (
          <div key={f.label} style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 18, fontWeight: 500, color: "rgba(255, 255, 255, 0.81)", letterSpacing: ".06em", marginBottom: 6 }}>{f.label}</label>
            <input
              type={f.type}
              placeholder={f.placeholder}
              value={f.val}
              onChange={e => f.set(e.target.value)}
              style={{ width: "100%", background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "11px 14px", fontSize: 20, color: "rgba(255, 255, 255, 0.89)", fontFamily: "'DM Sans', sans-serif", outline: "none" }}
            />
          </div>
        ))}

      <button onClick={handleCreate}
          disabled={loading}
          style={{ width: "100%", padding: 12, background: mba_red, border: "none", borderRadius: 6, fontSize: 16, fontWeight: 500, color: "#fff", fontFamily: "'DM Sans', sans-serif", cursor: "pointer", letterSpacing: ".04em", opacity: loading ? 0.7 : 1 }}>
          {loading ? "Creating Account..." : "Create Account"}
        </button>

        {error && (
          <div style={{ marginBottom: 16, fontSize: 14, color: "#ff6b6b", textAlign: "center" }}>
            {error}
          </div>
        )}
      </div>

      {/* Google Fonts */}
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&display=swap" />
    </div>
  )
}
