package com.truthlens.backend.service.metadata;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.truthlens.backend.dto.ForensicAnomalyDto;
import com.truthlens.backend.dto.MediaMetadataResponse;
import com.truthlens.backend.dto.MetadataAnomalyReportResponse;
import com.truthlens.backend.entity.Media;
import com.truthlens.backend.entity.MediaMetadata;
import com.truthlens.backend.entity.MediaType;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.UploadStatus;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.MediaNotFoundException;
import com.truthlens.backend.repository.MediaMetadataRepository;
import com.truthlens.backend.repository.MediaRepository;
import com.truthlens.backend.repository.UserRepository;
import com.truthlens.backend.service.storage.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.access.AccessDeniedException;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Field;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
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
@DisplayName("MediaMetadataService — Unit & Security Tests")
class MediaMetadataServiceTest {

    @Mock
    private MediaRepository mediaRepository;

    @Mock
    private MediaMetadataRepository mediaMetadataRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private StorageService storageService;

    @Mock
    private CompositeMetadataExtractorService extractorService;

    @Mock
    private MetadataAnomalyEvaluator anomalyEvaluator;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private MediaMetadataService service;

    private User owner;
    private User otherUser;
    private User analyst;
    private User researcher;
    private Media testMedia;

    @BeforeEach
    void setUp() throws Exception {
        service = new MediaMetadataService(
                mediaRepository,
                mediaMetadataRepository,
                userRepository,
                storageService,
                extractorService,
                anomalyEvaluator,
                objectMapper
        );

        Role userRole = new Role(RoleName.USER, "Standard User");
        Role analystRole = new Role(RoleName.ANALYST, "Analyst");
        Role researcherRole = new Role(RoleName.RESEARCHER, "Researcher");

        owner = new User("owner@truthlens.org", "hash", "Owner");
        owner.getRoles().add(userRole);
        setEntityId(owner, UUID.randomUUID());

        otherUser = new User("other@truthlens.org", "hash", "Other User");
        otherUser.getRoles().add(userRole);
        setEntityId(otherUser, UUID.randomUUID());

        analyst = new User("analyst@truthlens.org", "hash", "Analyst");
        analyst.getRoles().add(analystRole);
        setEntityId(analyst, UUID.randomUUID());

        researcher = new User("researcher@truthlens.org", "hash", "Researcher");
        researcher.getRoles().add(researcherRole);
        setEntityId(researcher, UUID.randomUUID());

        testMedia = new Media(owner, "photo.jpg", "storage/photo.jpg",
                MediaType.IMAGE, "image/jpeg", 4096, "hash123", UploadStatus.UPLOADED);
        setEntityId(testMedia, UUID.randomUUID());
    }

    private void setEntityId(Object entity, UUID id) throws Exception {
        Field idField = entity.getClass().getDeclaredField("id");
        idField.setAccessible(true);
        idField.set(entity, id);
    }

    @Test
    @DisplayName("extractAndSaveMetadata: extracts and persists metadata successfully")
    void extractAndSaveMetadata_success() {
        when(mediaMetadataRepository.findByMediaId(testMedia.getId())).thenReturn(Optional.empty());
        when(storageService.load(testMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(new byte[10]));

        ExtractedMetadata extracted = new ExtractedMetadata();
        extracted.setCameraMake("Nikon");
        extracted.setCameraModel("D850");
        extracted.setRawJson("{\"Make\": \"Nikon\"}");
        when(extractorService.extractMetadata(any(), eq(testMedia.getOriginalFilename()), eq(testMedia.getMimeType())))
                .thenReturn(extracted);

        when(anomalyEvaluator.evaluate(eq(testMedia), eq(extracted)))
                .thenReturn(new MetadataAnomalyEvaluator.EvaluationResult(List.of(), 0.0));

        when(mediaMetadataRepository.saveAndFlush(any(MediaMetadata.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        MediaMetadataResponse response = service.extractAndSaveMetadata(testMedia);

        assertThat(response).isNotNull();
        assertThat(response.cameraMake()).isEqualTo("Nikon");
        assertThat(response.cameraModel()).isEqualTo("D850");
        assertThat(response.hasAnomalies()).isFalse();
        assertThat(response.forensicScore()).isEqualTo(0.0);
    }

    @Test
    @DisplayName("extractAndSaveMetadata: returns existing record if already present")
    void extractAndSaveMetadata_alreadyExists_returnsExisting() {
        MediaMetadata existing = new MediaMetadata(testMedia);
        existing.setCameraMake("Sony");
        existing.setRawJson("{}");
        when(mediaMetadataRepository.findByMediaId(testMedia.getId())).thenReturn(Optional.of(existing));

        MediaMetadataResponse response = service.extractAndSaveMetadata(testMedia);

        assertThat(response.cameraMake()).isEqualTo("Sony");
        verify(storageService, never()).load(any());
        verify(mediaMetadataRepository, never()).saveAndFlush(any());
    }

    @Test
    @DisplayName("extractAndSaveMetadata: safely catches DataIntegrityViolationException on concurrent race")
    void extractAndSaveMetadata_concurrencyRace_recoversGracefully() {
        when(mediaMetadataRepository.findByMediaId(testMedia.getId()))
                .thenReturn(Optional.empty());
        when(storageService.load(testMedia.getStoragePath())).thenReturn(new ByteArrayInputStream(new byte[10]));

        ExtractedMetadata extracted = new ExtractedMetadata();
        extracted.setRawJson("{}");
        when(extractorService.extractMetadata(any(), any(), any())).thenReturn(extracted);
        when(anomalyEvaluator.evaluate(any(), any()))
                .thenReturn(new MetadataAnomalyEvaluator.EvaluationResult(List.of(), 0.0));

        MediaMetadata existingWinner = new MediaMetadata(testMedia);
        existingWinner.setCameraMake("WinnerMake");
        existingWinner.setRawJson("{}");

        when(mediaMetadataRepository.saveAndFlush(any(MediaMetadata.class)))
                .thenThrow(new DataIntegrityViolationException("Unique constraint violation"));
        when(mediaMetadataRepository.findByMediaId(testMedia.getId()))
                .thenReturn(Optional.empty())
                .thenReturn(Optional.of(existingWinner));

        MediaMetadataResponse response = service.extractAndSaveMetadata(testMedia);

        assertThat(response.cameraMake()).isEqualTo("WinnerMake");
    }

    @Test
    @DisplayName("getMetadata: owner can access their own media metadata")
    void getMetadata_ownerAccess_success() {
        when(mediaRepository.findById(testMedia.getId())).thenReturn(Optional.of(testMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        MediaMetadata metadata = new MediaMetadata(testMedia);
        metadata.setCameraMake("Canon");
        metadata.setRawJson("{}");
        when(mediaMetadataRepository.findByMediaId(testMedia.getId())).thenReturn(Optional.of(metadata));

        MediaMetadataResponse response = service.getMetadata(testMedia.getId(), owner.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.cameraMake()).isEqualTo("Canon");
    }

    @Test
    @DisplayName("getMetadata: elevated ANALYST can access another user's metadata")
    void getMetadata_analystAccess_success() {
        when(mediaRepository.findById(testMedia.getId())).thenReturn(Optional.of(testMedia));
        when(userRepository.findByEmail(analyst.getEmail())).thenReturn(Optional.of(analyst));

        MediaMetadata metadata = new MediaMetadata(testMedia);
        metadata.setCameraMake("Canon");
        metadata.setRawJson("{}");
        when(mediaMetadataRepository.findByMediaId(testMedia.getId())).thenReturn(Optional.of(metadata));

        MediaMetadataResponse response = service.getMetadata(testMedia.getId(), analyst.getEmail());

        assertThat(response).isNotNull();
        assertThat(response.cameraMake()).isEqualTo("Canon");
    }

    @Test
    @DisplayName("getMetadata: unauthorized standard USER accessing another user's media throws AccessDeniedException")
    void getMetadata_unauthorizedUser_throwsAccessDenied() {
        when(mediaRepository.findById(testMedia.getId())).thenReturn(Optional.of(testMedia));
        when(userRepository.findByEmail(otherUser.getEmail())).thenReturn(Optional.of(otherUser));

        assertThatThrownBy(() -> service.getMetadata(testMedia.getId(), otherUser.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("You do not have permission");
    }

    @Test
    @DisplayName("getMetadata: RESEARCHER accessing another user's media throws AccessDeniedException")
    void getMetadata_researcherAccessingOtherUserMedia_throwsAccessDenied() {
        when(mediaRepository.findById(testMedia.getId())).thenReturn(Optional.of(testMedia));
        when(userRepository.findByEmail(researcher.getEmail())).thenReturn(Optional.of(researcher));

        assertThatThrownBy(() -> service.getMetadata(testMedia.getId(), researcher.getEmail()))
                .isInstanceOf(AccessDeniedException.class)
                .hasMessageContaining("You do not have permission");
    }

    @Test
    @DisplayName("getMetadata: non-existent media throws MediaNotFoundException")
    void getMetadata_notFound_throwsMediaNotFoundException() {
        UUID unknownId = UUID.randomUUID();
        when(mediaRepository.findById(unknownId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.getMetadata(unknownId, owner.getEmail()))
                .isInstanceOf(MediaNotFoundException.class);
    }

    @Test
    @DisplayName("getAnomalyReport: returns structured forensic report with risk classification")
    void getAnomalyReport_withAnomalies_returnsReport() {
        when(mediaRepository.findById(testMedia.getId())).thenReturn(Optional.of(testMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        MediaMetadata metadata = new MediaMetadata(testMedia);
        metadata.setHasAnomalies(true);
        metadata.setAnomalyCount(2);
        metadata.setForensicScore(0.55);
        metadata.setAnomalyFlags("[{\"ruleId\":\"ANOM_EDITING_SOFTWARE\",\"category\":\"SOFTWARE_MODIFICATION\",\"severity\":\"HIGH\",\"title\":\"Editing Software\",\"description\":\"Photoshop detected\",\"evidence\":\"Adobe Photoshop\",\"confidence\":0.95,\"scoreImpact\":0.35}]");
        metadata.setRawJson("{}");
        when(mediaMetadataRepository.findByMediaId(testMedia.getId())).thenReturn(Optional.of(metadata));

        MetadataAnomalyReportResponse report = service.getAnomalyReport(testMedia.getId(), owner.getEmail());

        assertThat(report.hasAnomalies()).isTrue();
        assertThat(report.anomalyCount()).isEqualTo(2);
        assertThat(report.forensicScore()).isEqualTo(0.55);
        assertThat(report.riskLevel()).isEqualTo("HIGH_RISK");
        assertThat(report.anomalies()).hasSize(1);
        assertThat(report.anomalies().get(0).ruleId()).isEqualTo("ANOM_EDITING_SOFTWARE");
    }

    @Test
    @DisplayName("getRawMetadataJson: returns stored raw JSON tree")
    void getRawMetadataJson_success() {
        when(mediaRepository.findById(testMedia.getId())).thenReturn(Optional.of(testMedia));
        when(userRepository.findByEmail(owner.getEmail())).thenReturn(Optional.of(owner));

        MediaMetadata metadata = new MediaMetadata(testMedia);
        metadata.setRawJson("{\"EXIF IFD0\":{\"Make\":\"Nikon\"}}");
        when(mediaMetadataRepository.findByMediaId(testMedia.getId())).thenReturn(Optional.of(metadata));

        String rawJson = service.getRawMetadataJson(testMedia.getId(), owner.getEmail());

        assertThat(rawJson).isEqualTo("{\"EXIF IFD0\":{\"Make\":\"Nikon\"}}");
    }
}
