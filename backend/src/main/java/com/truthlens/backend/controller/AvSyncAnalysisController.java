package com.truthlens.backend.controller;

import com.truthlens.backend.dto.AvSyncAnalysisResponse;
import com.truthlens.backend.dto.AvSyncEvidenceDto;
import com.truthlens.backend.dto.MismatchSegmentDto;
import com.truthlens.backend.service.avsync.AvSyncAnalysisService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

/**
 * REST controller exposing Audio-Video Synchronization Analysis endpoints (Module 08).
 */
@RestController
@RequestMapping("/api/media/{id}/av-sync")
public class AvSyncAnalysisController {

    private final AvSyncAnalysisService avSyncAnalysisService;

    public AvSyncAnalysisController(AvSyncAnalysisService avSyncAnalysisService) {
        this.avSyncAnalysisService = avSyncAnalysisService;
    }

    /**
     * Retrieves AV synchronization analysis findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link AvSyncAnalysisResponse}
     */
    @GetMapping
    public ResponseEntity<AvSyncAnalysisResponse> getAvSyncAnalysis(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        AvSyncAnalysisResponse response = avSyncAnalysisService.getAvSyncAnalysis(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly re-triggers AV synchronization analysis for a media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link AvSyncAnalysisResponse}
     */
    @PostMapping({"", "/analyze"})
    public ResponseEntity<AvSyncAnalysisResponse> reanalyzeAvSync(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        AvSyncAnalysisResponse response = avSyncAnalysisService.reanalyzeAvSync(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the granular cross-modal forensic evidence and metrics for a media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link AvSyncEvidenceDto}
     */
    @GetMapping("/evidence")
    public ResponseEntity<AvSyncEvidenceDto> getEvidence(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        AvSyncEvidenceDto evidence = avSyncAnalysisService.getEvidence(id, userEmail);
        return ResponseEntity.ok(evidence);
    }

    /**
     * Retrieves the list of detected mismatch segments.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with list of {@link MismatchSegmentDto}
     */
    @GetMapping("/mismatch-segments")
    public ResponseEntity<List<MismatchSegmentDto>> getMismatchSegments(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        List<MismatchSegmentDto> segments = avSyncAnalysisService.getMismatchSegments(id, userEmail);
        return ResponseEntity.ok(segments);
    }
}
