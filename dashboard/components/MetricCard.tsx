interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean | null;
  highlight?: boolean;
}

export function MetricCard({ label, value, sub, positive, highlight }: MetricCardProps) {
  const valueColor =
    positive === true  ? 'positive' :
    positive === false ? 'negative' :
    highlight          ? 'style={{color:"var(--blue)"}}' : '';

  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div
        className="metric-value"
        style={{
          color: positive === true  ? 'var(--green)' :
                 positive === false ? 'var(--red)'   :
                 highlight          ? 'var(--blue)'  :
                 'var(--text-primary)'
        }}
      >
        {value}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}
