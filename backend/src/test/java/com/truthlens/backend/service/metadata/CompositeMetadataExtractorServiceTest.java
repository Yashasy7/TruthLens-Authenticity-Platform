package com.truthlens.backend.service.metadata;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("CompositeMetadataExtractorService — Fallback & Stream Reusability Tests (FINDING-04-01)")
class CompositeMetadataExtractorServiceTest {

    @Mock
    private JavaMetadataExtractorEngine javaEngine;

    @Mock
    private CliMetadataExtractorEngine cliEngine;

    private CompositeMetadataExtractorService compositeService;

    @BeforeEach
    void setUp() {
        compositeService = new CompositeMetadataExtractorService(javaEngine, cliEngine);
    }

    @Test
    @DisplayName("1. CLI engine succeeds with complete metadata -> Java engine not invoked")
    void extractMetadata_cliSucceeds_javaNotInvoked() {
        when(cliEngine.isAvailable()).thenReturn(true);

        ExtractedMetadata cliResult = new ExtractedMetadata();
        cliResult.setExifPresent(true);
        cliResult.setCameraMake("Nikon");
        cliResult.setWidth(1920);
        when(cliEngine.extract(any(InputStream.class), eq("photo.jpg"), eq("image/jpeg")))
                .thenReturn(cliResult);

        InputStream stream = new ByteArrayInputStream("dummy image content".getBytes(StandardCharsets.UTF_8));
        ExtractedMetadata result = compositeService.extractMetadata(stream, "photo.jpg", "image/jpeg");

        assertThat(result).isSameAs(cliResult);
        assertThat(result.getCameraMake()).isEqualTo("Nikon");
        verify(javaEngine, never()).extract(any(), any(), any());
    }

    @Test
    @DisplayName("2. CLI engine unavailable -> streams directly to Java engine")
    void extractMetadata_cliUnavailable_delegatesDirectlyToJava() {
        when(cliEngine.isAvailable()).thenReturn(false);

        ExtractedMetadata javaResult = new ExtractedMetadata();
        javaResult.setCameraMake("Canon");
        when(javaEngine.extract(any(InputStream.class), eq("photo.jpg"), eq("image/jpeg")))
                .thenReturn(javaResult);

        InputStream stream = new ByteArrayInputStream("sample bytes".getBytes(StandardCharsets.UTF_8));
        ExtractedMetadata result = compositeService.extractMetadata(stream, "photo.jpg", "image/jpeg");

        assertThat(result).isSameAs(javaResult);
        verify(cliEngine, never()).extract(any(), any(), any());
        verify(javaEngine).extract(any(), eq("photo.jpg"), eq("image/jpeg"));
    }

    @Test
    @DisplayName("3. CLI engine returns incomplete metadata -> Java fallback succeeds")
    void extractMetadata_cliIncomplete_fallsBackToJava() {
        when(cliEngine.isAvailable()).thenReturn(true);

        // Incomplete result (no EXIF, no width, no duration, no audio, empty raw tree)
        ExtractedMetadata incompleteCli = new ExtractedMetadata();
        when(cliEngine.extract(any(InputStream.class), eq("sample.jpg"), eq("image/jpeg")))
                .thenReturn(incompleteCli);

        ExtractedMetadata javaResult = new ExtractedMetadata();
        javaResult.setWidth(800);
        javaResult.setHeight(600);
        when(javaEngine.extract(any(InputStream.class), eq("sample.jpg"), eq("image/jpeg")))
                .thenReturn(javaResult);

        InputStream stream = new ByteArrayInputStream("image data".getBytes(StandardCharsets.UTF_8));
        ExtractedMetadata result = compositeService.extractMetadata(stream, "sample.jpg", "image/jpeg");

        assertThat(result).isSameAs(javaResult);
        assertThat(result.getWidth()).isEqualTo(800);
        verify(javaEngine).extract(any(InputStream.class), eq("sample.jpg"), eq("image/jpeg"));
    }

    @Test
    @DisplayName("4. CLI engine throws exception -> Java fallback succeeds safely")
    void extractMetadata_cliThrows_fallsBackToJava() {
        when(cliEngine.isAvailable()).thenReturn(true);
        when(cliEngine.extract(any(InputStream.class), eq("broken.jpg"), eq("image/jpeg")))
                .thenThrow(new RuntimeException("Process failure"));

        ExtractedMetadata javaResult = new ExtractedMetadata();
        javaResult.setContainerFormat("JPEG");
        when(javaEngine.extract(any(InputStream.class), eq("broken.jpg"), eq("image/jpeg")))
                .thenReturn(javaResult);

        InputStream stream = new ByteArrayInputStream("image data".getBytes(StandardCharsets.UTF_8));
        ExtractedMetadata result = compositeService.extractMetadata(stream, "broken.jpg", "image/jpeg");

        assertThat(result).isSameAs(javaResult);
        assertThat(result.getContainerFormat()).isEqualTo("JPEG");
        verify(javaEngine).extract(any(InputStream.class), eq("broken.jpg"), eq("image/jpeg"));
    }

    @Test
    @DisplayName("5. CLI engine consumes stream -> Java fallback STILL receives complete data (FINDING-04-01 fixed)")
    void extractMetadata_cliConsumesStream_javaReceivesCompleteData() {
        when(cliEngine.isAvailable()).thenReturn(true);

        byte[] originalContent = "critical_media_payload_that_must_not_be_lost".getBytes(StandardCharsets.UTF_8);

        // Simulate CLI engine consuming stream to EOF and failing
        when(cliEngine.extract(any(InputStream.class), eq("test.jpg"), eq("image/jpeg")))
                .thenAnswer(invocation -> {
                    InputStream is = invocation.getArgument(0);
                    is.readAllBytes(); // Read to EOF
                    return new ExtractedMetadata(); // Incomplete result
                });

        // Verify Java engine receives a fresh, unexhausted stream with all original bytes
        when(javaEngine.extract(any(InputStream.class), eq("test.jpg"), eq("image/jpeg")))
                .thenAnswer(invocation -> {
                    InputStream is = invocation.getArgument(0);
                    byte[] received = is.readAllBytes();
                    assertThat(received).isEqualTo(originalContent);
                    ExtractedMetadata javaMeta = new ExtractedMetadata();
                    javaMeta.setWidth(1024);
                    return javaMeta;
                });

        InputStream stream = new ByteArrayInputStream(originalContent);
        ExtractedMetadata result = compositeService.extractMetadata(stream, "test.jpg", "image/jpeg");

        assertThat(result.getWidth()).isEqualTo(1024);
    }

    @Test
    @DisplayName("6. Real JPEG fixture fallback works seamlessly through real Java engine")
    void extractMetadata_realJpegFixture_fallbackSucceeds() throws IOException {
        BufferedImage image = new BufferedImage(160, 120, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = image.createGraphics();
        g.setColor(Color.RED);
        g.fillRect(0, 0, 160, 120);
        g.dispose();

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "jpg", baos);
        byte[] jpegBytes = baos.toByteArray();

        JavaMetadataExtractorEngine realJavaEngine = new JavaMetadataExtractorEngine(new ObjectMapper());
        CompositeMetadataExtractorService service = new CompositeMetadataExtractorService(realJavaEngine, cliEngine);

        when(cliEngine.isAvailable()).thenReturn(true);
        when(cliEngine.extract(any(), eq("red.jpg"), eq("image/jpeg")))
                .thenAnswer(inv -> {
                    ((InputStream) inv.getArgument(0)).readAllBytes(); // exhaust
                    return new ExtractedMetadata(); // incomplete
                });

        ExtractedMetadata result = service.extractMetadata(new ByteArrayInputStream(jpegBytes), "red.jpg", "image/jpeg");

        assertThat(result).isNotNull();
        assertThat(result.getWidth()).isEqualTo(160);
        assertThat(result.getHeight()).isEqualTo(120);
    }

    @Test
    @DisplayName("7. Oversized stream (>25MB) is bounded safely and returns empty metadata without crash")
    void extractMetadata_oversizedStream_boundsSafely() {
        when(cliEngine.isAvailable()).thenReturn(true);

        // Stream that yields 25MB + 100 bytes without allocating full heap array upfront
        InputStream largeStream = new InputStream() {
            private int count = 0;
            @Override
            public int read() {
                if (count++ < CompositeMetadataExtractorService.MAX_BUFFER_SIZE_BYTES + 100) {
                    return 0x55;
                }
                return -1;
            }
        };

        ExtractedMetadata result = compositeService.extractMetadata(largeStream, "huge.bin", "application/octet-stream");

        assertThat(result).isNotNull();
        verify(cliEngine, never()).extract(any(), any(), any());
        verify(javaEngine, never()).extract(any(), any(), any());
    }
}
