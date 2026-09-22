package com.truthlens.backend.service.metadata;

import com.truthlens.backend.dto.ForensicAnomalyDto;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Evaluates forensic anomaly rules against extracted media metadata and ingestion properties.
 *
 * <p>Produces structured forensic findings (rule ID, category, severity, evidence, explanation,
 * confidence) and calculates a normalized metadata suspicion score between 0.0000 and 1.0000.</p>
 */
@Component
public class MetadataAnomalyEvaluator {

    private static final String[] HIGH_RISK_EDITORS = {
            "photoshop", "gimp", "canva", "capcut", "lightroom", "premiere",
            "after effects", "final cut", "snapseed", "picsart", "indesign",
            "affinity photo", "pixelmator"
    };

    private static final String[] MEDIUM_RISK_ENCODERS = {
            "ffmpeg", "libx264", "libx265", "handbrake", "lavf", "mencoder", "formatfactory"
    };

    private static final String[] CAMERA_MANUFACTURERS = {
            "canon", "nikon", "sony", "fujifilm", "olympus", "panasonic", "leica", "hasselblad"
    };

    public EvaluationResult evaluate(Media media, ExtractedMetadata metadata) {
        List<ForensicAnomalyDto> anomalies = new ArrayList<>();
        double totalScore = 0.0;

        // Rule 1: Editing software signature detection
        String software = metadata.getSoftwareTag();
        if (software != null && !software.isBlank()) {
            String lowerSoft = software.toLowerCase(Locale.ROOT);
            boolean matchedHigh = false;
            for (String editor : HIGH_RISK_EDITORS) {
                if (lowerSoft.contains(editor)) {
                    anomalies.add(new ForensicAnomalyDto(
                            "ANOM_EDITING_SOFTWARE",
                            "SOFTWARE_MODIFICATION",
                            "HIGH",
                            "Editing Software Signature Detected",
                            "Metadata headers indicate modification or creation using graphic editing software (" + software + "). Strongly suggests post-capture manipulation.",
                            "Software Tag: " + software,
                            0.95,
                            0.35
                    ));
                    totalScore += 0.35;
                    matchedHigh = true;
                    break;
                }
            }

            if (!matchedHigh) {
                for (String encoder : MEDIUM_RISK_ENCODERS) {
                    if (lowerSoft.contains(encoder)) {
                        anomalies.add(new ForensicAnomalyDto(
                                "ANOM_RE_ENCODING_SOFTWARE",
                                "SOFTWARE_MODIFICATION",
                                "MEDIUM",
                                "Re-encoding Tool Signature Detected",
                                "Metadata headers indicate re-encoding or container restructuring using transcode tools (" + software + ").",
                                "Encoder Tag: " + software,
                                0.85,
                                0.20
                        ));
                        totalScore += 0.20;
                        break;
                    }
                }
            }
        }

        // Rule 2: Future timestamps
        OffsetDateTime nowWithTolerance = OffsetDateTime.now(ZoneOffset.UTC).plusHours(1);
        if (metadata.getCapturedAt() != null && metadata.getCapturedAt().isAfter(nowWithTolerance)) {
            anomalies.add(new ForensicAnomalyDto(
                    "ANOM_FUTURE_CAPTURE_TIMESTAMP",
                    "TIMESTAMP_INCONSISTENCY",
                    "HIGH",
                    "Future Capture Timestamp",
                    "Media capture date (" + metadata.getCapturedAt() + ") is set in the future relative to current UTC time. Indicates forged EXIF or uncalibrated system clock.",
                    "CapturedAt: " + metadata.getCapturedAt(),
                    0.90,
                    0.35
            ));
            totalScore += 0.35;
        }

        if (metadata.getModifiedAt() != null && metadata.getModifiedAt().isAfter(nowWithTolerance)) {
            anomalies.add(new ForensicAnomalyDto(
                    "ANOM_FUTURE_MODIFY_TIMESTAMP",
                    "TIMESTAMP_INCONSISTENCY",
                    "HIGH",
                    "Future Modification Timestamp",
                    "Media modification date (" + metadata.getModifiedAt() + ") is set in the future relative to current UTC time.",
                    "ModifiedAt: " + metadata.getModifiedAt(),
                    0.90,
                    0.35
            ));
            totalScore += 0.35;
        }

        // Rule 3: Inconsistent chronological timestamps (modified before captured)
        if (metadata.getCapturedAt() != null && metadata.getModifiedAt() != null) {
            if (metadata.getModifiedAt().isBefore(metadata.getCapturedAt().minusMinutes(1))) {
                anomalies.add(new ForensicAnomalyDto(
                        "ANOM_TIMESTAMP_INCONSISTENCY",
                        "TIMESTAMP_INCONSISTENCY",
                        "MEDIUM",
                        "Chronological Inconsistency in Timestamps",
                        "Media modification timestamp (" + metadata.getModifiedAt() + ") precedes original capture timestamp (" + metadata.getCapturedAt() + "). Violates chronological causality.",
                        "CapturedAt: " + metadata.getCapturedAt() + " vs ModifiedAt: " + metadata.getModifiedAt(),
                        0.80,
                        0.20
                ));
                totalScore += 0.20;
            }
        }

        // Rule 4: Metadata stripping on camera-originating media
        if (media.getMediaType() == MediaType.IMAGE && !metadata.isExifPresent() &&
                metadata.getCameraMake() == null && metadata.getCameraModel() == null) {
            anomalies.add(new ForensicAnomalyDto(
                    "ANOM_METADATA_STRIPPED",
                    "METADATA_STRIPPED",
                    "LOW",
                    "Metadata Stripped or Absent",
                    "Image contains no EXIF or camera container headers. Commonly observed in social media re-encodings (e.g. WhatsApp, Twitter/X) or deliberate privacy/forensic sanitization.",
                    "Zero EXIF directories found",
                    0.70,
                    0.05
            ));
            totalScore += 0.05;
        }

        // Rule 5: Camera Hardware vs Software Mismatch
        if (metadata.getCameraMake() != null && software != null) {
            String lowerMake = metadata.getCameraMake().toLowerCase(Locale.ROOT);
            for (String manufacturer : CAMERA_MANUFACTURERS) {
                if (lowerMake.contains(manufacturer)) {
                    String lowerSoft = software.toLowerCase(Locale.ROOT);
                    if (lowerSoft.contains("photoshop") || lowerSoft.contains("gimp") ||
                            lowerSoft.contains("capcut") || lowerSoft.contains("canva") ||
                            lowerSoft.contains("apple") || lowerSoft.contains("android")) {
                        anomalies.add(new ForensicAnomalyDto(
                                "ANOM_CAMERA_SOFTWARE_MISMATCH",
                                "DEVICE_INCONSISTENCY",
                                "HIGH",
                                "Camera Hardware and Software Mismatch",
                                "Camera hardware manufacturer (" + metadata.getCameraMake() + ") conflicts with post-capture software (" + software + "). Indicates external processing on camera capture.",
                                "Make: " + metadata.getCameraMake() + " | Software: " + software,
                                0.85,
                                0.35
                        ));
                        totalScore += 0.35;
                        break;
                    }
                }
            }
        }

        // Rule 6: GPS boundary and implausibility checks
        if (metadata.getGpsLatitude() != null && metadata.getGpsLongitude() != null) {
            double lat = metadata.getGpsLatitude();
            double lon = metadata.getGpsLongitude();

            if (lat < -90.0 || lat > 90.0 || lon < -180.0 || lon > 180.0) {
                anomalies.add(new ForensicAnomalyDto(
                        "ANOM_GPS_OUT_OF_BOUNDS",
                        "GPS_ANOMALY",
                        "HIGH",
                        "GPS Coordinates Out of Bounds",
                        "Geographic coordinates (Lat: " + lat + ", Lon: " + lon + ") exceed valid earthly latitude/longitude boundaries.",
                        "Coordinates: " + lat + ", " + lon,
                        0.95,
                        0.35
                ));
                totalScore += 0.35;
            } else if (Math.abs(lat) < 0.0001 && Math.abs(lon) < 0.0001) {
                anomalies.add(new ForensicAnomalyDto(
                        "ANOM_GPS_NULL_ISLAND",
                        "GPS_ANOMALY",
                        "MEDIUM",
                        "GPS Situated at Coordinate Origin (Null Island)",
                        "Coordinates are recorded at 0.0, 0.0. Frequently caused by default uncalibrated GPS receiver initialization or synthesized metadata tags.",
                        "Coordinates: (0.0, 0.0)",
                        0.75,
                        0.20
                ));
                totalScore += 0.20;
            }
        }

        // Rule 7: Video container stream consistency
        if (media.getMediaType() == MediaType.VIDEO) {
            if (metadata.getContainerFormat() != null && metadata.getVideoCodec() == null && metadata.getDurationSeconds() == null) {
                anomalies.add(new ForensicAnomalyDto(
                        "ANOM_VIDEO_STREAM_INCONSISTENCY",
                        "CONTAINER_INCONSISTENCY",
                        "MEDIUM",
                        "Missing Video Stream Track Information",
                        "Video container declared format (" + metadata.getContainerFormat() + ") but lacks standard video track stream or codec headers.",
                        "Container: " + metadata.getContainerFormat(),
                        0.75,
                        0.20
                ));
                totalScore += 0.20;
            }
        }

        double normalizedScore = Math.min(1.0, Math.round(totalScore * 10000.0) / 10000.0);
        return new EvaluationResult(anomalies, normalizedScore);
    }

    public record EvaluationResult(
            List<ForensicAnomalyDto> anomalies,
            double forensicScore
    ) {
    }
}
