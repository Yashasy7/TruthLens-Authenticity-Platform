package com.truthlens.backend.controller;

import com.truthlens.backend.dto.TranscriptResponse;
import com.truthlens.backend.dto.TranscriptSegmentDto;
import com.truthlens.backend.service.stt.SpeechToTextService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * REST controller exposing Speech-to-Text & Transcript Extraction endpoints (Module 10).
 */
@RestController
@RequestMapping("/api/media/{id}/transcript")
public class TranscriptController {

    private final SpeechToTextService speechToTextService;

    public TranscriptController(SpeechToTextService speechToTextService) {
        this.speechToTextService = speechToTextService;
    }

    /**
     * Retrieves Speech-to-Text findings.
     * Reuses cached record if already transcribed; triggers on-demand transcription if absent.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link TranscriptResponse}
     */
    @GetMapping
    public ResponseEntity<TranscriptResponse> getTranscript(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        TranscriptResponse response = speechToTextService.getTranscript(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly re-triggers Speech-to-Text transcription for an audio or video media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link TranscriptResponse}
     */
    @PostMapping({"", "/analyze"})
    public ResponseEntity<TranscriptResponse> reanalyzeTranscript(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        TranscriptResponse response = speechToTextService.reanalyzeTranscript(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves timestamped speech segments with phrase text and word-level alignment offsets.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with list of {@link TranscriptSegmentDto}
     */
    @GetMapping("/segments")
    public ResponseEntity<List<TranscriptSegmentDto>> getSegments(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        List<TranscriptSegmentDto> segments = speechToTextService.getSegments(id, userEmail);
        return ResponseEntity.ok(segments);
    }

    /**
     * Retrieves the raw full text transcript string extracted from the audio/video media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with text response map
     */
    @GetMapping("/text")
    public ResponseEntity<Map<String, String>> getFullText(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        String text = speechToTextService.getFullText(id, userEmail);
        return ResponseEntity.ok(Map.of("full_text", text));
    }
}
