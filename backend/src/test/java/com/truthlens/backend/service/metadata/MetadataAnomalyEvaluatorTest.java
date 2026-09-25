package com.truthlens.backend.service.metadata;

import com.truthlens.backend.dto.ForensicAnomalyDto;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("MetadataAnomalyEvaluator — Forensic Anomaly Detection Rules")
class MetadataAnomalyEvaluatorTest {

    private MetadataAnomalyEvaluator evaluator;
    private Media testMedia;

    @BeforeEach
    void setUp() {
        evaluator = new MetadataAnomalyEvaluator();
        User user = new User("tester@truthlens.org", "hash", "Tester");
        testMedia = new Media(user, "sample.jpg", "media/image/sample.jpg",
                MediaType.IMAGE, "image/jpeg", 2048, "dummy_hash", UploadStatus.UPLOADED);
    }

    @Test
    @DisplayName("Clean metadata yields zero anomalies and 0.0 forensic score")
    void evaluate_cleanMetadata_zeroAnomalies() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setCameraMake("Canon");
        meta.setCameraModel("Canon EOS 5D Mark IV");
        meta.setSoftwareTag("Canon EOS Firmware 1.3.3");
        meta.setExifPresent(true);

        OffsetDateTime captured = OffsetDateTime.now(ZoneOffset.UTC).minusDays(5);
        OffsetDateTime modified = OffsetDateTime.now(ZoneOffset.UTC).minusDays(5);
        meta.setCapturedAt(captured);
        meta.setModifiedAt(modified);
        meta.setGpsLatitude(37.7749);
        meta.setGpsLongitude(-122.4194);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies()).isEmpty();
        assertThat(result.forensicScore()).isEqualTo(0.0);
    }

    @Test
    @DisplayName("Rule 1: Editing software (Photoshop) triggers HIGH anomaly")
    void evaluate_editingSoftwarePhotoshop_triggersHighAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setSoftwareTag("Adobe Photoshop 2024 (Macintosh)");
        meta.setExifPresent(true);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies()).hasSize(1);
        ForensicAnomalyDto anomaly = result.anomalies().get(0);
        assertThat(anomaly.ruleId()).isEqualTo("ANOM_EDITING_SOFTWARE");
        assertThat(anomaly.severity()).isEqualTo("HIGH");
        assertThat(anomaly.category()).isEqualTo("SOFTWARE_MODIFICATION");
        assertThat(result.forensicScore()).isGreaterThanOrEqualTo(0.35);
    }

    @Test
    @DisplayName("Rule 1: Re-encoding software (ffmpeg) triggers MEDIUM anomaly")
    void evaluate_reEncodingSoftwareFfmpeg_triggersMediumAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setSoftwareTag("Lavf58.76.100 (ffmpeg)");
        meta.setExifPresent(true);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies()).hasSize(1);
        ForensicAnomalyDto anomaly = result.anomalies().get(0);
        assertThat(anomaly.ruleId()).isEqualTo("ANOM_RE_ENCODING_SOFTWARE");
        assertThat(anomaly.severity()).isEqualTo("MEDIUM");
        assertThat(result.forensicScore()).isEqualTo(0.20);
    }

    @Test
    @DisplayName("Rule 2: Future capture timestamp triggers HIGH anomaly")
    void evaluate_futureCaptureTimestamp_triggersHighAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setExifPresent(true);
        meta.setCapturedAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(10));

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies())
                .extracting(ForensicAnomalyDto::ruleId)
                .contains("ANOM_FUTURE_CAPTURE_TIMESTAMP");
        assertThat(result.forensicScore()).isGreaterThanOrEqualTo(0.35);
    }

    @Test
    @DisplayName("Rule 3: Modification preceding capture triggers MEDIUM anomaly")
    void evaluate_modifiedBeforeCaptured_triggersMediumAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setExifPresent(true);
        OffsetDateTime capture = OffsetDateTime.now(ZoneOffset.UTC).minusDays(2);
        OffsetDateTime mod = capture.minusDays(5); // Modified 5 days BEFORE captured
        meta.setCapturedAt(capture);
        meta.setModifiedAt(mod);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies())
                .extracting(ForensicAnomalyDto::ruleId)
                .contains("ANOM_TIMESTAMP_INCONSISTENCY");
        assertThat(result.forensicScore()).isEqualTo(0.20);
    }

    @Test
    @DisplayName("Rule 4: Missing EXIF on image triggers LOW stripped metadata anomaly")
    void evaluate_strippedMetadataOnImage_triggersLowAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setExifPresent(false);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies())
                .extracting(ForensicAnomalyDto::ruleId)
                .contains("ANOM_METADATA_STRIPPED");
        assertThat(result.forensicScore()).isEqualTo(0.05);
    }

    @Test
    @DisplayName("Rule 5: Hardware camera with mobile editing app triggers HIGH anomaly")
    void evaluate_cameraSoftwareMismatch_triggersHighAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setCameraMake("Nikon");
        meta.setCameraModel("Nikon D850");
        meta.setSoftwareTag("Adobe Photoshop Express (Android)");
        meta.setExifPresent(true);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies())
                .extracting(ForensicAnomalyDto::ruleId)
                .contains("ANOM_EDITING_SOFTWARE", "ANOM_CAMERA_SOFTWARE_MISMATCH");
        assertThat(result.forensicScore()).isGreaterThanOrEqualTo(0.70);
    }

    @Test
    @DisplayName("Rule 6: GPS coordinate out of bounds triggers HIGH anomaly")
    void evaluate_gpsOutOfBounds_triggersHighAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setExifPresent(true);
        meta.setGpsLatitude(120.0); // Invalid: lat > 90
        meta.setGpsLongitude(45.0);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies())
                .extracting(ForensicAnomalyDto::ruleId)
                .contains("ANOM_GPS_OUT_OF_BOUNDS");
        assertThat(result.forensicScore()).isGreaterThanOrEqualTo(0.35);
    }

    @Test
    @DisplayName("Rule 6: GPS at Null Island (0.0, 0.0) triggers MEDIUM anomaly")
    void evaluate_gpsNullIsland_triggersMediumAnomaly() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setExifPresent(true);
        meta.setGpsLatitude(0.0);
        meta.setGpsLongitude(0.0);

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies())
                .extracting(ForensicAnomalyDto::ruleId)
                .contains("ANOM_GPS_NULL_ISLAND");
        assertThat(result.forensicScore()).isEqualTo(0.20);
    }

    @Test
    @DisplayName("Multiple severe anomalies cap at forensic score 1.0")
    void evaluate_multipleSevereAnomalies_capsScoreAtOne() {
        ExtractedMetadata meta = new ExtractedMetadata();
        meta.setCameraMake("Sony");
        meta.setSoftwareTag("Adobe Photoshop 2024");
        meta.setCapturedAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(5));
        meta.setGpsLatitude(95.0); // Out of bounds
        meta.setGpsLongitude(200.0); // Out of bounds

        MetadataAnomalyEvaluator.EvaluationResult result = evaluator.evaluate(testMedia, meta);

        assertThat(result.anomalies().size()).isGreaterThanOrEqualTo(3);
        assertThat(result.forensicScore()).isEqualTo(1.0);
    }
}
