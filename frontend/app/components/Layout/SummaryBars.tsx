interface SummaryItem {
  label: string;
  value: string | number;
}

interface SummaryBarProps {
  items: SummaryItem[];
}

export function SummaryBar({ items }: SummaryBarProps) {
  return (
    <div style={{
      display: "flex",
      background: "rgba(0,0,0,0.4)",
      borderTop: "0.5px solid rgba(255,255,255,0.1)",
      flexShrink: 0,
    }}>
      {items.map((item, idx, arr) => (
        <div key={item.label} style={{
          flex: 1,
          padding: "12px 20px",
          borderRight: idx < arr.length - 1 ? "0.5px solid rgba(255,255,255,0.08)" : "none",
        }}>
          <div style={{
            fontFamily: "var(--font-display)",
            fontSize: 28,
            fontWeight: 800,
            color: "white",
          }}>{item.value}</div>
          <div style={{
            fontSize: 13,
            fontWeight: 600,
            color: "rgba(255,255,255,0.7)",
            textTransform: "uppercase",
            letterSpacing: "0.07em",
          }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}