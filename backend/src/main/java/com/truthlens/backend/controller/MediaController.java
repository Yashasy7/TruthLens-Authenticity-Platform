package com.truthlens.backend.controller;

import com.truthlens.backend.dto.MediaResponse;
import com.truthlens.backend.dto.MediaUploadResponse;
import com.truthlens.backend.service.MediaService;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.UUID;

/**
 * REST controller for Module 02 — Media Upload & Secure Ingestion.
 *
 * <p>Base path: {@code /api/media}</p>
 *
 * <p>Provides authenticated endpoints for uploading multimedia files
 * (Image, Video, Audio, Text) into quarantined storage, inspecting metadata,
 * and retrieving user uploads.</p>
 */
@RestController
@RequestMapping("/api/media")
@PreAuthorize("hasAnyRole('USER', 'ANALYST', 'MODERATOR', 'ADMIN')")
public class MediaController {

    private final MediaService mediaService;

    public MediaController(MediaService mediaService) {
        this.mediaService = mediaService;
    }

    /**
     * Uploads a multimedia file into quarantined storage with magic-byte validation and hashing.
     *
     * @param file           the uploaded file (multipart/form-data)
     * @param authentication the authenticated user identity
     * @return HTTP 201 Created with verified {@link MediaUploadResponse}
     */
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<MediaUploadResponse> uploadMedia(
            @RequestParam("file") MultipartFile file,
            Authentication authentication) {

        String userEmail = authentication.getName();
        MediaUploadResponse response = mediaService.uploadMedia(file, userEmail);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * Retrieves metadata for an ingested media file by UUID.
     *
     * <p>Enforces object-level access control: standard users may only access their own
     * uploads, while elevated roles (ANALYST, MODERATOR, ADMIN) may access any media.</p>
     *
     * @param id             the media's unique identifier
     * @param authentication the authenticated user identity
     * @return HTTP 200 OK with {@link MediaResponse}
     */
    @GetMapping("/{id}")
    public ResponseEntity<MediaResponse> getMediaById(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        MediaResponse response = mediaService.getMediaById(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves all media uploaded by the currently authenticated user.
     *
     * @param authentication the authenticated user identity
     * @return HTTP 200 OK with list of {@link MediaResponse}
     */
    @GetMapping("/my")
    public ResponseEntity<List<MediaResponse>> getMyMedia(Authentication authentication) {
        String userEmail = authentication.getName();
        List<MediaResponse> responses = mediaService.getMediaForUser(userEmail);
        return ResponseEntity.ok(responses);
    }
}
