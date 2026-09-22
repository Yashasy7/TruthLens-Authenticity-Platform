package com.truthlens.backend.service.fingerprint;

import com.truthlens.backend.entity.MatchType;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaHash;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.repository.MediaHashRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Service evaluating ingested media against historical fingerprints to detect duplicates.
 *
 * <p>Evaluation sequence:</p>
 * <ol>
 *   <li><b>Exact Match</b>: Scans for identical SHA-256 hash across all media types with deterministic
 *       earliest canonical ordering. Similarity = 1.0, MatchType = {@link MatchType#EXACT_SHA256}.</li>
 *   <li><b>Visual Near-Match</b>: For {@link MediaType#IMAGE}, scans bounded perceptual hashes
 *       (dHash/pHash) and finds the closest candidate with Hamming distance &le; threshold.
 *       Similarity = (1.0 - distance / 64.0), MatchType = {@link MatchType#NEAR_MATCH_PHASH}.</li>
 *   <li><b>Acoustic Match</b>: For {@link MediaType#AUDIO}, scans bounded acoustic chromaprint
 *       signatures and evaluates Bit Error Rate (BER) similarity.
 *       MatchType = {@link MatchType#ACOUSTIC_MATCH}.</li>
 *   <li><b>No Match</b>: Media is flagged unique with MatchType = {@link MatchType#NONE}.</li>
 * </ol>
 */
@Service
public class DuplicateDetectionService {

    private static final Logger log = LoggerFactory.getLogger(DuplicateDetectionService.class);
    private static final int CANDIDATE_BATCH_SIZE = 100;

    private final MediaHashRepository mediaHashRepository;
    private final PerceptualHashService perceptualHashService;
    private final AcousticFingerprintService acousticFingerprintService;

    public DuplicateDetectionService(
            MediaHashRepository mediaHashRepository,
            PerceptualHashService perceptualHashService,
            AcousticFingerprintService acousticFingerprintService) {
        this.mediaHashRepository = mediaHashRepository;
        this.perceptualHashService = perceptualHashService;
        this.acousticFingerprintService = acousticFingerprintService;
    }

    /**
     * Evaluates a media item against existing fingerprints to detect duplicates.
     *
     * @param media       the media being analyzed
     * @param sha256Hash  the cryptographic SHA-256 hash
     * @param phash       the perceptual visual hash (nullable)
     * @param chromaprint the acoustic fingerprint (nullable)
     * @return {@link DuplicateResult} containing detection outcome
     */
    @Transactional(readOnly = true)
    public DuplicateResult detectDuplicate(Media media, String sha256Hash, String phash, String chromaprint) {
        if (media == null || media.getId() == null) {
            return DuplicateResult.noMatch();
        }

        // 1. Exact cryptographic match via SHA-256 (canonical earliest media first — F-05)
        if (sha256Hash != null && !sha256Hash.isBlank()) {
            List<MediaHash> exactMatches = mediaHashRepository.findExactMatchesOrderedByEarliest(sha256Hash, media.getId());
            if (exactMatches.isEmpty()) {
                exactMatches = mediaHashRepository.findBySha256HashAndMediaIdNot(sha256Hash, media.getId());
            }

            if (!exactMatches.isEmpty()) {
                Media original = exactMatches.get(0).getMedia();
                log.info("Duplicate detected (EXACT_SHA256): Media '{}' duplicates canonical '{}'", media.getId(), original.getId());
                return new DuplicateResult(true, original, MatchType.EXACT_SHA256, 1.0);
            }
        }

        // 2. Visual near-match via perceptual hashing (dHash/pHash) for IMAGE (bounded candidate retrieval — P-01)
        if (media.getMediaType() == MediaType.IMAGE && phash != null && !phash.isBlank()) {
            List<MediaHash> candidates = mediaHashRepository.findPerceptualCandidatesBounded(
                    media.getId(), PageRequest.of(0, CANDIDATE_BATCH_SIZE));
            if (candidates.isEmpty()) {
                candidates = mediaHashRepository.findPerceptualCandidatesExcluding(media.getId());
            }

            Media closestMatch = null;
            int minDistance = Integer.MAX_VALUE;

            for (MediaHash candidate : candidates) {
                if (candidate.getPhash() != null) {
                    int distance = perceptualHashService.calculateHammingDistance(phash, candidate.getPhash());
                    if (distance >= 0 && distance <= perceptualHashService.getHammingThreshold() && distance < minDistance) {
                        minDistance = distance;
                        closestMatch = candidate.getMedia();
                    }
                }
            }

            if (closestMatch != null) {
                // Remediated F-02: Calculate similarity directly from Hamming distance between perceptual hashes
                double actualSimilarity = Math.max(0.0, 1.0 - ((double) minDistance / PerceptualHashService.TOTAL_BITS));
                log.info("Duplicate detected (NEAR_MATCH_PHASH): Media '{}' visually matches '{}' (distance={}, similarity={})",
                        media.getId(), closestMatch.getId(), minDistance, actualSimilarity);
                return new DuplicateResult(true, closestMatch, MatchType.NEAR_MATCH_PHASH, actualSimilarity);
            }
        }

        // 3. Acoustic match via spectral chromaprint for AUDIO (bounded candidate retrieval — P-01)
        if (media.getMediaType() == MediaType.AUDIO && chromaprint != null && !chromaprint.isBlank()) {
            List<MediaHash> candidates = mediaHashRepository.findAcousticCandidatesBounded(
                    media.getId(), PageRequest.of(0, CANDIDATE_BATCH_SIZE));
            if (candidates.isEmpty()) {
                candidates = mediaHashRepository.findAcousticCandidatesExcluding(media.getId());
            }

            Media closestAcoustic = null;
            double highestSimilarity = 0.0;

            for (MediaHash candidate : candidates) {
                double sim = acousticFingerprintService.calculateSimilarity(chromaprint, candidate.getChromaprint());
                if (sim >= AcousticFingerprintService.DEFAULT_ACOUSTIC_SIMILARITY_THRESHOLD && sim > highestSimilarity) {
                    highestSimilarity = sim;
                    closestAcoustic = candidate.getMedia();
                }
            }

            if (closestAcoustic != null) {
                log.info("Duplicate detected (ACOUSTIC_MATCH): Media '{}' acoustically matches '{}' (similarity={})",
                        media.getId(), closestAcoustic.getId(), highestSimilarity);
                return new DuplicateResult(true, closestAcoustic, MatchType.ACOUSTIC_MATCH, highestSimilarity);
            }
        }

        return DuplicateResult.noMatch();
    }

    /**
     * Data record encapsulating the result of duplicate detection.
     */
    public record DuplicateResult(
            boolean isDuplicate,
            Media duplicateOf,
            MatchType matchType,
            Double similarityScore
    ) {
        public static DuplicateResult noMatch() {
            return new DuplicateResult(false, null, MatchType.NONE, 0.0);
        }
    }
}
