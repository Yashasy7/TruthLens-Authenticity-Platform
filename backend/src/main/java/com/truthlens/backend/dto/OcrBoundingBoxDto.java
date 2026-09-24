package com.truthlens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * DTO representing spatial coordinates and polygon corners for an OCR text region.
 */
public class OcrBoundingBoxDto {

    private int x;
    private int y;
    private int width;
    private int height;

    @JsonProperty("normalized_bbox")
    private List<Double> normalizedBbox;

    private List<List<Integer>> polygon;

    public OcrBoundingBoxDto() {
    }

    public OcrBoundingBoxDto(int x, int y, int width, int height, List<Double> normalizedBbox, List<List<Integer>> polygon) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.normalizedBbox = normalizedBbox;
        this.polygon = polygon;
    }

    public int getX() {
        return x;
    }

    public void setX(int x) {
        this.x = x;
    }

    public int getY() {
        return y;
    }

    public void setY(int y) {
        this.y = y;
    }

    public int getWidth() {
        return width;
    }

    public void setWidth(int width) {
        this.width = width;
    }

    public int getHeight() {
        return height;
    }

    public void setHeight(int height) {
        this.height = height;
    }

    public List<Double> getNormalizedBbox() {
        return normalizedBbox;
    }

    public void setNormalizedBbox(List<Double> normalizedBbox) {
        this.normalizedBbox = normalizedBbox;
    }

    public List<List<Integer>> getPolygon() {
        return polygon;
    }

    public void setPolygon(List<List<Integer>> polygon) {
        this.polygon = polygon;
    }
}
