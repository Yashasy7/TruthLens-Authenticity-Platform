package com.truthlens.backend.service.metadata;

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
import java.io.DataOutputStream;
import java.io.IOException;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("Real Media Metadata Extraction Tests — Real Media Fixtures (FINDING-04-02)")
class RealMediaMetadataExtractionTest {

    private JavaMetadataExtractorEngine engine;

    @BeforeEach
    void setUp() {
        engine = new JavaMetadataExtractorEngine(new ObjectMapper());
    }

    @Test
    @DisplayName("JPEG without EXIF: correctly extracts visual dimensions and formats raw JSON")
    void extract_jpegWithoutExif() throws IOException {
        BufferedImage img = new BufferedImage(320, 240, BufferedImage.TYPE_INT_RGB);
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(img, "jpg", baos);

        ExtractedMetadata result = engine.extract(new ByteArrayInputStream(baos.toByteArray()), "plain.jpg", "image/jpeg");

        assertThat(result.getWidth()).isEqualTo(320);
        assertThat(result.getHeight()).isEqualTo(240);
        assertThat(result.isExifPresent()).isFalse();
        assertThat(result.getRawJson()).isNotEmpty();
    }

    @Test
    @DisplayName("PNG with dimensions: extracts width and height from PNG IHDR chunk")
    void extract_pngImage() throws IOException {
        BufferedImage img = new BufferedImage(400, 300, BufferedImage.TYPE_INT_ARGB);
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(img, "png", baos);

        ExtractedMetadata result = engine.extract(new ByteArrayInputStream(baos.toByteArray()), "graphic.png", "image/png");

        assertThat(result.getWidth()).isEqualTo(400);
        assertThat(result.getHeight()).isEqualTo(300);
    }

    @Test
    @DisplayName("Malformed media: handles corrupt stream gracefully")
    void extract_malformedMedia() {
        byte[] junk = new byte[]{0x00, 0x01, 0x02, (byte) 0xFF, (byte) 0xD8, 0x00, 0x10};
        ExtractedMetadata result = engine.extract(new ByteArrayInputStream(junk), "broken.jpg", "image/jpeg");

        assertThat(result).isNotNull();
        assertThat(result.getRawJson()).isEqualTo("{}");
    }

    @Test
    @DisplayName("FINDING-04-02: Extracts normalized audio parameters from synthetic WAV fixture")
    void extract_wavAudioFixture_normalizedFields() throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        DataOutputStream dos = new DataOutputStream(baos);

        // RIFF Header
        dos.writeBytes("RIFF");
        dos.writeInt(Integer.reverseBytes(36)); // chunk size
        dos.writeBytes("WAVE");

        // fmt subchunk
        dos.writeBytes("fmt ");
        dos.writeInt(Integer.reverseBytes(16)); // subchunk size
        dos.writeShort(Short.reverseBytes((short) 1)); // PCM format
        dos.writeShort(Short.reverseBytes((short) 2)); // 2 channels (stereo)
        dos.writeInt(Integer.reverseBytes(44100)); // 44.1 kHz sample rate
        dos.writeInt(Integer.reverseBytes(44100 * 2 * 2)); // byte rate = 176400 B/s
        dos.writeShort(Short.reverseBytes((short) 4)); // block align
        dos.writeShort(Short.reverseBytes((short) 16)); // 16 bits per sample

        // data subchunk
        dos.writeBytes("data");
        dos.writeInt(Integer.reverseBytes(0));

        dos.flush();
        byte[] wavBytes = baos.toByteArray();

        ExtractedMetadata result = engine.extract(new ByteArrayInputStream(wavBytes), "sample.wav", "audio/wav");

        assertThat(result).isNotNull();
        assertThat(result.getContainerFormat()).isEqualTo("WAV");
        assertThat(result.getAudioCodec()).isEqualTo("PCM");
        assertThat(result.getAudioSampleRate()).isEqualTo(44100);
        assertThat(result.getAudioChannels()).isEqualTo(2);
        assertThat(result.getBitrate()).isEqualTo(176400L * 8L);
    }

    @Test
    @DisplayName("FINDING-04-02: Extracts normalized audio parameters from synthetic MP3 frame fixture")
    void extract_mp3AudioFixture_normalizedFields() {
        // Construct synthetic MPEG-1 Layer 3 audio frame (128 kbps, 44.1 kHz, Stereo)
        // Frame size = 144 * 128000 / 44100 = 417 bytes
        byte[] mp3Frame = new byte[418];
        mp3Frame[0] = (byte) 0xFF; // Sync word
        mp3Frame[1] = (byte) 0xFB; // MPEG 1, Layer 3, no protection
        mp3Frame[2] = (byte) 0x90; // 128 kbps, 44100 Hz, no padding
        mp3Frame[3] = (byte) 0x00; // Stereo channel mode

        ExtractedMetadata result = engine.extract(new ByteArrayInputStream(mp3Frame), "track.mp3", "audio/mpeg");

        assertThat(result).isNotNull();
        assertThat(result.getContainerFormat()).isEqualTo("MP3");
        assertThat(result.getAudioCodec()).isEqualTo("MPEG-1/2 Audio Layer 3");
        assertThat(result.getAudioSampleRate()).isEqualTo(44100);
        assertThat(result.getAudioChannels()).isEqualTo(2);
        assertThat(result.getBitrate()).isEqualTo(128000L);
    }
}
