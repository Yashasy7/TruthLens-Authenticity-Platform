/**
 * Authentication and User types matching Spring Boot backend DTOs.
 */

export interface RegisterRequest {
  email: string;
  password: string;
  fullName?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  message: string;
  token?: string | null;
  tokenType?: string | null;
  userId?: string | null;
  email?: string | null;
  fullName?: string | null;
  status?: string | null;
  roles?: string[] | null;
  createdAt?: string | null;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  fullName?: string | null;
  status: string;
  roles: string[];
  createdAt: string;
  updatedAt?: string | null;
}

export interface AuthState {
  token: string | null;
  user: UserProfileResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
