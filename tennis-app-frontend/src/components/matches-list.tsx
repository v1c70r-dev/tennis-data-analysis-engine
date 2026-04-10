import { useState } from "react"
import { Folder, ChevronRight, MoreVertical, Clock, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

interface Match {
  id: string
  name: string
  date: string
  duration: string
  status: "processed" | "processing" | "pending"
}

const mockMatches: Match[] = [
  { id: "1", name: "Practice Session - Roland Garros", date: "Apr 8, 2026", duration: "1h 24m", status: "processed" },
  { id: "2", name: "Training Match vs. Coach", date: "Apr 5, 2026", duration: "45m", status: "processed" },
  { id: "3", name: "Tournament Semifinal", date: "Apr 2, 2026", duration: "2h 15m", status: "processing" },
  { id: "4", name: "Doubles Practice", date: "Mar 28, 2026", duration: "1h 10m", status: "processed" },
  { id: "5", name: "Baseline Drills", date: "Mar 25, 2026", duration: "35m", status: "pending" },
  { id: "6", name: "Serve Training Session", date: "Mar 22, 2026", duration: "50m", status: "processed" },
]

export function MatchesList() {
  const [selectedMatch, setSelectedMatch] = useState<string | null>("1")

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">My Tennis Matches</h2>
        <span className="text-sm text-muted-foreground">{mockMatches.length} videos</span>
      </div>
      
      <ScrollArea className="flex-1 -mx-1 px-1">
        <div className="flex flex-col gap-2">
          {mockMatches.map((match) => (
            <button
              key={match.id}
              onClick={() => setSelectedMatch(match.id)}
              className={cn(
                "group flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-all duration-200",
                selectedMatch === match.id
                  ? "border-primary bg-primary/10"
                  : "border-border bg-secondary/30 hover:border-primary/50 hover:bg-secondary/50"
              )}
            >
              <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                match.status === "processed" ? "bg-primary/20 text-primary" :
                match.status === "processing" ? "bg-chart-3/20 text-chart-3" :
                "bg-muted text-muted-foreground"
              )}>
                <Folder className="h-5 w-5" />
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="truncate font-medium text-foreground">{match.name}</p>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {match.date}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {match.duration}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {match.status === "processing" && (
                  <span className="text-xs font-medium text-chart-3">Processing...</span>
                )}
                {match.status === "pending" && (
                  <span className="text-xs font-medium text-muted-foreground">Pending</span>
                )}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>View Analysis</DropdownMenuItem>
                    <DropdownMenuItem>Download Video</DropdownMenuItem>
                    <DropdownMenuItem>Rename</DropdownMenuItem>
                    <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
