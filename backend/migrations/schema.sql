-- Mifugo AI database schema
-- Applied once via: psql mifugo -f migrations/schema.sql
--
-- Design notes:
--   * Prices are NEVER deleted, only flagged. Officials need to be able to
--     audit why a price was excluded from averages (outlier_status +
--     outlier_reason), not just trust a black box.
--   * region and species are lookup tables rather than free text, so that
--     "Lodwar" and "lodwar" typed by different agents don't fragment the data.
--   * Every write is attributable to an agent for accountability.

CREATE TABLE IF NOT EXISTS regions (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    -- sub_county lets us group markets (e.g. Lodwar, Kakuma, Lokichogio) later
    sub_county  VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS species (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE  -- goat, camel, cattle, sheep
);

CREATE TABLE IF NOT EXISTS agents (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(150) NOT NULL,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'agent', -- agent | official | admin
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS price_entries (
    id                  SERIAL PRIMARY KEY,
    region_id           INTEGER NOT NULL REFERENCES regions(id),
    species_id          INTEGER NOT NULL REFERENCES species(id),
    agent_id            INTEGER NOT NULL REFERENCES agents(id),

    -- Price is stored in Kenyan Shillings (KES) as an integer to avoid
    -- floating point ambiguity in currency math.
    price_kes           INTEGER NOT NULL CHECK (price_kes > 0),

    -- The date the price was actually observed at market (may differ from
    -- when it was entered into the system, since agents may enter data
    -- for multiple days at once after returning from the field).
    market_date          DATE NOT NULL,
    entered_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Free-text notes from the agent (e.g. animal age/condition context)
    notes                 TEXT,

    -- Outlier detection results — never delete rows, just annotate them.
    -- status: 'valid' | 'flagged' | 'rejected'
    outlier_status         VARCHAR(20) NOT NULL DEFAULT 'valid',
    outlier_reason          TEXT,
    outlier_score            NUMERIC,

    CONSTRAINT valid_outlier_status CHECK (outlier_status IN ('valid', 'flagged', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_price_entries_region_species_date
    ON price_entries (region_id, species_id, market_date);

CREATE INDEX IF NOT EXISTS idx_price_entries_status
    ON price_entries (outlier_status);

-- Seed the four livestock types this system is scoped to.
INSERT INTO species (name) VALUES
    ('goat'), ('camel'), ('cattle'), ('sheep')
ON CONFLICT (name) DO NOTHING;

-- Seed a starter set of known Turkana markets. Agents/admins can add more
-- via the app; this is just a reasonable starting point.
INSERT INTO regions (name, sub_county) VALUES
    ('Lodwar', 'Turkana Central'),
    ('Kakuma', 'Turkana West'),
    ('Lokichogio', 'Turkana West'),
    ('Lokitaung', 'Turkana North'),
    ('Kalokol', 'Turkana Central'),
    ('Lokichar', 'Turkana South')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- Milestone 4: Climate & Disease Alerts
-- ============================================================

-- Climate data is sync-when-online, use-offline: this table holds whatever
-- was last logged (either an agent's field observation, or a bulletin
-- pasted in from NDMA/Kenya Met during a connectivity window). The
-- dashboard and AI always read the latest row per region, never fetch
-- live over the network.
--
-- drought_status follows Kenya's NDMA drought early-warning phase
-- classification (Normal / Alert / Alarm / Emergency), so it maps onto
-- terminology partners (county government, NDMA) already recognize.
CREATE TABLE IF NOT EXISTS climate_bulletins (
    id              SERIAL PRIMARY KEY,
    region_id       INTEGER NOT NULL REFERENCES regions(id),
    agent_id        INTEGER NOT NULL REFERENCES agents(id),

    bulletin_date   DATE NOT NULL,
    drought_status  VARCHAR(20) NOT NULL DEFAULT 'normal',
    rainfall_mm     NUMERIC,
    temperature_c   NUMERIC,

    -- Where this came from — a field agent's own observation, or a named
    -- external source (e.g. "NDMA Turkana Bulletin, June 2026"). Kept as
    -- free text rather than an enum since sources will vary and grow.
    source          VARCHAR(200) NOT NULL DEFAULT 'Field observation',
    notes           TEXT,

    entered_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT valid_drought_status CHECK (
        drought_status IN ('normal', 'alert', 'alarm', 'emergency')
    )
);

CREATE INDEX IF NOT EXISTS idx_climate_bulletins_region_date
    ON climate_bulletins (region_id, bulletin_date DESC);

-- Disease reports follow the SAME never-delete, always-reviewable pattern
-- as price_entries — a wrongly-suppressed real outbreak is far more
-- dangerous than a false alarm sitting flagged for review, so nothing
-- here is ever silently discarded.
CREATE TABLE IF NOT EXISTS disease_reports (
    id                  SERIAL PRIMARY KEY,
    region_id           INTEGER NOT NULL REFERENCES regions(id),
    species_id          INTEGER NOT NULL REFERENCES species(id),
    agent_id            INTEGER NOT NULL REFERENCES agents(id),

    report_date         DATE NOT NULL,
    disease_name        VARCHAR(150) NOT NULL,  -- suspected name, or "Unknown — see symptoms"
    symptoms            TEXT,
    affected_count       INTEGER CHECK (affected_count IS NULL OR affected_count >= 0),
    severity              VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- review_status: 'reported' (just logged, unreviewed) ->
    -- 'confirmed' (an official verified it's real) or
    -- 'false_alarm' (reviewed and dismissed) — never deleted either way.
    review_status         VARCHAR(20) NOT NULL DEFAULT 'reported',
    review_notes           TEXT,

    entered_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT valid_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT valid_review_status CHECK (
        review_status IN ('reported', 'confirmed', 'false_alarm')
    )
);

CREATE INDEX IF NOT EXISTS idx_disease_reports_region_date
    ON disease_reports (region_id, report_date DESC);

CREATE INDEX IF NOT EXISTS idx_disease_reports_status
    ON disease_reports (review_status);
