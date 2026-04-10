import { useState, useRef, useCallback } from "react"
import { Upload, Play, Pause, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function VideoUploader() {
  const [video, setVideo] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback((file: File) => {
    if (file && file.type.startsWith("video/")) {
      const url = URL.createObjectURL(file)
      setVideo(url)
      setIsPlaying(false)
    }
  }, [])

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

  const clearVideo = useCallback(() => {
    if (video) URL.revokeObjectURL(video)
    setVideo(null)
    setIsPlaying(false)
    if (inputRef.current) inputRef.current.value = ""
  }, [video])

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
    </div>
  )
}
