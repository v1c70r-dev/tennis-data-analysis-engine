import { useState, useCallback, useRef, useEffect } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? '/api';

//  Types 

// antes
type JobStatus = "pending" | "processing" | "processed" | "generating_report" | "report_ready" | "failed"
// después
const TERMINAL_STATES: JobStatus[] = ["report_ready", "failed"];

export interface Job {
    job_id: string;
    status: JobStatus;
    report_url: string | null;
}

export interface UploadResult {
    job_id: string;
    status: "pending";
}

//  useUploadVideo 
// POST /upload  uploads a video file and returns the new job.

interface UseUploadVideoReturn {
    upload: (file: File) => Promise<UploadResult>;
    isUploading: boolean;
    error: string | null;
    reset: () => void;
}

export function useUploadVideo(): UseUploadVideoReturn {
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const reset = useCallback(() => {
        setIsUploading(false);
        setError(null);
    }, []);

    const upload = useCallback(async (file: File): Promise<UploadResult> => {
        setIsUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE_URL}/upload`, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const detail = await res.text();
                throw new Error(detail || `Upload failed (${res.status})`);
            }

            const data: UploadResult = await res.json();
            return data;
        } catch (err) {
            const message = err instanceof Error ? err.message : "Unknown upload error";
            setError(message);
            throw err;
        } finally {
            setIsUploading(false);
        }
    }, []);

    return { upload, isUploading, error, reset };
}

//  useJobStatus 
// GET /jobs/:job_id - polls a job until it reaches a terminal state.
//
// Options:
//   pollingIntervalMs  How often to poll while the job is in-flight. Default: 3000
//   enabled            Set to false to pause / skip polling entirely.

interface UseJobStatusOptions {
    pollingIntervalMs?: number;
    enabled?: boolean;
}

interface UseJobStatusReturn {
    job: Job | null;
    isLoading: boolean;
    isPolling: boolean;
    error: string | null;
    refetch: () => void;
}

export function useJobStatus(
    jobId: string | null,
    { pollingIntervalMs = 3_000, enabled = true }: UseJobStatusOptions = {}
): UseJobStatusReturn {
    const [job, setJob] = useState<Job | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchJob = useCallback(async () => {
        if (!jobId) return;

        try {
            const res = await fetch(`${API_BASE_URL}/jobs/${jobId}`);

            if (!res.ok) {
                if (res.status === 404) throw new Error("Job not found");
                throw new Error(`Request failed (${res.status})`);
            }

            const data: Job = await res.json();
            setJob(data);
            setError(null);

            // Stop polling once terminal
            if (TERMINAL_STATES.includes(data.status)) {
                setIsPolling(false);
                if (intervalRef.current) {
                    clearInterval(intervalRef.current);
                    intervalRef.current = null;
                }
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : "Unknown error";
            setError(message);
        } finally {
            setIsLoading(false);
        }
    }, [jobId]);

    // Start / restart polling whenever jobId or enabled changes
    useEffect(() => {
        if (!jobId || !enabled) return;

        // Don't restart polling if the job already finished
        if (job && TERMINAL_STATES.includes(job.status)) return;

        setIsLoading(true);
        setIsPolling(true);
        fetchJob();

        intervalRef.current = setInterval(fetchJob, pollingIntervalMs);

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            setIsPolling(false);
        };
    }, [jobId, enabled, pollingIntervalMs]); // intentionally excludes fetchJob / job

    const refetch = useCallback(() => {
        setIsLoading(true);
        fetchJob();
    }, [fetchJob]);

    return { job, isLoading, isPolling, error, refetch };
}

//  useVideoProcessor 
// Combines upload + polling into a single hook.
// Upload a file, then automatically poll until the job completes.
//
// Usage:
//   const { submit, job, stage, error, reset } = useVideoProcessor();
//   await submit(file);  // kicks off upload then polling

type Stage = "idle" | "uploading" | "processing" | "done" | "failed";

interface UseVideoProcessorReturn {
    submit: (file: File) => Promise<void>;
    job: Job | null;
    jobId: string | null;
    stage: Stage;
    error: string | null;
    reset: () => void;
}

export function useVideoProcessor(
    pollingIntervalMs = 3_000
): UseVideoProcessorReturn {
    const [jobId, setJobId] = useState<string | null>(null);
    const [stage, setStage] = useState<Stage>("idle");
    const [uploadError, setUploadError] = useState<string | null>(null);

    const { upload, isUploading, error: uploadErr, reset: resetUpload } = useUploadVideo();

    const pollEnabled = stage === "processing";
    const { job, error: pollError } = useJobStatus(jobId, {
        pollingIntervalMs,
        enabled: pollEnabled,
    });

    // Mirror job status => local stage
    useEffect(() => {
        if (!job) return;
        if (job.status === "report_ready") setStage("done");
        else if (job.status === "failed") setStage("failed");
        else setStage("processing");
    }, [job]);

    const submit = useCallback(
        async (file: File) => {
            setStage("uploading");
            setUploadError(null);
            try {
                const result = await upload(file);
                setJobId(result.job_id);
                setStage("processing");
            } catch (err) {
                setStage("failed");
                setUploadError(err instanceof Error ? err.message : "Upload failed");
            }
        },
        [upload]
    );

    const reset = useCallback(() => {
        setJobId(null);
        setStage("idle");
        setUploadError(null);
        resetUpload();
    }, [resetUpload]);

    const error = uploadError ?? uploadErr ?? pollError;

    return { submit, job, jobId, stage, error, reset };
}