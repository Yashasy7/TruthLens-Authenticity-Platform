package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.List;

/**
 * DTO representing timestamped phrase segment with acoustic metrics and word offsets (Module 10).
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TranscriptSegmentDto {

    private int id;
    private int seek;
    private double start;
    private double end;
    private String text;
    private List<Integer> tokens = new ArrayList<>();
    private double temperature;

    @JsonProperty("avg_logprob")
    private double avgLogprob;

    @JsonProperty("compression_ratio")
    private double compressionRatio;

    @JsonProperty("no_speech_prob")
    private double noSpeechProb;

    private double confidence;
    private List<TranscriptWordDto> words = new ArrayList<>();

    public TranscriptSegmentDto() {
    }

    public TranscriptSegmentDto(
            @JsonProperty("id") int id,
            @JsonProperty("seek") int seek,
            @JsonProperty("start") double start,
            @JsonProperty("end") double end,
            @JsonProperty("text") String text,
            @JsonProperty("tokens") List<Integer> tokens,
            @JsonProperty("temperature") double temperature,
            @JsonProperty("avg_logprob") double avgLogprob,
            @JsonProperty("compression_ratio") double compressionRatio,
            @JsonProperty("no_speech_prob") double noSpeechProb,
            @JsonProperty("confidence") double confidence,
            @JsonProperty("words") List<TranscriptWordDto> words) {
        this.id = id;
        this.seek = seek;
        this.start = start;
        this.end = end;
        this.text = text;
        this.tokens = tokens != null ? tokens : new ArrayList<>();
        this.temperature = temperature;
        this.avgLogprob = avgLogprob;
        this.compressionRatio = compressionRatio;
        this.noSpeechProb = noSpeechProb;
        this.confidence = confidence;
        this.words = words != null ? words : new ArrayList<>();
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public int getSeek() {
        return seek;
    }

    public void setSeek(int seek) {
        this.seek = seek;
    }

    public double getStart() {
        return start;
    }

    public void setStart(double start) {
        this.start = start;
    }

    public double getEnd() {
        return end;
    }

    public void setEnd(double end) {
        this.end = end;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public List<Integer> getTokens() {
        return tokens;
    }

    public void setTokens(List<Integer> tokens) {
        this.tokens = tokens;
    }

    public double getTemperature() {
        return temperature;
    }

    public void setTemperature(double temperature) {
        this.temperature = temperature;
    }

    public double getAvgLogprob() {
        return avgLogprob;
    }

    public void setAvgLogprob(double avgLogprob) {
        this.avgLogprob = avgLogprob;
    }

    public double getCompressionRatio() {
        return compressionRatio;
    }

    public void setCompressionRatio(double compressionRatio) {
        this.compressionRatio = compressionRatio;
    }

    public double getNoSpeechProb() {
        return noSpeechProb;
    }

    public void setNoSpeechProb(double noSpeechProb) {
        this.noSpeechProb = noSpeechProb;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public List<TranscriptWordDto> getWords() {
        return words;
    }

    public void setWords(List<TranscriptWordDto> words) {
        this.words = words;
    }
}
