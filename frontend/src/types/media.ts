export type MediaType = "IMAGE" | "VIDEO" | "AUDIO" | "TEXT" | "image" | "video" | "audio";

export interface MediaFile {
  id: string;
  name: string;
  type: "image" | "video" | "audio" | "IMAGE" | "VIDEO" | "AUDIO";
  size: number;
  status: "ready" | "uploading" | "uploaded" | "failed";
}

export interface MediaUploadResponse {
  message: string;
  id: string;
  uploaderId: string;
  originalFilename: string;
  storagePath: string;
  mediaType: "IMAGE" | "VIDEO" | "AUDIO" | "TEXT";
  mimeType: string;
  fileSize: number;
  sha256Hash: string;
  uploadStatus: string;
  createdAt: string;
}

export interface MediaResponse {
  id: string;
  uploaderId: string;
  originalFilename: string;
  storagePath: string;
  mediaType: "IMAGE" | "VIDEO" | "AUDIO" | "TEXT";
  mimeType: string;
  fileSize: number;
  sha256Hash: string;
  uploadStatus: string;
  createdAt: string;
  updatedAt?: string | null;
}