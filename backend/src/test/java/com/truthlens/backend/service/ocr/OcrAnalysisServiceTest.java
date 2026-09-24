package com.truthlens.backend.service.ocr;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.FastApiOcrResponse;
import com.truthlens.backend.dto.OcrBoundingBoxDto;
import com.truthlens.backend.dto.OcrEvidenceDto;
import com.truthlens.backend.dto.OcrResultResponse;
import com.truthlens.backend.dto.OcrTextRegionDto;
import com.truthlens.backend.entity.AnalysisStatus;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.OcrResult;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AiServiceException;
import com.truthlens.backend.exception.InvalidMediaException;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.OcrResultRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Field;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("OcrAnalysisService — Unit & Security Tests")
class OcrAnalysisServiceTest {

    @Mock
    private OcrResultRepository ocrResultRepository;

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private OcrAiServiceClient ocrAiServiceClient;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private OcrAnalysisService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private Media imageMedia;
    private Media videoMedia;
    private Media audioMedia;
    private UUID imageMediaId;
    private UUID videoMediaId;
    private UUID audioMediaId;

    @BeforeEach
    void setUp() throws Exception {
        service = new OcrAnalysisService(
                ocrResultRepository,
                mediaRepository,
                userRepository,
                storageService,
                ocrAiServiceClient,
                objectMapper
        );

        owner = new User("owner@truthlens.org", "pass123", "Owner User");
        setId(owner, UUID.randomUUID());
        owner.getRoles().add(new Role(RoleName.USER, "Standard User"));

        otherUser = new User("other@truthlens.org", "pass123", "Other User");
        setId(otherUser, UUID.randomUUID());
        otherUser.getRoles().add(new Role(RoleName.USER, "Standard User"));

        analyst = new User("analyst@truthlens.org", "pass123", "Analyst User");
        setId(analyst, UUID.randomUUID());
        analyst.getRoles().add(new Role(RoleName.ANALYST, "Analyst User"));

        imageMediaId = UUID.randomUUID();
        imageMedia = new Media(owner, "banner.png", "storage/banner.png", MediaType.IMAGE, "image/png", 2048L, "sha256img", UploadStatus.UPLOADED);
        setId(imageMedia, imageMediaId);

        videoMediaId = UUID.randomUUID();
        videoMedia = new Media(owner, "clip.mp4", "storage/clip.mp4", MediaType.VIDEO, "video/mp4", 1048576L, "sha256vid", UploadStatus.UPLOADED);
        setId(videoMedia, videoMediaId);

        audioMediaId = UUID.randomUUID();
        audioMedia = new Media(owner, "speech.wav", "storage/speech.wav", MediaType.AUDIO, "audio/wav", 512000L, "sha256aud", UploadStatus.UPLOADED);
        setId(audioMedia, audioMediaId);
    }

    private void setId(Object target, UUID id) throws Exception {
        Field idField = target.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(target, id);
    }

    private FastApiOcrResponse buildSampleAiResponse() {
        OcrBoundingBoxDto bbox = new OcrBoundingBoxDto(10, 20, 100, 30, List.of(0.1, 0.2, 0.5, 0.1), List.of());
        OcrTextRegionDto region = new OcrTextRegionDto("SAMPLE HEADLINE", 0.92, bbox, "en", 0, 0.0, 0.0, 1.0);
        OcrEvidenceDto evidence = new OcrEvidenceDto(1, List.of("en"), 300, 200, "EasyOCR", List.of("CLAHE"), "IMAGE", 1, Map.of());

        return new FastApiOcrResponse(
                "SAMPLE HEADLINE",
                "en",
                0.92,
                1,
                List.of(region),
                evidence,
                "COMPLETED",
                null
        );
    }

    @Test
    @DisplayName("getOcrResult: media owner triggers analysis successfully")
    void getOcrResult_owner_success() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(ocrResultRepository.findByMediaId(imageMediaId)).thenReturn(Optional.empty());

        when(storageService.load(imageMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("image bytes".getBytes()));
        when(ocrAiServiceClient.analyzeOcr(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(ocrResultRepository.save(any(OcrResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OcrResultResponse response = service.getOcrResult(imageMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getExtractedText()).isEqualTo("SAMPLE HEADLINE");
        assertThat(response.getConfidenceScore()).isEqualTo(0.92);
        assertThat(response.getRegionsCount()).isEqualTo(1);
        verify(ocrAiServiceClient).analyzeOcr(any(), any(), any());
    }

    @Test
    @DisplayName("getOcrResult: analyst accessing other user's media succeeds via elevated role")
    void getOcrResult_analyst_success() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));
        when(ocrResultRepository.findByMediaId(imageMediaId)).thenReturn(Optional.empty());

        when(storageService.load(imageMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("image bytes".getBytes()));
        when(ocrAiServiceClient.analyzeOcr(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(ocrResultRepository.save(any(OcrResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OcrResultResponse response = service.getOcrResult(imageMediaId, analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getExtractedText()).isEqualTo("SAMPLE HEADLINE");
    }

    @Test
    @DisplayName("getOcrResult: IDOR blocked when unauthorized user accesses another user's media")
    void getOcrResult_idor_throwsAccessDeniedException() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getOcrResult(imageMediaId, otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("Access denied");

        verify(ocrResultRepository, never()).findByMediaId(any());
        verify(ocrAiServiceClient, never()).analyzeOcr(any(), any(), any());
    }

    @Test
    @DisplayName("getOcrResult: returns cached result without invoking AI service if already analyzed")
    void getOcrResult_cached_returnsExisting() {
        OcrResult existing = new OcrResult(
                imageMedia, "CACHED TEXT", "en", 0.95, 1, "[]", "{}", AnalysisStatus.COMPLETED
        );

        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(ocrResultRepository.findByMediaId(imageMediaId)).thenReturn(Optional.of(existing));

        OcrResultResponse response = service.getOcrResult(imageMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getExtractedText()).isEqualTo("CACHED TEXT");
        verify(ocrAiServiceClient, never()).analyzeOcr(any(), any(), any());
    }

    @Test
    @DisplayName("reanalyzeOcr: forces fresh evaluation even when previous result exists")
    void reanalyzeOcr_forcesFreshEvaluation() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(ocrResultRepository.findByMediaId(imageMediaId)).thenReturn(Optional.empty());

        when(storageService.load(imageMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("image bytes".getBytes()));
        when(ocrAiServiceClient.analyzeOcr(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(ocrResultRepository.save(any(OcrResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OcrResultResponse response = service.reanalyzeOcr(imageMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        verify(ocrAiServiceClient).analyzeOcr(any(), any(), any());
    }

    @Test
    @DisplayName("getOcrResult: unsupported media type AUDIO throws InvalidMediaException")
    void getOcrResult_audioMediaType_throwsInvalidMediaException() {
        when(mediaRepository.findById(audioMediaId)).thenReturn(Optional.of(audioMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        assertThatThrownBy(() -> service.getOcrResult(audioMediaId, owner.getEmail()))
                .isInstanceOf(InvalidMediaException.class)
                .hasMessageContaining("OCR text extraction is only supported for image and video assets");

        verify(ocrAiServiceClient, never()).analyzeOcr(any(), any(), any());
    }

    @Test
    @DisplayName("getOcrResult: VIDEO media asset is accepted and processed successfully")
    void getOcrResult_videoMedia_success() {
        when(mediaRepository.findById(videoMediaId)).thenReturn(Optional.of(videoMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(ocrResultRepository.findByMediaId(videoMediaId)).thenReturn(Optional.empty());

        when(storageService.load(videoMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("video bytes".getBytes()));
        when(ocrAiServiceClient.analyzeOcr(any(), any(), any())).thenReturn(buildSampleAiResponse());
        when(ocrResultRepository.save(any(OcrResult.class))).thenAnswer(invocation -> invocation.getArgument(0));

        OcrResultResponse response = service.getOcrResult(videoMediaId, owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.getExtractedText()).isEqualTo("SAMPLE HEADLINE");
    }

    @Test
    @DisplayName("getOcrResult: AI service failure records FAILED status in database")
    void getOcrResult_aiFailure_persistsFailure() {
        when(mediaRepository.findById(imageMediaId)).thenReturn(Optional.of(imageMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));
        when(ocrResultRepository.findByMediaId(imageMediaId)).thenReturn(Optional.empty());

        when(storageService.load(imageMedia.getStoragePath())).thenReturn(new ByteArrayInputStream("image bytes".getBytes()));
        when(ocrAiServiceClient.analyzeOcr(any(), any(), any()))
                .thenThrow(new AiServiceException("Downstream OCR failed"));

        assertThatThrownBy(() -> service.getOcrResult(imageMediaId, owner.getEmail()))
                .isInstanceOf(AiServiceException.class);

        verify(ocrResultRepository).save(any(OcrResult.class));
    }
}
