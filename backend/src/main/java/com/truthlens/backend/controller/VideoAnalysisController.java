package com.truthlens.backend.controller;

import com.truthlens.backend.dto.SuspiciousTimestampDto;
import com.truthlens.backend.dto.VideoAnalysisResponse;
import com.truthlens.backend.dto.VideoEvidenceDto;
import com.truthlens.backend.service.video.VideoAuthenticityService;
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
 * REST controller exposing Video Deepfake & Forensic Analysis endpoints (Module 06).
 */
@RestController
@RequestMapping("/api/media/{id}/video-analysis")
public class VideoAnalysisController {

    private final VideoAuthenticityService videoAuthenticityService;

    public VideoAnalysisController(VideoAuthenticityService videoAuthenticityService) {
        this.videoAuthenticityService = videoAuthenticityService;
    }

    /**
     * Retrieves video deepfake analysis findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link VideoAnalysisResponse}
     */
    @GetMapping
    public ResponseEntity<VideoAnalysisResponse> getVideoAnalysis(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        VideoAnalysisResponse response = videoAuthenticityService.getVideoAnalysis(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly re-triggers video authenticity analysis for a media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link VideoAnalysisResponse}
     */
    @PostMapping
    public ResponseEntity<VideoAnalysisResponse> reanalyzeVideo(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        VideoAnalysisResponse response = videoAuthenticityService.reanalyzeVideo(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the granular forensic evidence and per-frame scores for a video asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link VideoEvidenceDto}
     */
    @GetMapping("/evidence")
    public ResponseEntity<VideoEvidenceDto> getEvidence(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        VideoEvidenceDto evidence = videoAuthenticityService.getEvidence(id, userEmail);
        return ResponseEntity.ok(evidence);
    }

    /**
     * Retrieves the chronological timeline of marked suspicious timestamps.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with list of {@link SuspiciousTimestampDto}
     */
    @GetMapping("/timeline")
    public ResponseEntity<List<SuspiciousTimestampDto>> getTimeline(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        List<SuspiciousTimestampDto> timeline = videoAuthenticityService.getTimeline(id, userEmail);
        return ResponseEntity.ok(timeline);
    }
}
