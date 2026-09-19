package com.truthlens.backend.service.validation;

import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.exception.FileSizeExceededException;
import com.truthlens.backend.exception.InvalidMediaException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("MediaValidationService — Apache Tika Validation Tests")
class MediaValidationServiceTest {

    private MediaValidationService validationService;

    @BeforeEach
    void setUp() {
        // Set max limit to 10MB for test
        validationService = new MediaValidationService(10 * 1024 * 1024);
    }

    @Test
    @DisplayName("Validates real PNG image using magic bytes")
    void validate_validPng_success() {
        byte[] pngBytes = new byte[]{
                (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52
        };
        MockMultipartFile file = new MockMultipartFile("file", "sample.png", "image/png", pngBytes);

        MediaValidationService.ValidationResult result = validationService.validate(file);

        assertThat(result.mediaType()).isEqualTo(MediaType.IMAGE);
        assertThat(result.mimeType()).isEqualTo("image/png");
        assertThat(result.sanitizedFilename()).isEqualTo("sample.png");
        assertThat(result.fileSize()).isEqualTo(pngBytes.length);
    }

    @Test
    @DisplayName("Validates plain text file")
    void validate_plainText_success() {
        byte[] textBytes = "Authenticity analysis report transcript.".getBytes(StandardCharsets.UTF_8);
        MockMultipartFile file = new MockMultipartFile("file", "transcript.txt", "text/plain", textBytes);

        MediaValidationService.ValidationResult result = validationService.validate(file);

        assertThat(result.mediaType()).isEqualTo(MediaType.TEXT);
        assertThat(result.mimeType()).isEqualTo("text/plain");
    }

    @Test
    @DisplayName("Validates PDF document using magic bytes")
    void validate_validPdf_success() {
        byte[] pdfBytes = "%PDF-1.4 mock content".getBytes(StandardCharsets.UTF_8);
        MockMultipartFile file = new MockMultipartFile("file", "dossier.pdf", "application/pdf", pdfBytes);

        MediaValidationService.ValidationResult result = validationService.validate(file);

        assertThat(result.mediaType()).isEqualTo(MediaType.TEXT);
        assertThat(result.mimeType()).isEqualTo("application/pdf");
    }

    @Test
    @DisplayName("Detects real content type even when extension is spoofed")
    void validate_spoofedExtension_detectsTrueType() {
        // Plain text content named as .jpg
        byte[] textBytes = "Hello this is just a plain text document".getBytes(StandardCharsets.UTF_8);
        MockMultipartFile file = new MockMultipartFile("file", "fake_photo.jpg", "image/jpeg", textBytes);

        MediaValidationService.ValidationResult result = validationService.validate(file);

        // Apache Tika should detect text/plain, mapping it to TEXT rather than trusting client image/jpeg
        assertThat(result.mediaType()).isEqualTo(MediaType.TEXT);
        assertThat(result.mimeType()).isEqualTo("text/plain");
    }

    @Test
    @DisplayName("Rejects unsupported executable binaries")
    void validate_unsupportedExecutable_throwsInvalidMediaException() {
        // Linux ELF binary header: 0x7F 'E' 'L' 'F'
        byte[] elfBytes = new byte[]{0x7F, 0x45, 0x4C, 0x46, 0x02, 0x01, 0x01, 0x00};
        MockMultipartFile file = new MockMultipartFile("file", "malware.elf", "application/octet-stream", elfBytes);

        assertThatThrownBy(() -> validationService.validate(file))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("Unsupported file format");
    }

    @Test
    @DisplayName("Rejects empty file (0 bytes)")
    void validate_emptyFile_throwsInvalidMediaException() {
        MockMultipartFile file = new MockMultipartFile("file", "empty.jpg", "image/jpeg", new byte[0]);

        assertThatThrownBy(() -> validationService.validate(file))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("missing or empty");
    }

    @Test
    @DisplayName("Rejects oversized file")
    void validate_oversizedFile_throwsFileSizeExceededException() {
        // Validation service configured with 10MB limit; pass 11MB
        byte[] data = new byte[100];
        // Create custom MockMultipartFile reporting oversized size
        MockMultipartFile file = new MockMultipartFile("file", "large.png", "image/png", data) {
            @Override
            public long getSize() {
                return 11 * 1024 * 1024L;
            }
        };

        assertThatThrownBy(() -> validationService.validate(file))
                .isInstanceOf(FileSizeExceededException.class)
                .hasMessageContaining("exceeds maximum limit");
    }

    @Test
    @DisplayName("Sanitizes path traversal and Windows path filenames")
    void sanitizeFilename_traversalAttempts_cleansProperly() {
        assertThat(validationService.sanitizeFilename("../../etc/passwd.jpg")).isEqualTo("passwd.jpg");
        assertThat(validationService.sanitizeFilename("C:\\Users\\admin\\Desktop\\photo.png")).isEqualTo("photo.png");
        assertThat(validationService.sanitizeFilename("bad\0filename.mp4")).isEqualTo("badfilename.mp4");
        assertThat(validationService.sanitizeFilename("")).isEqualTo("unnamed_upload");
    }

    @Test
    @DisplayName("Rejects HTML documents to eliminate stored-XSS hazards")
    void validate_htmlDocument_rejectedAsUnsupported() {
        byte[] htmlBytes = "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Content</h1></body></html>"
                .getBytes(StandardCharsets.UTF_8);
        MockMultipartFile file = new MockMultipartFile("file", "index.html", "text/html", htmlBytes);

        assertThatThrownBy(() -> validationService.validate(file))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("Unsupported file format: 'text/html'");
    }
}
