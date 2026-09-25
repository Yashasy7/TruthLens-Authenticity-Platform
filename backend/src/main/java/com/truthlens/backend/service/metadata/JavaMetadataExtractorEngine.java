package com.truthlens.backend.service.metadata;

import com.drew.imaging.ImageMetadataReader;
import com.drew.imaging.ImageProcessingException;
import com.drew.lang.GeoLocation;
import com.drew.metadata.Directory;
import com.drew.metadata.Metadata;
import com.drew.metadata.Tag;
import com.drew.metadata.avi.AviDirectory;
import com.drew.metadata.exif.ExifIFD0Directory;
import com.drew.metadata.exif.ExifSubIFDDirectory;
import com.drew.metadata.exif.GpsDirectory;
import com.drew.metadata.mov.QuickTimeDirectory;
import com.drew.metadata.mov.media.QuickTimeSoundDirectory;
import com.drew.metadata.mov.media.QuickTimeVideoDirectory;
import com.drew.metadata.mp3.Mp3Directory;
import com.drew.metadata.mp4.Mp4Directory;
import com.drew.metadata.mp4.media.Mp4SoundDirectory;
import com.drew.metadata.mp4.media.Mp4VideoDirectory;
import com.drew.metadata.wav.WavDirectory;
import com.drew.metadata.xmp.XmpDirectory;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Pure-Java metadata extraction engine based on Drew Noakes' metadata-extractor.
 *
 * <p>Extracts EXIF, IPTC, XMP, GPS, QuickTime/MP4 container structures, standalone audio
 * parameters (WAV / MP3), and camera hardware profiles without requiring external native binaries.
 * Bounded by {@link #MAX_RAW_METADATA_BYTES} to prevent memory exhaustion (FINDING-04-05).</p>
 */
@Component
public class JavaMetadataExtractorEngine implements MetadataExtractorEngine {

    private static final Logger log = LoggerFactory.getLogger(JavaMetadataExtractorEngine.class);
    private static final String ENGINE_NAME = "JAVA_METADATA_EXTRACTOR";

    /**
     * Maximum serialized size for raw JSON metadata (512 KB) to prevent memory exhaustion (FINDING-04-05).
     */
    public static final int MAX_RAW_METADATA_BYTES = 512 * 1024;

    private final ObjectMapper objectMapper;

    public JavaMetadataExtractorEngine(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public ExtractedMetadata extract(InputStream inputStream, String filename, String mimeType) {
        ExtractedMetadata result = new ExtractedMetadata();
        result.setExtractionEngine(ENGINE_NAME);

        if (inputStream == null) {
            return result;
        }

        try (BufferedInputStream bis = new BufferedInputStream(inputStream)) {
            Metadata metadata = ImageMetadataReader.readMetadata(bis);

            // 1. Traverse all directories and tags to build hierarchical raw tree
            for (Directory directory : metadata.getDirectories()) {
                String dirName = directory.getName();
                for (Tag tag : directory.getTags()) {
                    result.addDirectoryTag(dirName, tag.getTagName(), tag.getDescription());
                }
            }

            // 2. Extract EXIF IFD0 (Make, Model, Software, Timestamps)
            ExifIFD0Directory ifd0 = metadata.getFirstDirectoryOfType(ExifIFD0Directory.class);
            if (ifd0 != null) {
                result.setExifPresent(true);
                if (ifd0.containsTag(ExifIFD0Directory.TAG_MAKE)) {
                    result.setCameraMake(cleanString(ifd0.getString(ExifIFD0Directory.TAG_MAKE)));
                }
                if (ifd0.containsTag(ExifIFD0Directory.TAG_MODEL)) {
                    result.setCameraModel(cleanString(ifd0.getString(ExifIFD0Directory.TAG_MODEL)));
                }
                if (ifd0.containsTag(ExifIFD0Directory.TAG_SOFTWARE)) {
                    result.setSoftwareTag(cleanString(ifd0.getString(ExifIFD0Directory.TAG_SOFTWARE)));
                }
                if (ifd0.containsTag(ExifIFD0Directory.TAG_DATETIME)) {
                    Date dt = ifd0.getDate(ExifIFD0Directory.TAG_DATETIME);
                    if (dt != null) {
                        result.setModifiedAt(dt.toInstant().atOffset(ZoneOffset.UTC));
                    }
                }
                if (ifd0.containsTag(ExifIFD0Directory.TAG_IMAGE_WIDTH)) {
                    result.setWidth(ifd0.getInteger(ExifIFD0Directory.TAG_IMAGE_WIDTH));
                }
                if (ifd0.containsTag(ExifIFD0Directory.TAG_IMAGE_HEIGHT)) {
                    result.setHeight(ifd0.getInteger(ExifIFD0Directory.TAG_IMAGE_HEIGHT));
                }
            }

            // 3. Extract EXIF SubIFD (Lens, Capture Timestamps, Image Dimensions)
            ExifSubIFDDirectory subIfd = metadata.getFirstDirectoryOfType(ExifSubIFDDirectory.class);
            if (subIfd != null) {
                result.setExifPresent(true);
                if (subIfd.containsTag(ExifSubIFDDirectory.TAG_LENS_MODEL)) {
                    result.setLensModel(cleanString(subIfd.getString(ExifSubIFDDirectory.TAG_LENS_MODEL)));
                }
                Date origDate = subIfd.getDateOriginal();
                if (origDate != null) {
                    result.setCapturedAt(origDate.toInstant().atOffset(ZoneOffset.UTC));
                }
                if (result.getWidth() == null && subIfd.containsTag(ExifSubIFDDirectory.TAG_EXIF_IMAGE_WIDTH)) {
                    result.setWidth(subIfd.getInteger(ExifSubIFDDirectory.TAG_EXIF_IMAGE_WIDTH));
                }
                if (result.getHeight() == null && subIfd.containsTag(ExifSubIFDDirectory.TAG_EXIF_IMAGE_HEIGHT)) {
                    result.setHeight(subIfd.getInteger(ExifSubIFDDirectory.TAG_EXIF_IMAGE_HEIGHT));
                }
            }

            // 3b. Extract fallback visual dimensions from image format directories (JPEG, PNG, WebP)
            com.drew.metadata.jpeg.JpegDirectory jpegDir = metadata.getFirstDirectoryOfType(com.drew.metadata.jpeg.JpegDirectory.class);
            if (jpegDir != null) {
                if (result.getWidth() == null && jpegDir.containsTag(com.drew.metadata.jpeg.JpegDirectory.TAG_IMAGE_WIDTH)) {
                    result.setWidth(jpegDir.getInteger(com.drew.metadata.jpeg.JpegDirectory.TAG_IMAGE_WIDTH));
                }
                if (result.getHeight() == null && jpegDir.containsTag(com.drew.metadata.jpeg.JpegDirectory.TAG_IMAGE_HEIGHT)) {
                    result.setHeight(jpegDir.getInteger(com.drew.metadata.jpeg.JpegDirectory.TAG_IMAGE_HEIGHT));
                }
            }

            com.drew.metadata.png.PngDirectory pngDir = metadata.getFirstDirectoryOfType(com.drew.metadata.png.PngDirectory.class);
            if (pngDir != null) {
                if (result.getWidth() == null && pngDir.containsTag(com.drew.metadata.png.PngDirectory.TAG_IMAGE_WIDTH)) {
                    result.setWidth(pngDir.getInteger(com.drew.metadata.png.PngDirectory.TAG_IMAGE_WIDTH));
                }
                if (result.getHeight() == null && pngDir.containsTag(com.drew.metadata.png.PngDirectory.TAG_IMAGE_HEIGHT)) {
                    result.setHeight(pngDir.getInteger(com.drew.metadata.png.PngDirectory.TAG_IMAGE_HEIGHT));
                }
            }

            com.drew.metadata.webp.WebpDirectory webpDir = metadata.getFirstDirectoryOfType(com.drew.metadata.webp.WebpDirectory.class);
            if (webpDir != null) {
                if (result.getWidth() == null && webpDir.containsTag(com.drew.metadata.webp.WebpDirectory.TAG_IMAGE_WIDTH)) {
                    result.setWidth(webpDir.getInteger(com.drew.metadata.webp.WebpDirectory.TAG_IMAGE_WIDTH));
                }
                if (result.getHeight() == null && webpDir.containsTag(com.drew.metadata.webp.WebpDirectory.TAG_IMAGE_HEIGHT)) {
                    result.setHeight(webpDir.getInteger(com.drew.metadata.webp.WebpDirectory.TAG_IMAGE_HEIGHT));
                }
            }

            // 4. Extract GPS Coordinates
            GpsDirectory gpsDir = metadata.getFirstDirectoryOfType(GpsDirectory.class);
            if (gpsDir != null) {
                result.setExifPresent(true);
                GeoLocation geoLocation = gpsDir.getGeoLocation();
                if (geoLocation != null && !geoLocation.isZero()) {
                    result.setGpsLatitude(geoLocation.getLatitude());
                    result.setGpsLongitude(geoLocation.getLongitude());
                }
                if (gpsDir.containsTag(GpsDirectory.TAG_ALTITUDE)) {
                    try {
                        result.setGpsAltitude(gpsDir.getDoubleObject(GpsDirectory.TAG_ALTITUDE));
                    } catch (Exception ignored) {
                    }
                }
            }

            // 5. Extract XMP metadata (CreatorTool, History, Software fallback)
            XmpDirectory xmpDir = metadata.getFirstDirectoryOfType(XmpDirectory.class);
            if (xmpDir != null && result.getSoftwareTag() == null) {
                if (xmpDir.getXmpProperties().containsKey("xmp:CreatorTool")) {
                    result.setSoftwareTag(cleanString(xmpDir.getXmpProperties().get("xmp:CreatorTool")));
                } else if (xmpDir.getXmpProperties().containsKey("tiff:Software")) {
                    result.setSoftwareTag(cleanString(xmpDir.getXmpProperties().get("tiff:Software")));
                }
            }

            // 6. Extract MP4 Container Properties
            Mp4Directory mp4Dir = metadata.getFirstDirectoryOfType(Mp4Directory.class);
            if (mp4Dir != null) {
                result.setContainerFormat("MP4");
                Date creation = mp4Dir.getDate(Mp4Directory.TAG_CREATION_TIME);
                if (creation != null && result.getCapturedAt() == null) {
                    result.setCapturedAt(creation.toInstant().atOffset(ZoneOffset.UTC));
                }
                Date mod = mp4Dir.getDate(Mp4Directory.TAG_MODIFICATION_TIME);
                if (mod != null && result.getModifiedAt() == null) {
                    result.setModifiedAt(mod.toInstant().atOffset(ZoneOffset.UTC));
                }
                if (mp4Dir.containsTag(Mp4Directory.TAG_DURATION_SECONDS)) {
                    try {
                        result.setDurationSeconds(mp4Dir.getDoubleObject(Mp4Directory.TAG_DURATION_SECONDS));
                    } catch (Exception ignored) {
                    }
                }
            }

            Mp4VideoDirectory mp4Video = metadata.getFirstDirectoryOfType(Mp4VideoDirectory.class);
            if (mp4Video != null) {
                if (mp4Video.containsTag(Mp4VideoDirectory.TAG_WIDTH)) {
                    result.setWidth(mp4Video.getInteger(Mp4VideoDirectory.TAG_WIDTH));
                }
                if (mp4Video.containsTag(Mp4VideoDirectory.TAG_HEIGHT)) {
                    result.setHeight(mp4Video.getInteger(Mp4VideoDirectory.TAG_HEIGHT));
                }
                if (mp4Video.containsTag(Mp4VideoDirectory.TAG_FRAME_RATE)) {
                    try {
                        result.setFrameRate(mp4Video.getDoubleObject(Mp4VideoDirectory.TAG_FRAME_RATE));
                    } catch (Exception ignored) {
                    }
                }
                if (mp4Video.containsTag(Mp4VideoDirectory.TAG_COMPRESSION_TYPE)) {
                    result.setVideoCodec(cleanString(mp4Video.getString(Mp4VideoDirectory.TAG_COMPRESSION_TYPE)));
                }
            }

            Mp4SoundDirectory mp4Sound = metadata.getFirstDirectoryOfType(Mp4SoundDirectory.class);
            if (mp4Sound != null) {
                if (mp4Sound.containsTag(Mp4SoundDirectory.TAG_AUDIO_SAMPLE_RATE)) {
                    result.setAudioSampleRate(mp4Sound.getInteger(Mp4SoundDirectory.TAG_AUDIO_SAMPLE_RATE));
                }
                if (mp4Sound.containsTag(Mp4SoundDirectory.TAG_NUMBER_OF_CHANNELS)) {
                    result.setAudioChannels(mp4Sound.getInteger(Mp4SoundDirectory.TAG_NUMBER_OF_CHANNELS));
                }
                if (mp4Sound.containsTag(Mp4SoundDirectory.TAG_AUDIO_FORMAT)) {
                    result.setAudioCodec(cleanString(mp4Sound.getString(Mp4SoundDirectory.TAG_AUDIO_FORMAT)));
                }
            }

            // 7. Extract QuickTime Container Properties
            QuickTimeDirectory qtDir = metadata.getFirstDirectoryOfType(QuickTimeDirectory.class);
            if (qtDir != null && result.getContainerFormat() == null) {
                result.setContainerFormat("QuickTime");
                if (qtDir.containsTag(QuickTimeDirectory.TAG_DURATION_SECONDS)) {
                    try {
                        result.setDurationSeconds(qtDir.getDoubleObject(QuickTimeDirectory.TAG_DURATION_SECONDS));
                    } catch (Exception ignored) {
                    }
                }
            }

            QuickTimeVideoDirectory qtVideo = metadata.getFirstDirectoryOfType(QuickTimeVideoDirectory.class);
            if (qtVideo != null && result.getWidth() == null) {
                if (qtVideo.containsTag(QuickTimeVideoDirectory.TAG_WIDTH)) {
                    result.setWidth(qtVideo.getInteger(QuickTimeVideoDirectory.TAG_WIDTH));
                }
                if (qtVideo.containsTag(QuickTimeVideoDirectory.TAG_HEIGHT)) {
                    result.setHeight(qtVideo.getInteger(QuickTimeVideoDirectory.TAG_HEIGHT));
                }
            }

            QuickTimeSoundDirectory qtSound = metadata.getFirstDirectoryOfType(QuickTimeSoundDirectory.class);
            if (qtSound != null && result.getAudioSampleRate() == null) {
                if (qtSound.containsTag(QuickTimeSoundDirectory.TAG_AUDIO_SAMPLE_RATE)) {
                    result.setAudioSampleRate(qtSound.getInteger(QuickTimeSoundDirectory.TAG_AUDIO_SAMPLE_RATE));
                }
                if (qtSound.containsTag(QuickTimeSoundDirectory.TAG_NUMBER_OF_CHANNELS)) {
                    result.setAudioChannels(qtSound.getInteger(QuickTimeSoundDirectory.TAG_NUMBER_OF_CHANNELS));
                }
            }

            // 8. Extract Standalone Audio Metadata — WAV (FINDING-04-02)
            WavDirectory wavDir = metadata.getFirstDirectoryOfType(WavDirectory.class);
            if (wavDir != null) {
                if (result.getContainerFormat() == null) {
                    result.setContainerFormat("WAV");
                }
                if (result.getAudioCodec() == null) {
                    result.setAudioCodec("PCM");
                }
                if (result.getAudioSampleRate() == null && wavDir.containsTag(WavDirectory.TAG_SAMPLES_PER_SEC)) {
                    result.setAudioSampleRate(wavDir.getInteger(WavDirectory.TAG_SAMPLES_PER_SEC));
                }
                if (result.getAudioChannels() == null && wavDir.containsTag(WavDirectory.TAG_CHANNELS)) {
                    result.setAudioChannels(wavDir.getInteger(WavDirectory.TAG_CHANNELS));
                }
                if (result.getBitrate() == null && wavDir.containsTag(WavDirectory.TAG_BYTES_PER_SEC)) {
                    try {
                        long bytesPerSec = wavDir.getLong(WavDirectory.TAG_BYTES_PER_SEC);
                        result.setBitrate(bytesPerSec * 8L);
                    } catch (Exception ignored) {
                    }
                }
                if (result.getDurationSeconds() == null && wavDir.containsTag(WavDirectory.TAG_DURATION)) {
                    try {
                        result.setDurationSeconds(wavDir.getDoubleObject(WavDirectory.TAG_DURATION));
                    } catch (Exception ignored) {
                    }
                }
                if (result.getSoftwareTag() == null && wavDir.containsTag(WavDirectory.TAG_SOFTWARE)) {
                    result.setSoftwareTag(cleanString(wavDir.getString(WavDirectory.TAG_SOFTWARE)));
                }
            }

            // 9. Extract Standalone Audio Metadata — MP3 (FINDING-04-02)
            Mp3Directory mp3Dir = metadata.getFirstDirectoryOfType(Mp3Directory.class);
            if (mp3Dir != null) {
                if (result.getContainerFormat() == null) {
                    result.setContainerFormat("MP3");
                }
                if (result.getAudioCodec() == null) {
                    result.setAudioCodec("MPEG-1/2 Audio Layer 3");
                }
                if (result.getAudioSampleRate() == null && mp3Dir.containsTag(Mp3Directory.TAG_FREQUENCY)) {
                    result.setAudioSampleRate(mp3Dir.getInteger(Mp3Directory.TAG_FREQUENCY));
                }
                if (result.getAudioChannels() == null && mp3Dir.containsTag(Mp3Directory.TAG_MODE)) {
                    String mode = mp3Dir.getString(Mp3Directory.TAG_MODE);
                    if (mode != null) {
                        if (mode.equalsIgnoreCase("Mono") || mode.equalsIgnoreCase("Single Channel")) {
                            result.setAudioChannels(1);
                        } else {
                            result.setAudioChannels(2);
                        }
                    }
                }
                if (result.getBitrate() == null && mp3Dir.containsTag(Mp3Directory.TAG_BITRATE)) {
                    try {
                        int kbps = mp3Dir.getInteger(Mp3Directory.TAG_BITRATE);
                        result.setBitrate((long) kbps * 1000L);
                    } catch (Exception ignored) {
                    }
                }
            }

            // 10. Extract AVI Container Metadata
            AviDirectory aviDir = metadata.getFirstDirectoryOfType(AviDirectory.class);
            if (aviDir != null && result.getContainerFormat() == null) {
                result.setContainerFormat("AVI");
                if (result.getWidth() == null && aviDir.containsTag(AviDirectory.TAG_WIDTH)) {
                    result.setWidth(aviDir.getInteger(AviDirectory.TAG_WIDTH));
                }
                if (result.getHeight() == null && aviDir.containsTag(AviDirectory.TAG_HEIGHT)) {
                    result.setHeight(aviDir.getInteger(AviDirectory.TAG_HEIGHT));
                }
            }

            // 11. Bounded JSON Serialization to prevent memory exhaustion (FINDING-04-05)
            String jsonTree = serializeBoundedRawJson(result.getRawMetadataTree());
            result.setRawJson(jsonTree);

        } catch (ImageProcessingException e) {
            log.debug("ImageProcessingException reading metadata for file '{}': {}", filename, e.getMessage());
            result.setRawJson("{}");
        } catch (IOException e) {
            log.warn("IOException reading metadata stream for file '{}': {}", filename, e.getMessage());
            result.setRawJson("{}");
        } catch (Exception e) {
            log.warn("Unexpected error extracting metadata for file '{}': {}", filename, e.getMessage());
            result.setRawJson("{}");
        }

        return result;
    }

    /**
     * Serializes raw metadata tree safely within {@link #MAX_RAW_METADATA_BYTES}.
     * If the payload exceeds the limit, prunes entries while maintaining valid JSON (FINDING-04-05).
     */
    String serializeBoundedRawJson(Map<String, Map<String, String>> rawTree) {
        if (rawTree == null || rawTree.isEmpty()) {
            return "{}";
        }
        try {
            String fullJson = objectMapper.writeValueAsString(rawTree);
            if (fullJson.getBytes(StandardCharsets.UTF_8).length <= MAX_RAW_METADATA_BYTES) {
                return fullJson;
            }

            // Construct valid pruned JSON object
            Map<String, Object> pruned = new LinkedHashMap<>();
            pruned.put("_metadata_status", "TRUNCATED");
            pruned.put("_max_bytes", MAX_RAW_METADATA_BYTES);
            pruned.put("_warning", "Raw metadata exceeded maximum allowed payload size of 512 KB and was safely bounded.");

            Map<String, Map<String, String>> boundedTree = new LinkedHashMap<>();
            for (Map.Entry<String, Map<String, String>> entry : rawTree.entrySet()) {
                Map<String, String> dirTags = new LinkedHashMap<>();
                for (Map.Entry<String, String> tagEntry : entry.getValue().entrySet()) {
                    String val = tagEntry.getValue();
                    if (val != null && val.length() > 150) {
                        val = val.substring(0, 150) + "... [truncated]";
                    }
                    dirTags.put(tagEntry.getKey(), val);
                }
                boundedTree.put(entry.getKey(), dirTags);

                String currentCheck = objectMapper.writeValueAsString(boundedTree);
                if (currentCheck.getBytes(StandardCharsets.UTF_8).length > (MAX_RAW_METADATA_BYTES - 2048)) {
                    break;
                }
            }
            pruned.put("directories", boundedTree);
            return objectMapper.writeValueAsString(pruned);

        } catch (Exception e) {
            log.warn("Failed to serialize raw metadata JSON: {}", e.getMessage());
            return "{}";
        }
    }

    @Override
    public boolean isAvailable() {
        return true;
    }

    @Override
    public String getEngineName() {
        return ENGINE_NAME;
    }

    private String cleanString(String input) {
        if (input == null) {
            return null;
        }
        String trimmed = input.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
