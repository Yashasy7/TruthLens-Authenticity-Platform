package com.truthlens.backend.service.claim;

import com.truthlens.backend.dto.FastApiClaimResponse;

/**
 * Interface defining contract for external/internal NLP Claim Analysis AI services (Module 11).
 */
public interface ClaimAiServiceClient {

    FastApiClaimResponse analyzeClaims(String text, String sourceType, String language);
}
