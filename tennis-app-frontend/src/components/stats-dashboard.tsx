import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent } from "@/components/ui/card"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts"

const playerSpeedData = [
  { time: "0:00", player1: 5.2, player2: 4.8 },
  { time: "0:15", player1: 12.5, player2: 8.3 },
  { time: "0:30", player1: 8.1, player2: 15.2 },
  { time: "0:45", player1: 3.2, player2: 6.1 },
  { time: "1:00", player1: 18.4, player2: 12.7 },
  { time: "1:15", player1: 14.2, player2: 9.8 },
  { time: "1:30", player1: 6.5, player2: 11.4 },
]

const shotDistribution = [
  { type: "Forehand", count: 145 },
  { type: "Backhand", count: 98 },
  { type: "Serve", count: 62 },
  { type: "Volley", count: 28 },
  { type: "Drop Shot", count: 15 },
]

const ballSpeedData = [
  { shot: "1", speed: 125 },
  { shot: "2", speed: 98 },
  { shot: "3", speed: 142 },
  { shot: "4", speed: 88 },
  { shot: "5", speed: 156 },
  { shot: "6", speed: 134 },
  { shot: "7", speed: 112 },
  { shot: "8", speed: 145 },
]

const courtCoverage = [
  { name: "Baseline", value: 45 },
  { name: "Mid Court", value: 30 },
  { name: "Net", value: 15 },
  { name: "Service Box", value: 10 },
]

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"]

function StatCard({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="rounded-lg bg-secondary/50 p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
      {subtext && <p className="mt-1 text-xs text-primary">{subtext}</p>}
    </div>
  )
}

function PlayerStatsContent() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Distance Covered" value="2.4 km" subtext="+12% vs avg" />
        <StatCard label="Max Speed" value="18.4 km/h" />
        <StatCard label="Avg Rally Length" value="6.2 shots" />
        <StatCard label="Winners" value="24" subtext="68% forehand" />
      </div>
      
      <Card className="bg-card border-border">
        <CardContent className="p-4">
          <h4 className="mb-4 text-sm font-medium text-foreground">Player Speed Over Time</h4>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={playerSpeedData}>
              <defs>
                <linearGradient id="colorPlayer1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorPlayer2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--chart-2)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--chart-2)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" stroke="var(--muted-foreground)" fontSize={12} />
              <YAxis stroke="var(--muted-foreground)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  color: "var(--popover-foreground)",
                }}
              />
              <Area type="monotone" dataKey="player1" stroke="var(--chart-1)" strokeWidth={2} fillOpacity={1} fill="url(#colorPlayer1)" name="You" />
              <Area type="monotone" dataKey="player2" stroke="var(--chart-2)" strokeWidth={2} fillOpacity={1} fill="url(#colorPlayer2)" name="Opponent" />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}

function BallStatsContent() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Avg Ball Speed" value="128 km/h" />
        <StatCard label="Max Ball Speed" value="156 km/h" subtext="Serve" />
        <StatCard label="Spin Rate" value="2,450 rpm" />
        <StatCard label="Ball In Play" value="42%" />
      </div>
      
      <Card className="bg-card border-border">
        <CardContent className="p-4">
          <h4 className="mb-4 text-sm font-medium text-foreground">Ball Speed per Shot</h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={ballSpeedData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="shot" stroke="var(--muted-foreground)" fontSize={12} />
              <YAxis stroke="var(--muted-foreground)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  color: "var(--popover-foreground)",
                }}
              />
              <Bar dataKey="speed" fill="var(--chart-1)" radius={[4, 4, 0, 0]} name="Speed (km/h)" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}

function OtherStatsContent() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Match Duration" value="1h 24m" />
        <StatCard label="Total Points" value="124" />
        <StatCard label="Unforced Errors" value="18" />
        <StatCard label="First Serve %" value="68%" subtext="+5% vs avg" />
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <h4 className="mb-4 text-sm font-medium text-foreground">Shot Distribution</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={shotDistribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" stroke="var(--muted-foreground)" fontSize={12} />
                <YAxis dataKey="type" type="category" stroke="var(--muted-foreground)" fontSize={12} width={80} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    color: "var(--popover-foreground)",
                  }}
                />
                <Bar dataKey="count" fill="var(--chart-1)" radius={[0, 4, 4, 0]} name="Count" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <h4 className="mb-4 text-sm font-medium text-foreground">Court Coverage</h4>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={courtCoverage}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {courtCoverage.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    color: "var(--popover-foreground)",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap justify-center gap-4 text-xs">
              {courtCoverage.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-1">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-muted-foreground">{entry.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export function StatsDashboard() {
  const [activeTab, setActiveTab] = useState("players")

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-foreground">Match Analytics</h2>
        <p className="text-sm text-muted-foreground">Detailed statistics from your latest match</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1">
        <TabsList className="mb-4 bg-secondary/50">
          <TabsTrigger value="players" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Player Stats
          </TabsTrigger>
          <TabsTrigger value="ball" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Tennis Ball Stats
          </TabsTrigger>
          <TabsTrigger value="other" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Other Stats
          </TabsTrigger>
        </TabsList>

        <TabsContent value="players" className="mt-0">
          <PlayerStatsContent />
        </TabsContent>

        <TabsContent value="ball" className="mt-0">
          <BallStatsContent />
        </TabsContent>

        <TabsContent value="other" className="mt-0">
          <OtherStatsContent />
        </TabsContent>
      </Tabs>
    </div>
  )
}
