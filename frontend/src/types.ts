export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  organization: { id: number; name: string; slug: string } | null;
  role: string | null;
}

export interface Dashboard {
  total_activities: number;
  pending: number;
  flagged: number;
  failed: number;
  approved: number;
  locked: number;
  by_scope: Record<string, number>;
  by_source: Record<string, number>;
  recent_batches: Batch[];
}

export interface Batch {
  id: number;
  source_type: string;
  filename: string;
  uploaded_at: string;
  status: string;
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  flagged_rows: number;
  error_summary: string;
}

export interface Activity {
  id: number;
  batch: number;
  batch_filename: string;
  source_type: string;
  source_row_id: string;
  scope: string;
  category: string;
  activity_date: string | null;
  period_start: string | null;
  period_end: string | null;
  description: string;
  site_code: string;
  site_name: string;
  vendor: string;
  quantity: string | null;
  unit: string;
  normalized_quantity: string | null;
  normalized_unit: string;
  currency: string;
  amount: string | null;
  review_status: string;
  flags: string[];
  validation_errors: string[];
  raw_payload: Record<string, string>;
  ingested_at: string;
  is_edited: boolean;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
