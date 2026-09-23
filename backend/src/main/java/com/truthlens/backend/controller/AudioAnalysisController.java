package com.truthlens.backend.controller;

import com.truthlens.backend.dto.AudioAnalysisResponse;
import com.truthlens.backend.dto.AudioEvidenceDto;
import com.truthlens.backend.dto.AudioSpliceMarkerDto;
import com.truthlens.backend.service.audio.AudioAuthenticityService;
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
 * REST controller exposing Audio Authenticity & Voice Forensics endpoints (Module 07).
 */
@RestController
@RequestMapping("/api/media/{id}/audio-analysis")
public class AudioAnalysisController {

    private final AudioAuthenticityService audioAuthenticityService;

    public AudioAnalysisController(AudioAuthenticityService audioAuthenticityService) {
        this.audioAuthenticityService = audioAuthenticityService;
    }

    /**
     * Retrieves audio authenticity findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link AudioAnalysisResponse}
     */
    @GetMapping
    public ResponseEntity<AudioAnalysisResponse> getAudioAnalysis(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        AudioAnalysisResponse response = audioAuthenticityService.getAudioAnalysis(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly re-triggers audio authenticity analysis for a media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link AudioAnalysisResponse}
     */
    @PostMapping
    public ResponseEntity<AudioAnalysisResponse> reanalyzeAudio(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        AudioAnalysisResponse response = audioAuthenticityService.reanalyzeAudio(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the granular acoustic evidence and metrics for an audio asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link AudioEvidenceDto}
     */
    @GetMapping("/evidence")
    public ResponseEntity<AudioEvidenceDto> getEvidence(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        AudioEvidenceDto evidence = audioAuthenticityService.getEvidence(id, userEmail);
        return ResponseEntity.ok(evidence);
    }

    /**
     * Retrieves the detected audio splice markers.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with list of {@link AudioSpliceMarkerDto}
     */
    @GetMapping("/splice-markers")
    public ResponseEntity<List<AudioSpliceMarkerDto>> getSpliceMarkers(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        List<AudioSpliceMarkerDto> markers = audioAuthenticityService.getSpliceMarkers(id, userEmail);
        return ResponseEntity.ok(markers);
    }
}
