import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface ChartDataPoint {
  date: string;
  price: number;
  scraped_at: string;
}

interface PriceChartProps {
  data: ChartDataPoint[];
  thresholdDollars: number | null;
}

export function PriceChart({ data, thresholdDollars }: PriceChartProps) {
  return (
    <div style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 20, bottom: 5, left: 10 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-border)"
          />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
          />
          <YAxis
            tickFormatter={(v: number) => "$" + v.toFixed(0)}
            tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
          />
          <Tooltip
            formatter={(value: number) => ["$" + value.toFixed(2), "Price"]}
            contentStyle={{
              backgroundColor: "var(--color-card)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius)",
            }}
          />
          {thresholdDollars !== null && (
            <ReferenceLine
              y={thresholdDollars}
              stroke="var(--color-destructive)"
              strokeDasharray="8 4"
              label={{
                value: "Threshold",
                position: "right",
                fill: "var(--color-destructive)",
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="price"
            stroke="var(--color-primary)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--color-primary)" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
