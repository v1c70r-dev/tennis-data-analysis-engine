import { useState, useEffect, useCallback } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? '/api';

//  Types 

export type JobStatus =
  | "pending"
  | "processing"
  | "processed"
  | "generating_report"
  | "report_ready"
  | "failed";

export interface JobSummary {
  job_id: string;
  status: JobStatus;
  input_url: string | null;
  report_url: string | null;
}

//  useJobList 
// GET /jobs  fetches all jobs. Call refetch() to refresh manually.

interface UseJobListReturn {
  jobs: JobSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useJobList(): UseJobListReturn {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/jobs`);
      if (!res.ok) throw new Error(`Failed to fetch jobs (${res.status})`);
      const data: JobSummary[] = await res.json();
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  return { jobs, isLoading, error, refetch: fetchJobs };
}

//  useDeleteJob 
// DELETE /jobs/:job_id  deletes a job and all its MinIO objects.
// Optionally pass onSuccess to update local state without a full refetch.

interface UseDeleteJobReturn {
  deleteJob: (jobId: string) => Promise<void>;
  isDeleting: boolean;
  error: string | null;
}

export function useDeleteJob(onSuccess?: (jobId: string) => void): UseDeleteJobReturn {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deleteJob = useCallback(
    async (jobId: string) => {
      setIsDeleting(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
          method: "DELETE",
        });
        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `Delete failed (${res.status})`);
        }
        onSuccess?.(jobId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        throw err;
      } finally {
        setIsDeleting(false);
      }
    },
    [onSuccess]
  );

  return { deleteJob, isDeleting, error };
}

//  useJobDashboard 
// GET /jobs/:job_id/dashboard  fetches dashboard.json for Plotly rendering.
// Only available when job status is "report_ready".

interface UseJobDashboardReturn {
  dashboard: Record<string, unknown> | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useJobDashboard(jobId: string | null): UseJobDashboardReturn {
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    if (!jobId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/dashboard`);
      if (res.status === 425) {
        // Report not ready yet  not an error worth surfacing
        return;
      }
      if (!res.ok) throw new Error(`Failed to fetch dashboard (${res.status})`);
      const data = await res.json();
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return { dashboard, isLoading, error, refetch: fetchDashboard };
}

//  useReportUrl 
// GET /jobs/:job_id/report  fetches a presigned MinIO URL for the PDF report.
// Call fetchUrl() manually (e.g. on button click) to avoid unnecessary requests.

interface UseReportUrlReturn {
  url: string | null;
  isFetching: boolean;
  error: string | null;
  fetchUrl: () => Promise<string | null>;
}

export function useReportUrl(jobId: string | null): UseReportUrlReturn {
  const [url, setUrl] = useState<string | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUrl = useCallback(async (): Promise<string | null> => {
    if (!jobId) return null;
    setIsFetching(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/report`);
      if (!res.ok) throw new Error(`Failed to get report URL (${res.status})`);
      const data: { url: string } = await res.json();
      setUrl(data.url);
      return data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      return null;
    } finally {
      setIsFetching(false);
    }
  }, [jobId]);

  return { url, isFetching, error, fetchUrl };
}

//  useJobManager 
// Combines useJobList + useDeleteJob with optimistic local state update.
// The delete removes the job from the local list immediately without refetching.

interface UseJobManagerReturn {
  jobs: JobSummary[];
  isLoading: boolean;
  isDeleting: boolean;
  error: string | null;
  refetch: () => void;
  deleteJob: (jobId: string) => Promise<void>;
}

export function useJobManager(): UseJobManagerReturn {
  const { jobs, isLoading, error, refetch, setJobs } = useJobListInternal();

  const { deleteJob, isDeleting, error: deleteError } = useDeleteJob(
    (deletedId) => setJobs((prev) => prev.filter((j) => j.job_id !== deletedId))
  );

  return {
    jobs,
    isLoading,
    isDeleting,
    error: error ?? deleteError,
    refetch,
    deleteJob,
  };
}

// Internal version of useJobList that exposes setJobs for optimistic updates
function useJobListInternal() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/jobs`);
      if (!res.ok) throw new Error(`Failed to fetch jobs (${res.status})`);
      const data: JobSummary[] = await res.json();
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  return { jobs, setJobs, isLoading, error, refetch: fetchJobs };
}