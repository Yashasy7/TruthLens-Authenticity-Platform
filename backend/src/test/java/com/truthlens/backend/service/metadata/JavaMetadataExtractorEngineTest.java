package com.truthlens.backend.service.metadata;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("JavaMetadataExtractorEngine — Pure-Java Extraction & Bounded JSON (FINDING-04-05)")
class JavaMetadataExtractorEngineTest {

    private JavaMetadataExtractorEngine engine;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        engine = new JavaMetadataExtractorEngine(objectMapper);
    }

    @Test
    @DisplayName("Engine reports availability and correct engine name")
    void engineMetadata() {
        assertThat(engine.isAvailable()).isTrue();
        assertThat(engine.getEngineName()).isEqualTo("JAVA_METADATA_EXTRACTOR");
    }

    @Test
    @DisplayName("Extracts basic properties from generated JPEG image stream")
    void extract_validJpegImage() throws Exception {
        BufferedImage image = new BufferedImage(120, 80, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = image.createGraphics();
        g.setColor(Color.BLUE);
        g.fillRect(0, 0, 120, 80);
        g.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "jpg", baos);
        byte[] jpegBytes = baos.toByteArray();

        ExtractedMetadata result = engine.extract(new ByteArrayInputStream(jpegBytes), "test.jpg", "image/jpeg");

        assertThat(result).isNotNull();
        assertThat(result.getExtractionEngine()).isEqualTo("JAVA_METADATA_EXTRACTOR");
        assertThat(result.getWidth()).isEqualTo(120);
        assertThat(result.getHeight()).isEqualTo(80);
        assertThat(result.getRawJson()).isNotEmpty();
    }

    @Test
    @DisplayName("Handles null input stream safely")
    void extract_nullStream() {
        ExtractedMetadata result = engine.extract(null, "none.jpg", "image/jpeg");
        assertThat(result).isNotNull();
        assertThat(result.getRawMetadataTree()).isEmpty();
    }

    @Test
    @DisplayName("Handles corrupt or random binary stream safely without crashing")
    void extract_corruptStream() {
        byte[] randomData = new byte[]{0x12, 0x34, 0x56, 0x78, (byte) 0x9A, (byte) 0xBC};
        InputStream is = new ByteArrayInputStream(randomData);

        ExtractedMetadata result = engine.extract(is, "corrupt.jpg", "image/jpeg");
        assertThat(result).isNotNull();
        assertThat(result.getRawJson()).isEqualTo("{}");
    }

    @Test
    @DisplayName("FINDING-04-05: Serializes normal metadata tree without truncation")
    void serializeBoundedRawJson_normalPayload() {
        Map<String, Map<String, String>> tree = new LinkedHashMap<>();
        Map<String, String> ifd0 = new LinkedHashMap<>();
        ifd0.put("Make", "Canon");
        ifd0.put("Model", "EOS 5D");
        tree.put("Exif IFD0", ifd0);

        String json = engine.serializeBoundedRawJson(tree);

        assertThat(json).contains("Canon").contains("EOS 5D");
        assertThat(json).doesNotContain("TRUNCATED");
    }

    @Test
    @DisplayName("FINDING-04-05: Bounds oversized metadata (>512KB) into safe, valid truncated JSON")
    void serializeBoundedRawJson_oversizedPayload_boundedAndValidJson() throws Exception {
        Map<String, Map<String, String>> tree = new LinkedHashMap<>();

        // Generate 600KB of tags
        for (int i = 0; i < 20; i++) {
            Map<String, String> dir = new LinkedHashMap<>();
            for (int j = 0; j < 50; j++) {
                dir.put("OversizedTag_" + j, "X".repeat(600));
            }
            tree.put("Directory_" + i, dir);
        }

        String json = engine.serializeBoundedRawJson(tree);

        // Verify JSON is bounded <= 512KB
        assertThat(json.getBytes(StandardCharsets.UTF_8).length).isLessThanOrEqualTo(JavaMetadataExtractorEngine.MAX_RAW_METADATA_BYTES);

        // Verify JSON is strictly valid
        JsonNode root = objectMapper.readTree(json);
        assertThat(root.has("_metadata_status")).isTrue();
        assertThat(root.get("_metadata_status").asText()).isEqualTo("TRUNCATED");
        assertThat(root.has("directories")).isTrue();
    }
}
