# Database Schema: Module 05 — Image Authenticity Analysis

## Overview
Module 05 introduces the `image_analysis` table via Flyway migration `V5__create_image_analysis_schema.sql`. It stores machine learning probabilities, forensic indicators, and visual artifact references for image authenticity analysis.

---

## Schema Definition

```sql
CREATE TABLE image_analysis (
    id                      UUID             NOT NULL,
    media_id                UUID             NOT NULL,
    ai_prob                 DOUBLE PRECISION NOT NULL,
    manipulation_prob       DOUBLE PRECISION NOT NULL,
    ela_heatmap_url         VARCHAR(500),
    gradcam_heatmap_url     VARCHAR(500),
    noise_variance          DOUBLE PRECISION,
    fft_anomaly_score       DOUBLE PRECISION,
    copy_move_detected      BOOLEAN          NOT NULL DEFAULT FALSE,
    splicing_detected       BOOLEAN          NOT NULL DEFAULT FALSE,
    analysis_status         VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    model_version           VARCHAR(100),
    evidence_json           TEXT,
    created_at              TIMESTAMPTZ      NOT NULL,
    updated_at              TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_image_analysis PRIMARY KEY (id),
    CONSTRAINT uq_image_analysis_media_id UNIQUE (media_id),
    CONSTRAINT fk_image_analysis_media FOREIGN KEY (media_id)
        REFERENCES media(id) ON DELETE CASCADE,
    CONSTRAINT ck_image_analysis_ai_prob
        CHECK (ai_prob >= 0.0 AND ai_prob <= 1.0),
    CONSTRAINT ck_image_analysis_manipulation_prob
        CHECK (manipulation_prob >= 0.0 AND manipulation_prob <= 1.0)
);
```

---

## Indexes

| Index Name | Target Column(s) | Purpose |
| :--- | :--- | :--- |
| `idx_image_analysis_media_id` | `media_id` | Fast 1:1 lookup by parent media item. |
| `idx_image_analysis_ai_prob` | `ai_prob` | Fast sorting and filtering for high-risk synthetic image queries. |
| `idx_image_analysis_manip_prob` | `manipulation_prob` | Fast sorting and filtering for physically manipulated media queries. |
| `idx_image_analysis_status` | `analysis_status` | Filter by lifecycle state (`COMPLETED`, `FAILED`, `PENDING`). |

---

## Integrity & Constraints
1. **Foreign Key Cascade**: Deleting a record from `media` automatically removes the associated `image_analysis` row without orphan retention.
2. **Cardinality**: `uq_image_analysis_media_id` guarantees at most one analysis record per media asset.
3. **Value Bounding**: `ck_image_analysis_ai_prob` and `ck_image_analysis_manipulation_prob` enforce strict probability bounds $[0.0, 1.0]$.
4. **Lifecycle Safety**: Lifecycle states are restricted to valid enum values (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) enforced via the Java `AnalysisStatus` JPA enum mapping (`@Enumerated(EnumType.STRING)`).
