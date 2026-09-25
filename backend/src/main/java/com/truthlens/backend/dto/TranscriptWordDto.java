package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO representing word-level timing offset and alignment confidence (Module 10).
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TranscriptWordDto {

    private String word;
    private double start;
    private double end;
    private double probability;

    public TranscriptWordDto() {
    }

    public TranscriptWordDto(
            @JsonProperty("word") String word,
            @JsonProperty("start") double start,
            @JsonProperty("end") double end,
            @JsonProperty("probability") double probability) {
        this.word = word;
        this.start = start;
        this.end = end;
        this.probability = probability;
    }

    public String getWord() {
        return word;
    }

    public void setWord(String word) {
        this.word = word;
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

    public double getProbability() {
        return probability;
    }

    public void setProbability(double probability) {
        this.probability = probability;
    }
}
