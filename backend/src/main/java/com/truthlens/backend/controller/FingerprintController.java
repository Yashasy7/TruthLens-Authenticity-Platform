package com.truthlens.backend.controller;

import com.truthlens.backend.dto.DuplicateDetailResponse;
import com.truthlens.backend.dto.MediaHashResponse;
import com.truthlens.backend.service.fingerprint.MediaFingerprintService;
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
 * REST controller for Module 03 — Media Fingerprinting & Duplicate Detection.
 *
 * <p>Provides endpoints for inspecting cryptographic, perceptual, and acoustic fingerprints,
 * triggering fingerprint generation and catalog re-evaluation, and retrieving duplicate analysis.</p>
 */
@RestController
@RequestMapping("/api/media/{id}")
@PreAuthorize("hasAnyRole('USER', 'ANALYST', 'MODERATOR', 'ADMIN', 'RESEARCHER')")
public class FingerprintController {

    private final MediaFingerprintService mediaFingerprintService;

    public FingerprintController(MediaFingerprintService mediaFingerprintService) {
        this.mediaFingerprintService = mediaFingerprintService;
    }

    /**
     * Retrieves the cryptographic and perceptual fingerprint metadata for a media file.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link MediaHashResponse}
     */
    @GetMapping("/fingerprint")
    public ResponseEntity<MediaHashResponse> getFingerprint(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        MediaHashResponse response = mediaFingerprintService.getFingerprint(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly generates or re-evaluates fingerprints and duplicate status for a media file against the current catalog.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with refreshed {@link MediaHashResponse}
     */
    @PostMapping("/fingerprint")
    public ResponseEntity<MediaHashResponse> generateFingerprint(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        MediaHashResponse response = mediaFingerprintService.generateOrReevaluateFingerprint(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves duplicate detection analysis and matching details for a media file.
     *
     * @param id             the media identifier
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link DuplicateDetailResponse}
     */
    @GetMapping("/duplicates")
    public ResponseEntity<DuplicateDetailResponse> getDuplicateDetails(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        DuplicateDetailResponse response = mediaFingerprintService.getDuplicateDetails(id, userEmail);
        return ResponseEntity.ok(response);
    }
}
