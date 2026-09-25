export type MediaType = "image" | "video" | "audio";

export interface MediaFile {
  id: string;
  name: string;
  type: MediaType;
  size: number;
  status: "ready" | "uploading" | "uploaded" | "failed";
}