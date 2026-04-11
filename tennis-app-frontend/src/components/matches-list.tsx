import { useState } from "react"
import { Folder, ChevronRight, MoreVertical, Clock, Calendar, RefreshCw, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { useJobManager } from "@/hooks/UseJobsDashboard"
import type { JobSummary, JobStatus } from "@/hooks/UseJobsDashboard"

//  Helpers 

function statusLabel(status: JobStatus): string {
  switch (status) {
    case "pending": return "Pending"
    case "processing": return "Processing..."
    case "processed": return "Processed"
    case "generating_report": return "Generating report..."
    case "report_ready": return "Ready"
    case "failed": return "Failed"
  }
}

function statusColor(status: JobStatus): string {
  switch (status) {
    case "report_ready": return "bg-primary/20 text-primary"
    case "processing":
    case "processed":
    case "generating_report": return "bg-chart-3/20 text-chart-3"
    case "failed": return "bg-destructive/20 text-destructive"
    default: return "bg-muted text-muted-foreground"
  }
}

function isInProgress(status: JobStatus): boolean {
  return ["pending", "processing", "processed", "generating_report"].includes(status)
}

function jobDisplayName(job: JobSummary): string {
  // Derive a readable name from the input_url filename, fallback to job_id
  if (job.input_url) {
    const parts = job.input_url.split("/")
    const filename = parts[parts.length - 1]
    if (filename) return decodeURIComponent(filename)
  }
  return job.job_id.slice(0, 8)
}

//  Component 

interface MatchesListProps {
  onSelectJob?: (jobId: string) => void
}

export function MatchesList({ onSelectJob }: MatchesListProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { jobs, isLoading, isDeleting, error, refetch, deleteJob } = useJobManager()

  function handleSelect(jobId: string) {
    setSelectedId(jobId)
    onSelectJob?.(jobId)
  }

  async function handleDelete(e: React.MouseEvent, jobId: string) {
    e.stopPropagation()
    if (!confirm("Delete this match and all its data?")) return
    try {
      await deleteJob(jobId)
      if (selectedId === jobId) setSelectedId(null)
    } catch {
      // error already captured in hook
    }
  }

  async function handleDownload(e: React.MouseEvent, jobId: string) {
    e.stopPropagation()
    window.open(`/api/jobs/${jobId}/report/download`, "_blank")
  }

  return (
    <div className="flex h-full flex-col">

      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">My Tennis Matches</h2>
        <div className="flex items-center gap-2">
          {!isLoading && (
            <span className="text-sm text-muted-foreground">{jobs.length} videos</span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={refetch}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <p className="mb-2 text-sm text-destructive">{error}</p>
      )}

      {/* Loading skeleton */}
      {isLoading && jobs.length === 0 && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-secondary/50" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && jobs.length === 0 && !error && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
          <Folder className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No matches yet. Upload a video to get started.</p>
        </div>
      )}

      {/* List */}
      <ScrollArea className="flex-1 -mx-1 px-1">
        <div className="flex flex-col gap-2">
          {jobs.map((job) => (
            <button
              key={job.job_id}
              onClick={() => handleSelect(job.job_id)}
              className={cn(
                "group flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-all duration-200",
                selectedId === job.job_id
                  ? "border-primary bg-primary/10"
                  : "border-border bg-secondary/30 hover:border-primary/50 hover:bg-secondary/50"
              )}
            >
              {/* Icon */}
              <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                statusColor(job.status)
              )}>
                {isInProgress(job.status)
                  ? <Loader2 className="h-5 w-5 animate-spin" />
                  : <Folder className="h-5 w-5" />
                }
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="truncate font-medium text-foreground">
                  {jobDisplayName(job)}
                </p>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1 font-mono">
                    {job.job_id.slice(0, 8)}
                  </span>
                </div>
              </div>

              {/* Status + actions */}
              <div className="flex items-center gap-2">
                {isInProgress(job.status) && (
                  <span className="text-xs font-medium text-chart-3">
                    {statusLabel(job.status)}
                  </span>
                )}
                {job.status === "failed" && (
                  <span className="text-xs font-medium text-destructive">Failed</span>
                )}

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                      disabled={isDeleting}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {job.status === "report_ready" && (
                      <DropdownMenuItem onClick={() => handleSelect(job.job_id)}>
                        View Analysis
                      </DropdownMenuItem>
                    )}
                    {job.report_url && (
                      <DropdownMenuItem onClick={(e) => handleDownload(e, job.job_id)}>
                        Download Report
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem
                      className="text-destructive"
                      onClick={(e) => handleDelete(e, job.job_id)}
                    >
                      Delete
                    </DropdownMenuItem>
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