# Database Schema: Module 06 — Video Deepfake & Forensic Analysis

## Overview
Module 06 introduces the `video_analysis` table via Flyway migration `V6__create_video_analysis_schema.sql`. It stores aggregate deepfake manipulation probabilities, face counts, total frames sampled, suspicious timeline markers, and per-frame forensic scores.

---

## Schema Definition

```sql
CREATE TABLE video_analysis (
    id                         UUID             NOT NULL,
    media_id                   UUID             NOT NULL,
    deepfake_prob              DOUBLE PRECISION NOT NULL,
    face_count                 INTEGER          NOT NULL DEFAULT 0,
    total_frames_sampled       INTEGER          NOT NULL DEFAULT 0,
    suspicious_timestamps_json TEXT,
    frame_scores_json          TEXT,
    analysis_status            VARCHAR(30)      NOT NULL DEFAULT 'COMPLETED',
    model_version              VARCHAR(100),
    created_at                 TIMESTAMPTZ      NOT NULL,
    updated_at                 TIMESTAMPTZ      NOT NULL,

    CONSTRAINT pk_video_analysis PRIMARY KEY (id),
    CONSTRAINT uq_video_analysis_media_id UNIQUE (media_id),
    CONSTRAINT fk_video_analysis_media FOREIGN KEY (media_id)
        REFERENCES media (id)
        ON DELETE CASCADE,
    CONSTRAINT ck_video_analysis_deepfake_prob
        CHECK (deepfake_prob >= 0.0 AND deepfake_prob <= 1.0)
);
```

---

## Indexes

| Index Name | Target Column(s) | Purpose |
| :--- | :--- | :--- |
| `idx_video_analysis_media_id` | `media_id` | Fast 1:1 lookup by parent media item. |
| `idx_video_analysis_deepfake_prob` | `deepfake_prob` | Fast sorting and filtering for high-risk deepfake video queries. |
| `idx_video_analysis_status` | `analysis_status` | Filter by lifecycle state (`COMPLETED`, `FAILED`, `PENDING`). |

---

## Integrity & Constraints
1. **Foreign Key Cascade**: Deleting a record from `media` automatically removes the associated `video_analysis` row without orphan retention.
2. **Cardinality**: `uq_video_analysis_media_id` guarantees at most one analysis record per media asset.
3. **Value Bounding**: `ck_video_analysis_deepfake_prob` enforces strict probability bounds $[0.0, 1.0]$.
4. **Lifecycle Safety**: Lifecycle states are restricted to valid enum values (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) enforced via the Java `AnalysisStatus` JPA enum mapping (`@Enumerated(EnumType.STRING)`).
