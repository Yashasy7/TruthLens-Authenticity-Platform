package com.truthlens.backend.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * Outbound DTO returned upon successful media ingestion into quarantined storage.
 *
 * <p>Exposes safe metadata and verified MIME / category information.
 * Internal absolute filesystem paths are never leaked to clients.</p>
 */
public class MediaUploadResponse {

    private String message;
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

    public MediaUploadResponse() {
    }

    public MediaUploadResponse(String message,
                               UUID id,
                               UUID uploaderId,
                               String originalFilename,
                               String storagePath,
                               String mediaType,
                               String mimeType,
                               long fileSize,
                               String sha256Hash,
                               String uploadStatus,
                               OffsetDateTime createdAt) {
        this.message = message;
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
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
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
}
