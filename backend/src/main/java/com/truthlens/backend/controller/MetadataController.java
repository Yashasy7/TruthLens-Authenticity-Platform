package com.truthlens.backend.controller;

import com.truthlens.backend.dto.MediaMetadataResponse;
import com.truthlens.backend.dto.MetadataAnomalyReportResponse;
import com.truthlens.backend.service.metadata.MediaMetadataService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * REST controller for Module 04 — Metadata Forensics.
 *
 * <p>Provides endpoints for extracting and inspecting EXIF/container metadata,
 * triggering forensic anomaly evaluations, retrieving anomaly reports, and inspecting
 * raw hierarchical metadata trees.</p>
 */
@RestController
@RequestMapping("/api/media/{id}/metadata")
@PreAuthorize("hasAnyRole('USER', 'ANALYST', 'MODERATOR', 'ADMIN', 'RESEARCHER')")
public class MetadataController {

    private final MediaMetadataService mediaMetadataService;

    public MetadataController(MediaMetadataService mediaMetadataService) {
        this.mediaMetadataService = mediaMetadataService;
    }

    /**
     * Retrieves the forensic metadata record for a media file.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link MediaMetadataResponse}
     */
    @GetMapping
    public ResponseEntity<MediaMetadataResponse> getMetadata(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        MediaMetadataResponse response = mediaMetadataService.getMetadata(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly triggers metadata extraction or re-evaluation for a media file.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with refreshed {@link MediaMetadataResponse}
     */
    @PostMapping
    public ResponseEntity<MediaMetadataResponse> generateOrReevaluateMetadata(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        MediaMetadataResponse response = mediaMetadataService.generateOrReevaluateMetadata(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the forensic anomaly evaluation report for a media file.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link MetadataAnomalyReportResponse}
     */
    @GetMapping("/anomalies")
    public ResponseEntity<MetadataAnomalyReportResponse> getAnomalyReport(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        MetadataAnomalyReportResponse response = mediaMetadataService.getAnomalyReport(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the raw hierarchical JSON metadata tree for a media file.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with raw JSON payload
     */
    @GetMapping(value = "/raw", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> getRawMetadataJson(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        String rawJson = mediaMetadataService.getRawMetadataJson(id, userEmail);
        return ResponseEntity.ok(rawJson);
    }
}
