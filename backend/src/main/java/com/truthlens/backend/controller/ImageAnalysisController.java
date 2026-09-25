package com.truthlens.backend.controller;

import com.truthlens.backend.dto.ImageAnalysisResponse;
import com.truthlens.backend.dto.ImageEvidenceDto;
import com.truthlens.backend.service.image.ImageAuthenticityService;
import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.InputStream;
import java.util.UUID;

/**
 * REST controller for Module 05 — Image Authenticity Analysis.
 *
 * <p>Provides endpoints to trigger deepfake & physical manipulation analysis,
 * retrieve existing analysis results and structured forensic evidence,
 * and securely stream generated visual heatmap artifacts.</p>
 */
@RestController
@RequestMapping("/api/media/{id}/image-analysis")
@PreAuthorize("hasAnyRole('USER', 'ANALYST', 'MODERATOR', 'ADMIN', 'RESEARCHER')")
public class ImageAnalysisController {

    private final ImageAuthenticityService imageAuthenticityService;

    public ImageAnalysisController(ImageAuthenticityService imageAuthenticityService) {
        this.imageAuthenticityService = imageAuthenticityService;
    }

    /**
     * Retrieves the image authenticity analysis for a media asset, computing it on demand
     * if not already generated.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link ImageAnalysisResponse}
     */
    @GetMapping
    public ResponseEntity<ImageAnalysisResponse> getImageAnalysis(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ImageAnalysisResponse response = imageAuthenticityService.getImageAnalysis(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly triggers or re-evaluates image authenticity analysis for a media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link ImageAnalysisResponse}
     */
    @PostMapping
    public ResponseEntity<ImageAnalysisResponse> triggerAnalysis(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ImageAnalysisResponse response = imageAuthenticityService.reanalyzeImage(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves detailed explainable forensic evidence breakdown for an image.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link ImageEvidenceDto}
     */
    @GetMapping("/evidence")
    public ResponseEntity<ImageEvidenceDto> getEvidence(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ImageEvidenceDto evidence = imageAuthenticityService.getEvidence(id, userEmail);
        return ResponseEntity.ok(evidence);
    }

    /**
     * Streams a visual forensic heatmap artifact (ELA or Grad-CAM) as a PNG image.
     *
     * @param id             UUID of the media asset
     * @param type           artifact type: "ela" or "gradcam"
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with PNG image resource stream
     */
    @GetMapping(value = "/artifacts/{type}", produces = MediaType.IMAGE_PNG_VALUE)
    public ResponseEntity<Resource> getArtifact(
            @PathVariable("id") UUID id,
            @PathVariable("type") String type,
            Authentication authentication) {
        String userEmail = authentication.getName();
        InputStream is = imageAuthenticityService.getArtifactStream(id, type, userEmail);
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .body(new InputStreamResource(is));
    }
}
