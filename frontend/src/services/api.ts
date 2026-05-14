import {
  Dashboard,
  DashboardListResponse,
  Rubric,
  RubricResponse,
  ChatMessage,
  ChatHistoryResponse,
  ApiError,
  LoginResponse,
} from '../types/api';

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000');

interface RequestOptions extends RequestInit {
  headers?: HeadersInit;
}

class ApiClient {
  private baseUrl: string;
  private localRubricFile: File | null = null;
  private localFiles = new Map<string, File>();
  private localRubric: Rubric | null = null;
  private token: string | null = localStorage.getItem('authToken');

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  get isStateless(): boolean {
    return import.meta.env.VITE_STATELESS_API === 'true' || this.baseUrl.startsWith('/api');
  }

  private createLocalId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  }

  private localFilePath(file: File): string {
    return /^image\//.test(file.type) ? URL.createObjectURL(file) : file.name;
  }

  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }
    return headers;
  }

  private getAuthHeaders(): HeadersInit {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }

  isAuthenticated(): boolean {
    return Boolean(this.token);
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `Login failed: ${response.status}`);
    }

    const data: LoginResponse = await response.json();
    this.token = data.access_token;
    localStorage.setItem('authToken', data.access_token);
    localStorage.setItem('authUsername', data.username);
    return data;
  }

  logout(): void {
    this.token = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUsername');
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Rubric endpoints
  async uploadRubric(file: File): Promise<Rubric> {
    if (this.isStateless) {
      this.localRubricFile = file;
      this.localRubric = {
        id: this.createLocalId('rubric'),
        filename: file.name,
        file_path: this.localFilePath(file),
        uploaded_at: new Date().toISOString(),
      };
      return this.localRubric;
    }

    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseUrl}/rubric/upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: formData,
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `Upload failed: ${response.status}`);
    }

    const data = await response.json();
    return data.rubric;
  }

  async getRubric(): Promise<RubricResponse> {
    if (this.isStateless) {
      return { rubric: this.localRubric };
    }
    return this.request<RubricResponse>('/rubric');
  }

  async deleteRubric(): Promise<void> {
    if (this.isStateless) {
      this.localRubricFile = null;
      this.localRubric = null;
      return;
    }
    return this.request<void>('/rubric', {
      method: 'DELETE',
    });
  }

  // Dashboard endpoints
  async uploadDashboard(file: File): Promise<Dashboard> {
    if (this.isStateless) {
      const id = this.createLocalId('file');
      this.localFiles.set(id, file);
      return {
        id,
        filename: file.name,
        file_path: this.localFilePath(file),
        uploaded_at: new Date().toISOString(),
      };
    }

    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseUrl}/dashboards/upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: formData,
    });

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw new Error(error.detail || `Upload failed: ${response.status}`);
    }

    return response.json();
  }

  async listDashboards(): Promise<DashboardListResponse> {
    if (this.isStateless) {
      return { dashboards: [], total: 0 };
    }
    return this.request<DashboardListResponse>('/dashboards');
  }

  async getDashboard(dashboardId: string): Promise<Dashboard> {
    if (this.isStateless) {
      const file = this.localFiles.get(dashboardId);
      if (!file) throw new Error('Local file not found');
      return {
        id: dashboardId,
        filename: file.name,
        file_path: this.localFilePath(file),
        uploaded_at: new Date().toISOString(),
      };
    }
    return this.request<Dashboard>(`/dashboards/${dashboardId}`);
  }

  async deleteDashboard(dashboardId: string): Promise<void> {
    if (this.isStateless) {
      this.localFiles.delete(dashboardId);
      return;
    }
    return this.request<void>(`/dashboards/${dashboardId}`, {
      method: 'DELETE',
    });
  }

  async getStudents(dashboardId: string): Promise<string[]> {
    if (this.isStateless) {
      const file = this.localFiles.get(dashboardId);
      if (!file) return [];
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${this.baseUrl}/students`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: formData,
      });
      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || `Student detection failed: ${response.status}`);
      }
      const data = await response.json();
      return data.students || [];
    }

    const data = await this.request<{ students: string[] }>(`/dashboards/${dashboardId}/students`);
    return data.students;
  }

  // Chat endpoints
  async sendMessage(message: string, dashboardId?: string, pbixId?: string, studentName?: string): Promise<ChatMessage> {
    if (this.isStateless) {
      const formData = new FormData();
      if (message) formData.append('message', message);
      if (studentName) formData.append('student_name', studentName);
      if (this.localRubricFile) formData.append('rubric_file', this.localRubricFile);
      const visualFile = dashboardId ? this.localFiles.get(dashboardId) : null;
      const pbixFile = pbixId ? this.localFiles.get(pbixId) : null;
      if (visualFile) formData.append('visual_file', visualFile);
      if (pbixFile) formData.append('pbix_file', pbixFile);

      const response = await fetch(`${this.baseUrl}/grade`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: formData,
      });
      if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || `Grading failed: ${response.status}`);
      }
      return response.json();
    }

    return this.request<ChatMessage>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        dashboard_id: dashboardId || null,
        pbix_id: pbixId || null,
        student_name: studentName || null,
      }),
    });
  }

  async getChatHistory(): Promise<ChatHistoryResponse> {
    if (this.isStateless) {
      return { messages: [], total: 0 };
    }
    return this.request<ChatHistoryResponse>('/chat/history');
  }

  // Health endpoints
  async health(): Promise<{ status: string }> {
    return fetch(`${this.baseUrl}/health`).then(r => r.json());
  }
}

export const apiClient = new ApiClient(API_URL);
