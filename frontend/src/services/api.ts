import type {
  RegisterRequest,
  LoginRequest,
  AuthResponse,
  UserProfileResponse,
} from '../types/auth';
import type { MediaResponse, MediaUploadResponse } from '../types/media';
import type {
  ImageAnalysisResponse,
  VideoAnalysisResponse,
  AudioAnalysisResponse,
  AvSyncAnalysisResponse,
  OcrResultResponse,
  TranscriptResponse,
  MetadataResponse,
  FingerprintResponse,
  DuplicateMatchResponse,
} from '../types/forensics';
import type { ClaimAnalysisResponse } from '../types/claim';

const TOKEN_KEY = 'truthlens_auth_token';

export const getToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setToken = (token: string | null): void => {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // ignore local storage errors
  }
};

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const token = getToken();

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Do not set Content-Type if FormData is being passed (browser sets boundary)
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Invalid / expired token
    if (endpoint !== '/api/auth/login' && endpoint !== '/api/auth/register') {
      setToken(null);
    }
  }

  let data: any = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await response.text();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errorMsg =
      (data && typeof data === 'object' && (data.message || data.detail || data.error)) ||
      `HTTP Error ${response.status}: ${response.statusText}`;
    throw new ApiError(errorMsg, response.status, data);
  }

  return data as T;
}

// -----------------------------------------------------------------------------
// Authentication & User APIs
// -----------------------------------------------------------------------------

export const authApi = {
  register: (payload: RegisterRequest): Promise<AuthResponse> =>
    request<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  login: async (payload: LoginRequest): Promise<AuthResponse> => {
    const res = await request<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.token) {
      setToken(res.token);
    }
    return res;
  },

  logout: async (): Promise<void> => {
    try {
      await request<{ message: string }>('/api/auth/logout', {
        method: 'POST',
      });
    } finally {
      setToken(null);
    }
  },

  getCurrentUser: (): Promise<UserProfileResponse> =>
    request<UserProfileResponse>('/api/users/me'),
};

// -----------------------------------------------------------------------------
// Media Ingestion API (Module 02)
// -----------------------------------------------------------------------------

export const mediaApi = {
  upload: (file: File): Promise<MediaUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return request<MediaUploadResponse>('/api/media/upload', {
      method: 'POST',
      body: formData,
    });
  },

  getById: (id: string): Promise<MediaResponse> =>
    request<MediaResponse>(`/api/media/${id}`),

  getMyMedia: (): Promise<MediaResponse[]> =>
    request<MediaResponse[]>('/api/media/my'),
};

// -----------------------------------------------------------------------------
// Forensics & AI/ML APIs (Modules 03–11)
// -----------------------------------------------------------------------------

export const forensicsApi = {
  // Module 03: Fingerprint & Duplicates
  getFingerprint: (mediaId: string): Promise<FingerprintResponse> =>
    request<FingerprintResponse>(`/api/media/${mediaId}/fingerprint`),

  getDuplicates: (mediaId: string): Promise<DuplicateMatchResponse[]> =>
    request<DuplicateMatchResponse[]>(`/api/media/${mediaId}/duplicates`),

  // Module 04: Metadata
  getMetadata: (mediaId: string): Promise<MetadataResponse> =>
    request<MetadataResponse>(`/api/media/${mediaId}/metadata`),

  // Module 05: Image Authenticity
  getImageAnalysis: (mediaId: string): Promise<ImageAnalysisResponse> =>
    request<ImageAnalysisResponse>(`/api/media/${mediaId}/image-analysis`),

  reanalyzeImage: (mediaId: string): Promise<ImageAnalysisResponse> =>
    request<ImageAnalysisResponse>(`/api/media/${mediaId}/image-analysis`, {
      method: 'POST',
    }),

  getImageArtifactUrl: (mediaId: string, type: 'ela' | 'gradcam'): string =>
    `/api/media/${mediaId}/image-analysis/artifacts/${type}`,

  // Module 06: Video Deepfake Detection
  getVideoAnalysis: (mediaId: string): Promise<VideoAnalysisResponse> =>
    request<VideoAnalysisResponse>(`/api/media/${mediaId}/video-analysis`),

  reanalyzeVideo: (mediaId: string): Promise<VideoAnalysisResponse> =>
    request<VideoAnalysisResponse>(`/api/media/${mediaId}/video-analysis`, {
      method: 'POST',
    }),

  // Module 07: Audio Authenticity
  getAudioAnalysis: (mediaId: string): Promise<AudioAnalysisResponse> =>
    request<AudioAnalysisResponse>(`/api/media/${mediaId}/audio-analysis`),

  reanalyzeAudio: (mediaId: string): Promise<AudioAnalysisResponse> =>
    request<AudioAnalysisResponse>(`/api/media/${mediaId}/audio-analysis`, {
      method: 'POST',
    }),

  // Module 08: AV Synchronization
  getAvSyncAnalysis: (mediaId: string): Promise<AvSyncAnalysisResponse> =>
    request<AvSyncAnalysisResponse>(`/api/media/${mediaId}/av-sync`),

  reanalyzeAvSync: (mediaId: string): Promise<AvSyncAnalysisResponse> =>
    request<AvSyncAnalysisResponse>(`/api/media/${mediaId}/av-sync/analyze`, {
      method: 'POST',
    }),

  // Module 09: OCR Visual Text Extraction
  getOcr: (mediaId: string): Promise<OcrResultResponse> =>
    request<OcrResultResponse>(`/api/media/${mediaId}/ocr`),

  reanalyzeOcr: (mediaId: string): Promise<OcrResultResponse> =>
    request<OcrResultResponse>(`/api/media/${mediaId}/ocr/analyze`, {
      method: 'POST',
    }),

  // Module 10: Speech-to-Text Transcripts
  getTranscript: (mediaId: string): Promise<TranscriptResponse> =>
    request<TranscriptResponse>(`/api/media/${mediaId}/transcript`),

  reanalyzeTranscript: (mediaId: string): Promise<TranscriptResponse> =>
    request<TranscriptResponse>(`/api/media/${mediaId}/transcript/analyze`, {
      method: 'POST',
    }),

  // Module 11: Claims & Entity Extraction
  getClaims: (mediaId: string): Promise<ClaimAnalysisResponse> =>
    request<ClaimAnalysisResponse>(`/api/media/${mediaId}/claims`),

  reanalyzeClaims: (mediaId: string): Promise<ClaimAnalysisResponse> =>
    request<ClaimAnalysisResponse>(`/api/media/${mediaId}/claims/analyze`, {
      method: 'POST',
    }),

  extractTextClaims: (
    text: string,
    sourceType: string = 'DIRECT_TEXT',
    language: string = 'en',
  ): Promise<ClaimAnalysisResponse> =>
    request<ClaimAnalysisResponse>('/api/claims/extract', {
      method: 'POST',
      body: JSON.stringify({
        text,
        sourceType,
        language,
      }),
    }),
};
