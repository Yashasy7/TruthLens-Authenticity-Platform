package com.truthlens.backend.service.metadata;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("CliMetadataExtractorEngine — ExifTool, MediaInfo & Stderr Separation Tests (FINDING-04-03, FINDING-04-04)")
class CliMetadataExtractorEngineTest {

    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
    }

    @Test
    @DisplayName("Engine reports availability based on tool detection")
    void isAvailable_reportsCorrectly() {
        CliMetadataExtractorEngine bothPresent = new CliMetadataExtractorEngine(objectMapper, true, true);
        assertThat(bothPresent.isAvailable()).isTrue();
        assertThat(bothPresent.getEngineName()).isEqualTo("EXIFTOOL_MEDIAINFO_CLI");

        CliMetadataExtractorEngine onlyExif = new CliMetadataExtractorEngine(objectMapper, true, false);
        assertThat(onlyExif.isAvailable()).isTrue();
        assertThat(onlyExif.getEngineName()).isEqualTo("EXIFTOOL_CLI");

        CliMetadataExtractorEngine onlyMediaInfo = new CliMetadataExtractorEngine(objectMapper, false, true);
        assertThat(onlyMediaInfo.isAvailable()).isTrue();
        assertThat(onlyMediaInfo.getEngineName()).isEqualTo("MEDIAINFO_CLI");

        CliMetadataExtractorEngine neither = new CliMetadataExtractorEngine(objectMapper, false, false);
        assertThat(neither.isAvailable()).isFalse();
        assertThat(neither.getEngineName()).isEqualTo("NONE");
    }

    @Test
    @DisplayName("parseExifToolJson: parses valid ExifTool JSON tags into ExtractedMetadata")
    void parseExifToolJson_validPayload() {
        CliMetadataExtractorEngine engine = new CliMetadataExtractorEngine(objectMapper, true, false);
        ExtractedMetadata result = new ExtractedMetadata();

        String exifJson = """
                [
                  {
                    "SourceFile": "test.jpg",
                    "Make": "Canon",
                    "Model": "EOS 5D Mark IV",
                    "Software": "Adobe Photoshop 2024",
                    "LensModel": "EF 24-70mm f/2.8L II USM",
                    "ImageWidth": 6720,
                    "ImageHeight": 4480,
                    "GPSLatitude": 37.7749,
                    "GPSLongitude": -122.4194
                  }
                ]
                """;

        engine.parseExifToolJson(exifJson, result);

        assertThat(result.getCameraMake()).isEqualTo("Canon");
        assertThat(result.getCameraModel()).isEqualTo("EOS 5D Mark IV");
        assertThat(result.getSoftwareTag()).isEqualTo("Adobe Photoshop 2024");
        assertThat(result.getLensModel()).isEqualTo("EF 24-70mm f/2.8L II USM");
        assertThat(result.getWidth()).isEqualTo(6720);
        assertThat(result.getHeight()).isEqualTo(4480);
        assertThat(result.getGpsLatitude()).isEqualTo(37.7749);
        assertThat(result.getGpsLongitude()).isEqualTo(-122.4194);
        assertThat(result.isExifPresent()).isTrue();
    }

    @Test
    @DisplayName("parseMediaInfoJson: parses General, Video, and Audio tracks into ExtractedMetadata (FINDING-04-03)")
    void parseMediaInfoJson_validMultiTrackPayload() {
        CliMetadataExtractorEngine engine = new CliMetadataExtractorEngine(objectMapper, false, true);
        ExtractedMetadata result = new ExtractedMetadata();

        String mediaInfoJson = """
                {
                  "media": {
                    "track": [
                      {
                        "@type": "General",
                        "Format": "MPEG-4",
                        "Duration": "15.500",
                        "OverallBitRate": "4500000"
                      },
                      {
                        "@type": "Video",
                        "Format": "AVC",
                        "Width": "1920",
                        "Height": "1080",
                        "FrameRate": "30.000"
                      },
                      {
                        "@type": "Audio",
                        "Format": "AAC",
                        "SamplingRate": "48000",
                        "Channels": "2"
                      }
                    ]
                  }
                }
                """;

        engine.parseMediaInfoJson(mediaInfoJson, result);

        assertThat(result.getContainerFormat()).isEqualTo("MPEG-4");
        assertThat(result.getDurationSeconds()).isEqualTo(15.5);
        assertThat(result.getBitrate()).isEqualTo(4500000L);
        assertThat(result.getVideoCodec()).isEqualTo("AVC");
        assertThat(result.getWidth()).isEqualTo(1920);
        assertThat(result.getHeight()).isEqualTo(1080);
        assertThat(result.getFrameRate()).isEqualTo(30.0);
        assertThat(result.getAudioCodec()).isEqualTo("AAC");
        assertThat(result.getAudioSampleRate()).isEqualTo(48000);
        assertThat(result.getAudioChannels()).isEqualTo(2);
    }

    @Test
    @DisplayName("Handles malformed JSON safely without throwing exceptions")
    void parseJson_malformedPayload_handledSafely() {
        CliMetadataExtractorEngine engine = new CliMetadataExtractorEngine(objectMapper, true, true);
        ExtractedMetadata result = new ExtractedMetadata();

        engine.parseExifToolJson("{invalid json", result);
        assertThat(result.getCameraMake()).isNull();

        engine.parseMediaInfoJson("not a json string", result);
        assertThat(result.getContainerFormat()).isNull();
    }

    @Test
    @DisplayName("FINDING-04-04: Valid stdout JSON parses successfully independent of stderr warnings")
    void parseExifToolJson_validPayload_whenStderrHasWarnings() {
        CliMetadataExtractorEngine engine = new CliMetadataExtractorEngine(objectMapper, true, false);
        ExtractedMetadata result = new ExtractedMetadata();

        // Valid stdout JSON (stderr warnings like 'Warning: [minor] Fixed incorrect URI' were sent to error stream)
        String stdoutJson = """
                [
                  {
                    "SourceFile": "warning_sample.jpg",
                    "Make": "Sony",
                    "Model": "ILCE-7RM4",
                    "ImageWidth": 9504,
                    "ImageHeight": 6336
                  }
                ]
                """;

        engine.parseExifToolJson(stdoutJson, result);

        assertThat(result.getCameraMake()).isEqualTo("Sony");
        assertThat(result.getCameraModel()).isEqualTo("ILCE-7RM4");
        assertThat(result.getWidth()).isEqualTo(9504);
        assertThat(result.getHeight()).isEqualTo(6336);
        assertThat(result.isExifPresent()).isTrue();
    }

    @Test
    @DisplayName("FINDING-04-05: ExifTool output exceeding 512KB is safely bounded to warning JSON")
    void parseExifToolJson_oversizedPayload_boundedAndSafe() {
        CliMetadataExtractorEngine engine = new CliMetadataExtractorEngine(objectMapper, true, false);
        ExtractedMetadata result = new ExtractedMetadata();

        // Generate JSON > 512KB
        String hugeString = "Z".repeat(550 * 1024);
        String oversizedJson = "[{\"Make\":\"HugeMake\",\"HugeField\":\"" + hugeString + "\"}]";

        engine.parseExifToolJson(oversizedJson, result);

        assertThat(result.getRawJson()).isEqualTo("{\"_warning\":\"ExifTool output exceeded 512KB limit\"}");
        assertThat(result.getCameraMake()).isEqualTo("HugeMake");
    }
}
