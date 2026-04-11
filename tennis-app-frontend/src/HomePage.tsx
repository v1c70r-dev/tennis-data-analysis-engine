import { Header } from "@/components/header"
import { VideoUploader } from "@/components/video-uploader"
import { MatchesList } from "@/components/matches-list"
import { StatsDashboard } from "@/components/stats-dashboard"
import { useState } from "react"

export default function HomePage() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />

      <main className="flex-1 p-6">
        <div className="mx-auto flex h-full max-w-[1600px] flex-col gap-6">
          {/* Top Section: Video Upload + Matches List */}
          <div className="grid gap-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <div className="h-[400px] rounded-xl border border-border bg-card p-4">
                <VideoUploader selectedJobId={selectedJobId} />
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="h-[400px] rounded-xl border border-border bg-card p-4">
                <MatchesList onSelectJob={setSelectedJobId} />
              </div>
            </div>
          </div>

          {/* Bottom Section: Dashboard */}
          <div className="flex-1">
            <div className="rounded-xl border border-border bg-card p-4">
              <StatsDashboard />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
