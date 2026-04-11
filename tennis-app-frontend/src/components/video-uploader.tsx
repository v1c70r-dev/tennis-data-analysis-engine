import { useState, useRef, useCallback, useEffect } from "react"
import { Upload, Play, Pause, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useVideoProcessor } from "../hooks/UseVideoApi"

interface VideoUploaderProps {
  selectedJobId?: string | null
}

export function VideoUploader({ selectedJobId }: VideoUploaderProps) {
  const [video, setVideo] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { submit, job, stage, error, reset } = useVideoProcessor()

  // useEffect(() => {
  //   if (!selectedJobId) return
  //   // Revocar URL anterior si existe
  //   if (video) URL.revokeObjectURL(video)
  //   setVideo(`/api/jobs/${selectedJobId}/video`)
  //   setIsPlaying(false)
  // }, [selectedJobId])

  useEffect(() => {
    if (!selectedJobId) return
    setVideo((prev) => {
      if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev)
      return `/api/jobs/${selectedJobId}/video`
    })
    setIsPlaying(false)
  }, [selectedJobId])

  const clearVideo = useCallback(() => {
    // Solo revocar si es un blob local, no una URL de API
    if (video && video.startsWith("blob:")) URL.revokeObjectURL(video)
    setVideo(null)
    setIsPlaying(false)
    reset()
    if (inputRef.current) inputRef.current.value = ""
  }, [video, reset])

  //   const clearVideo = useCallback(() => {
  //   if (video) URL.revokeObjectURL(video)
  //   setVideo(null)
  //   setIsPlaying(false)
  //   reset()
  //   if (inputRef.current) inputRef.current.value = ""
  // }, [video, reset])

  const handleFileSelect = useCallback((file: File) => {
    if (file && file.type.startsWith("video/")) {
      const url = URL.createObjectURL(file)
      setVideo(url)
      setIsPlaying(false)
      submit(file)
    }
  }, [submit])

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setIsDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFileSelect(file)
    },
    [handleFileSelect]
  )

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFileSelect(file)
    },
    [handleFileSelect]
  )

  const togglePlayPause = useCallback(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }, [isPlaying])



  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Upload Match</h2>
        {video && (
          <Button variant="ghost" size="icon" onClick={clearVideo} className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div
        className={cn(
          "relative flex flex-1 cursor-pointer items-center justify-center overflow-hidden rounded-lg border-2 border-dashed transition-all duration-200",
          isDragOver ? "border-primary bg-primary/10" : "border-border bg-secondary/30 hover:border-primary/50 hover:bg-secondary/50",
          video && "border-solid border-border"
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !video && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={handleInputChange}
        />

        {video ? (
          <div className="relative h-full w-full">
            <video
              ref={videoRef}
              src={video}
              className="h-full w-full object-contain"
              onEnded={() => setIsPlaying(false)}
              onError={(e) => console.error("Video error:", e.currentTarget.error)}
            />
            <div className="absolute inset-0 flex items-center justify-center bg-background/20 opacity-0 transition-opacity hover:opacity-100">
              <Button
                variant="secondary"
                size="icon"
                className="h-14 w-14 rounded-full bg-primary/90 text-primary-foreground hover:bg-primary"
                onClick={(e) => {
                  e.stopPropagation()
                  togglePlayPause()
                }}
              >
                {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6 ml-1" />}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 p-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <div>
              <p className="text-lg font-medium text-foreground">
                Drop your tennis match video here
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                or click to browse files
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              Supports MP4, MOV, AVI up to 500MB
            </p>
          </div>
        )}
      </div>

      <div className="mt-3">
        {stage !== "idle" && (
          <div className="rounded-lg border border-border bg-background p-3">

            {/* Header: label + badge */}
            <div className="mb-2.5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {(stage === "uploading" || job?.status === "pending" || job?.status === "processing" || job?.status === "processed" || job?.status === "generating_report") && (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-border border-t-blue-500" />
                )}
                <span className="text-sm font-medium text-foreground">
                  {stage === "uploading" && "Uploading video…"}
                  {job?.status === "pending" && "Waiting in queue…"}
                  {job?.status === "processing" && "Processing video…"}
                  {job?.status === "processed" && "Video processed…"}
                  {job?.status === "generating_report" && "Generating report…"}
                  {job?.status === "report_ready" && "Report ready"}
                  {job?.status === "failed" && "Something went wrong"}
                </span>
                {job?.job_id && job.status !== "report_ready" && job.status !== "failed" && (
                  <span className="text-xs text-muted-foreground">
                    job {job.job_id.slice(0, 8)}
                  </span>
                )}
              </div>

              {/* Status badge */}
              {job?.status === "pending" && (
                <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  pending
                </span>
              )}
              {(job?.status === "processing" || job?.status === "processed") && (
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                  {job.status}
                </span>
              )}
              {job?.status === "generating_report" && (
                <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                  generating report
                </span>
              )}
              {job?.status === "report_ready" && (
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
                  done
                </span>
              )}
              {job?.status === "failed" && (
                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
                  failed
                </span>
              )}
            </div>

            {/* Progress bar — 5 steps after upload */}
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
              {stage === "uploading" && (
                <div className="h-full w-2/5 animate-[indeterminate_1.4s_ease_infinite] rounded-full bg-blue-400" />
              )}
              {job?.status === "pending" && (
                <div className="h-full w-1/5 rounded-full bg-blue-300 transition-all duration-500" />
              )}
              {job?.status === "processing" && (
                <div className="h-full w-2/5 rounded-full bg-blue-400 transition-all duration-500" />
              )}
              {job?.status === "processed" && (
                <div className="h-full w-3/5 rounded-full bg-blue-500 transition-all duration-500" />
              )}
              {job?.status === "generating_report" && (
                <div className="h-full w-4/5 rounded-full bg-yellow-500 transition-all duration-500" />
              )}
              {job?.status === "report_ready" && (
                <div className="h-full w-full rounded-full bg-green-500 transition-all duration-500" />
              )}
              {job?.status === "failed" && (
                <div className="h-full w-full rounded-full bg-destructive" />
              )}
            </div>

            {/* Step indicators */}
            {stage !== "uploading" && job?.status !== "failed" && (
              <div className="mt-2 flex justify-between">
                {(["pending", "processing", "processed", "generating_report", "report_ready"] as const).map((s) => {
                  const order = ["pending", "processing", "processed", "generating_report", "report_ready"]
                  const currentIdx = order.indexOf(job?.status ?? "")
                  const stepIdx = order.indexOf(s)
                  const done = currentIdx >= stepIdx
                  return (
                    <span key={s} className={`text-[10px] ${done ? "text-foreground" : "text-muted-foreground/40"}`}>
                      {s === "pending" && "queued"}
                      {s === "processing" && "processing"}
                      {s === "processed" && "processed"}
                      {s === "generating_report" && "report"}
                      {s === "report_ready" && "ready"}
                    </span>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  )
}
