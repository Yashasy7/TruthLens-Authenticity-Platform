package com.truthlens.backend.controller;

import com.truthlens.backend.dto.AdHocTextClaimRequest;
import com.truthlens.backend.dto.ClaimAnalysisResponse;
import com.truthlens.backend.dto.ClaimDto;
import com.truthlens.backend.entity.ClaimSourceType;
import com.truthlens.backend.service.claim.TextClaimAnalysisService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * REST controller exposing Text & Claim Analysis endpoints (Module 11).
 */
@RestController
@RequestMapping("/api")
public class ClaimController {

    private final TextClaimAnalysisService textClaimAnalysisService;

    public ClaimController(TextClaimAnalysisService textClaimAnalysisService) {
        this.textClaimAnalysisService = textClaimAnalysisService;
    }

    /**
     * Retrieves extracted claims for a given media asset.
     * Reuses cached records if present; triggers on-demand claim extraction if absent.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link ClaimAnalysisResponse}
     */
    @GetMapping("/media/{id}/claims")
    public ResponseEntity<ClaimAnalysisResponse> getClaims(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ClaimAnalysisResponse response = textClaimAnalysisService.getClaims(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Forces fresh re-analysis and extraction of claims on a target media asset.
     *
     * @param id             UUID of the media asset
     * @param source         optional explicit source filter ('OCR', 'TRANSCRIPT', 'COMBINED')
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link ClaimAnalysisResponse}
     */
    @PostMapping(value = {"/media/{id}/claims", "/media/{id}/claims/analyze"})
    public ResponseEntity<ClaimAnalysisResponse> reanalyzeClaims(
            @PathVariable("id") UUID id,
            @RequestParam(value = "source", required = false) String source,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ClaimSourceType sourceType = null;
        if (source != null && !source.isBlank()) {
            try {
                sourceType = ClaimSourceType.valueOf(source.toUpperCase());
            } catch (IllegalArgumentException ignored) {
                // Default to null, will resolve dynamically
            }
        }
        ClaimAnalysisResponse response = textClaimAnalysisService.reanalyzeClaims(id, userEmail, sourceType);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves a single structured claim by its UUID.
     *
     * @param id             UUID of the media asset
     * @param claimId        UUID of the claim record
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link ClaimDto}
     */
    @GetMapping("/media/{id}/claims/{claimId}")
    public ResponseEntity<ClaimDto> getClaimById(
            @PathVariable("id") UUID id,
            @PathVariable("claimId") UUID claimId,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ClaimDto claimDto = textClaimAnalysisService.getClaimById(id, claimId, userEmail);
        return ResponseEntity.ok(claimDto);
    }

    /**
     * Executes ad-hoc claim extraction directly on raw text.
     *
     * @param request        validated {@link AdHocTextClaimRequest}
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with transient {@link ClaimAnalysisResponse}
     */
    @PostMapping(value = {"/claims/extract", "/claims/analyze-text"})
    public ResponseEntity<ClaimAnalysisResponse> analyzeDirectText(
            @Valid @RequestBody AdHocTextClaimRequest request,
            Authentication authentication) {
        String userEmail = authentication.getName();
        ClaimAnalysisResponse response = textClaimAnalysisService.analyzeDirectText(
                request.getText(),
                request.getSourceType(),
                request.getLanguage(),
                userEmail
        );
        return ResponseEntity.ok(response);
    }
}
