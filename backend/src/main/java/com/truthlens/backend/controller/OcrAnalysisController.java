package com.truthlens.backend.controller;

import com.truthlens.backend.dto.OcrResultResponse;
import com.truthlens.backend.dto.OcrTextRegionDto;
import com.truthlens.backend.service.ocr.OcrAnalysisService;
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
 * REST controller exposing OCR & Visual Text Extraction endpoints (Module 09).
 */
@RestController
@RequestMapping("/api/media/{id}/ocr")
public class OcrAnalysisController {

    private final OcrAnalysisService ocrAnalysisService;

    public OcrAnalysisController(OcrAnalysisService ocrAnalysisService) {
        this.ocrAnalysisService = ocrAnalysisService;
    }

    /**
     * Retrieves OCR visual text extraction findings.
     * Reuses cached record if already analyzed; triggers on-demand analysis if absent.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with {@link OcrResultResponse}
     */
    @GetMapping
    public ResponseEntity<OcrResultResponse> getOcrResult(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        OcrResultResponse response = ocrAnalysisService.getOcrResult(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Explicitly re-triggers OCR analysis for a media asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with fresh {@link OcrResultResponse}
     */
    @PostMapping({"", "/analyze"})
    public ResponseEntity<OcrResultResponse> reanalyzeOcr(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        OcrResultResponse response = ocrAnalysisService.reanalyzeOcr(id, userEmail);
        return ResponseEntity.ok(response);
    }

    /**
     * Retrieves the list of detected text regions with spatial bounding boxes and timestamps.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with list of {@link OcrTextRegionDto}
     */
    @GetMapping("/bounding-boxes")
    public ResponseEntity<List<OcrTextRegionDto>> getBoundingBoxes(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        List<OcrTextRegionDto> boundingBoxes = ocrAnalysisService.getBoundingBoxes(id, userEmail);
        return ResponseEntity.ok(boundingBoxes);
    }

    /**
     * Retrieves the raw concatenated text string extracted from the visual asset.
     *
     * @param id             UUID of the media asset
     * @param authentication authenticated caller context
     * @return HTTP 200 OK with text response map
     */
    @GetMapping("/text")
    public ResponseEntity<Map<String, String>> getExtractedText(
            @PathVariable("id") UUID id,
            Authentication authentication) {
        String userEmail = authentication.getName();
        String text = ocrAnalysisService.getExtractedText(id, userEmail);
        return ResponseEntity.ok(Map.of("extracted_text", text));
    }
}
