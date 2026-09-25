package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Outbound DTO representing safe metadata for an ingested media record.
 */
public class MediaResponse {

    private UUID id;
    private UUID uploaderId;
    private String originalFilename;
    private String storagePath;
    private String mediaType;
    private String mimeType;
    private long fileSize;
    private String sha256Hash;
    private String uploadStatus;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    public MediaResponse() {
    }

    public MediaResponse(UUID id,
                         UUID uploaderId,
                         String originalFilename,
                         String storagePath,
                         String mediaType,
                         String mimeType,
                         long fileSize,
                         String sha256Hash,
                         String uploadStatus,
                         OffsetDateTime createdAt,
                         OffsetDateTime updatedAt) {
        this.id = id;
        this.uploaderId = uploaderId;
        this.originalFilename = originalFilename;
        this.storagePath = storagePath;
        this.mediaType = mediaType;
        this.mimeType = mimeType;
        this.fileSize = fileSize;
        this.sha256Hash = sha256Hash;
        this.uploadStatus = uploadStatus;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public UUID getUploaderId() {
        return uploaderId;
    }

    public void setUploaderId(UUID uploaderId) {
        this.uploaderId = uploaderId;
    }

    public String getOriginalFilename() {
        return originalFilename;
    }

    public void setOriginalFilename(String originalFilename) {
        this.originalFilename = originalFilename;
    }

    public String getStoragePath() {
        return storagePath;
    }

    public void setStoragePath(String storagePath) {
        this.storagePath = storagePath;
    }

    public String getMediaType() {
        return mediaType;
    }

    public void setMediaType(String mediaType) {
        this.mediaType = mediaType;
    }

    public String getMimeType() {
        return mimeType;
    }

    public void setMimeType(String mimeType) {
        this.mimeType = mimeType;
    }

    public long getFileSize() {
        return fileSize;
    }

    public void setFileSize(long fileSize) {
        this.fileSize = fileSize;
    }

    public String getSha256Hash() {
        return sha256Hash;
    }

    public void setSha256Hash(String sha256Hash) {
        this.sha256Hash = sha256Hash;
    }

    public String getUploadStatus() {
        return uploadStatus;
    }

    public void setUploadStatus(String uploadStatus) {
        this.uploadStatus = uploadStatus;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
