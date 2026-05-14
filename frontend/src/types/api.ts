export interface Dashboard {
  id: string;
  filename: string;
  file_path: string;
  uploaded_at: string;
}

export interface DashboardListResponse {
  dashboards: Dashboard[];
  total: number;
}

export interface Rubric {
  id: string;
  filename: string;
  file_path: string;
  uploaded_at: string;
}

export interface RubricResponse {
  rubric: Rubric | null;
}

export interface ChatMessage {
  id: string;
  dashboard_id: string | null;
  pbix_id?: string | null;
  student_name?: string | null;
  user_message: string;
  ai_response: Record<string, unknown>;
  created_at: string;
  dashboard_filename?: string | null;
  dashboard_file_path?: string | null;
  pbix_filename?: string | null;
  pbix_file_path?: string | null;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  total: number;
}

export interface ApiError {
  detail: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
}
