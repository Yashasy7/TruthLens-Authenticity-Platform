package com.truthlens.backend.service.metadata;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.TimeUnit;

/**
 * CLI wrapper engine executing ExifTool and/or MediaInfo if available on the system PATH.
 *
 * <p>Implements the blueprint specification for "ExifTool and MediaInfo CLI wrapper service".
 * Separates stdout and stderr to prevent diagnostic warning interleaving (FINDING-04-04).
 * If native binaries are not installed, {@link #isAvailable()} safely returns {@code false},
 * allowing seamless delegation to {@link JavaMetadataExtractorEngine} (FINDING-04-03).</p>
 */
@Component
public class CliMetadataExtractorEngine implements MetadataExtractorEngine {

    private static final Logger log = LoggerFactory.getLogger(CliMetadataExtractorEngine.class);
    public static final int MAX_RAW_METADATA_BYTES = 512 * 1024; // 512 KB limit (FINDING-04-05)

    private final ObjectMapper objectMapper;
    private final boolean exiftoolAvailable;
    private final boolean mediainfoAvailable;

    @Autowired
    public CliMetadataExtractorEngine(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
        this.exiftoolAvailable = checkCliAvailability("exiftool", "-ver");
        this.mediainfoAvailable = checkCliAvailability("mediainfo", "--Version");
    }

    // Package-private constructor for testing with simulated CLI availability
    CliMetadataExtractorEngine(ObjectMapper objectMapper, boolean exiftoolAvailable, boolean mediainfoAvailable) {
        this.objectMapper = objectMapper;
        this.exiftoolAvailable = exiftoolAvailable;
        this.mediainfoAvailable = mediainfoAvailable;
    }

    @Override
    public ExtractedMetadata extract(InputStream inputStream, String filename, String mimeType) {
        if (!isAvailable() || inputStream == null) {
            return new ExtractedMetadata();
        }

        ExtractedMetadata result = new ExtractedMetadata();
        result.setExtractionEngine(getEngineName());

        File tempFile = null;
        try {
            tempFile = File.createTempFile("truthlens_cli_", ".tmp");
            try (FileOutputStream fos = new FileOutputStream(tempFile)) {
                inputStream.transferTo(fos);
            }

            // 1. Run ExifTool if available
            if (exiftoolAvailable) {
                runExifTool(tempFile, result, filename);
            }

            // 2. Run MediaInfo if available (especially beneficial for audio/video containers)
            if (mediainfoAvailable) {
                runMediaInfo(tempFile, result, filename);
            }

        } catch (Exception e) {
            log.warn("Error running CLI metadata extraction for '{}': {}", filename, e.getMessage());
        } finally {
            if (tempFile != null && tempFile.exists()) {
                try {
                    tempFile.delete();
                } catch (Exception ignored) {
                }
            }
        }

        return result;
    }

    private void runExifTool(File file, ExtractedMetadata result, String filename) {
        try {
            ProcessBuilder pb = new ProcessBuilder("exiftool", "-j", "-q", "-q", file.getAbsolutePath());
            pb.redirectErrorStream(false); // FINDING-04-04: Do NOT interleave stderr with JSON stdout
            Process process = pb.start();

            // Read stdout (JSON)
            StringBuilder stdout = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    stdout.append(line);
                }
            }

            // Read stderr separately (logging only)
            StringBuilder stderr = new StringBuilder();
            try (BufferedReader errReader = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = errReader.readLine()) != null) {
                    stderr.append(line);
                }
            }

            boolean finished = process.waitFor(10, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                log.warn("ExifTool CLI timed out for file '{}'", filename);
                return;
            }

            if (!stderr.isEmpty()) {
                log.debug("ExifTool stderr for '{}': {}", filename, stderr);
            }

            if (process.exitValue() == 0 && !stdout.isEmpty()) {
                parseExifToolJson(stdout.toString(), result);
            }

        } catch (Exception e) {
            log.warn("ExifTool execution error for '{}': {}", filename, e.getMessage());
        }
    }

    private void runMediaInfo(File file, ExtractedMetadata result, String filename) {
        try {
            ProcessBuilder pb = new ProcessBuilder("mediainfo", "--Output=JSON", file.getAbsolutePath());
            pb.redirectErrorStream(false); // Separate stderr
            Process process = pb.start();

            StringBuilder stdout = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    stdout.append(line);
                }
            }

            StringBuilder stderr = new StringBuilder();
            try (BufferedReader errReader = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = errReader.readLine()) != null) {
                    stderr.append(line);
                }
            }

            boolean finished = process.waitFor(10, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                log.warn("MediaInfo CLI timed out for file '{}'", filename);
                return;
            }

            if (!stderr.isEmpty()) {
                log.debug("MediaInfo stderr for '{}': {}", filename, stderr);
            }

            if (process.exitValue() == 0 && !stdout.isEmpty()) {
                parseMediaInfoJson(stdout.toString(), result);
            }

        } catch (Exception e) {
            log.warn("MediaInfo execution error for '{}': {}", filename, e.getMessage());
        }
    }

    /**
     * Parses ExifTool JSON output into {@link ExtractedMetadata}.
     * Package-private for deterministic unit testing.
     */
    void parseExifToolJson(String json, ExtractedMetadata result) {
        try {
            JsonNode root = objectMapper.readTree(json);
            if (root.isArray() && !root.isEmpty()) {
                JsonNode tags = root.get(0);
                String raw = tags.toString();
                if (raw.getBytes(StandardCharsets.UTF_8).length <= MAX_RAW_METADATA_BYTES) {
                    result.setRawJson(raw);
                } else {
                    result.setRawJson("{\"_warning\":\"ExifTool output exceeded 512KB limit\"}");
                }

                if (tags.has("Make")) {
                    result.setCameraMake(tags.get("Make").asText());
                    result.setExifPresent(true);
                }
                if (tags.has("Model")) {
                    result.setCameraModel(tags.get("Model").asText());
                    result.setExifPresent(true);
                }
                if (tags.has("Software")) {
                    result.setSoftwareTag(tags.get("Software").asText());
                }
                if (tags.has("LensModel")) {
                    result.setLensModel(tags.get("LensModel").asText());
                }
                if (tags.has("ImageWidth")) {
                    result.setWidth(tags.get("ImageWidth").asInt());
                }
                if (tags.has("ImageHeight")) {
                    result.setHeight(tags.get("ImageHeight").asInt());
                }
                if (tags.has("GPSLatitude")) {
                    result.setGpsLatitude(tags.get("GPSLatitude").asDouble());
                    result.setExifPresent(true);
                }
                if (tags.has("GPSLongitude")) {
                    result.setGpsLongitude(tags.get("GPSLongitude").asDouble());
                    result.setExifPresent(true);
                }
            }
        } catch (Exception e) {
            log.warn("Failed to parse ExifTool JSON: {}", e.getMessage());
        }
    }

    /**
     * Parses MediaInfo JSON output into {@link ExtractedMetadata}.
     * Package-private for deterministic unit testing.
     */
    void parseMediaInfoJson(String json, ExtractedMetadata result) {
        try {
            JsonNode root = objectMapper.readTree(json);
            JsonNode mediaNode = root.path("media");
            JsonNode trackNode = mediaNode.path("track");

            if (trackNode.isArray()) {
                for (JsonNode track : trackNode) {
                    String type = track.path("@type").asText("");

                    if ("General".equalsIgnoreCase(type)) {
                        if (result.getContainerFormat() == null && track.has("Format")) {
                            result.setContainerFormat(track.get("Format").asText());
                        }
                        if (result.getDurationSeconds() == null && track.has("Duration")) {
                            try {
                                result.setDurationSeconds(Double.parseDouble(track.get("Duration").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                        if (result.getBitrate() == null && track.has("OverallBitRate")) {
                            try {
                                result.setBitrate(Long.parseLong(track.get("OverallBitRate").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                    } else if ("Video".equalsIgnoreCase(type)) {
                        if (result.getVideoCodec() == null && track.has("Format")) {
                            result.setVideoCodec(track.get("Format").asText());
                        }
                        if (result.getWidth() == null && track.has("Width")) {
                            try {
                                result.setWidth(Integer.parseInt(track.get("Width").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                        if (result.getHeight() == null && track.has("Height")) {
                            try {
                                result.setHeight(Integer.parseInt(track.get("Height").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                        if (result.getFrameRate() == null && track.has("FrameRate")) {
                            try {
                                result.setFrameRate(Double.parseDouble(track.get("FrameRate").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                    } else if ("Audio".equalsIgnoreCase(type)) {
                        if (result.getAudioCodec() == null && track.has("Format")) {
                            result.setAudioCodec(track.get("Format").asText());
                        }
                        if (result.getAudioSampleRate() == null && track.has("SamplingRate")) {
                            try {
                                result.setAudioSampleRate(Integer.parseInt(track.get("SamplingRate").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                        if (result.getAudioChannels() == null && track.has("Channels")) {
                            try {
                                result.setAudioChannels(Integer.parseInt(track.get("Channels").asText()));
                            } catch (Exception ignored) {
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Failed to parse MediaInfo JSON: {}", e.getMessage());
        }
    }

    @Override
    public boolean isAvailable() {
        return exiftoolAvailable || mediainfoAvailable;
    }

    @Override
    public String getEngineName() {
        if (exiftoolAvailable && mediainfoAvailable) {
            return "EXIFTOOL_MEDIAINFO_CLI";
        } else if (exiftoolAvailable) {
            return "EXIFTOOL_CLI";
        } else if (mediainfoAvailable) {
            return "MEDIAINFO_CLI";
        } else {
            return "NONE";
        }
    }

    private boolean checkCliAvailability(String command, String testArg) {
        try {
            Process process = new ProcessBuilder(command, testArg).start();
            boolean finished = process.waitFor(2, TimeUnit.SECONDS);
            if (finished && process.exitValue() == 0) {
                log.info("CLI tool '{}' detected on system PATH; integration enabled.", command);
                return true;
            }
        } catch (Exception ignored) {
        }
        log.info("CLI tool '{}' not found on system PATH; will delegate to built-in pure-Java extraction.", command);
        return false;
    }
}
