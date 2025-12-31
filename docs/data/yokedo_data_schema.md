# Yokedo – PostrgreSQL Data Schema v1.1 (MCP-ready)
**Latest update:** 2025-12-31 12:26 UTC

---

## 🚀 Step 1: PostgreSQL Extensions (CRITICAL)

```sql
-- For gen_random_uuid() in primary keys
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- For vectors (ML embeddings)
CREATE EXTENSION IF NOT EXISTS vector;
-- For case-insensitive fields
CREATE EXTENSION IF NOT EXISTS citext;
```
---

## 🚀 STEP 2: Table Creation (Mandatory Order)

1. **users**  
2. **user_sessions**  
3. **interests**  
4. **user_interests**  
5. **plan_category**  
6. **availability_weekly_templates** ⬅️ **[NEW]**  
7. **availability_day_overrides** ⬅️ **[NEW]**  
8. **availabilities**  
9. **plan_proposals**  
10. **contacts**  
11. **invitation_links**  
12. **invitation_acceptances**  
13. **notifications**  
14. **user_interaction_logs**  
15. **user_notification_settings**  
16. **contact_requests**  
17. **plan_categories_map**  
18. **semantic_similarity_log**  
19. **user_affinities**  
20. **mcp_context_snapshots** (documented; reserved)

> All DDL statements include data types, `CHECK` constraints, foreign keys (`FK`), indexes, and comments.  
> Fields marked with `-- [NEW]` are **additive** and backward-safe extensions.

---

### 1. Table `users`

```sql
CREATE TABLE users (
  id              UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  email           CITEXT    NOT NULL UNIQUE,
  password_hash   VARCHAR   NOT NULL,
  first_name      VARCHAR   NOT NULL,
  last_name       VARCHAR   NOT NULL,
  alias           CITEXT    NULL,

  age             INTEGER   NULL,
  age_range       VARCHAR   NULL
                    CHECK (age_range IN (
                      'under_18','18_25','26_35','36_45','46_55','56_65','over_65'
                    )),
  gender          VARCHAR   NULL
                    CHECK (gender IN (
                      'female','male','non_binary','other','prefer_not_to_say'
                    )),
  custom_gender   VARCHAR   NULL,

  city            VARCHAR   NULL,
  province        VARCHAR   NULL,
  country         VARCHAR   NULL,
  timezone        VARCHAR   NOT NULL,

-- User preferred language (i18n), e.g. 'es', 'en', 'es-ES'
  language        VARCHAR(5) NULL
                    CHECK (language ~ '^[a-z]{2}(-[A-Z]{2})?$'),

  frequency_social VARCHAR  NULL
                    CHECK (frequency_social IN (
                      'daily','weekly','monthly','rarely'
                    )),

  bio             TEXT      NULL,
  profession      VARCHAR   NULL,
  avatar_url      VARCHAR   NULL,

  private_mode    BOOLEAN   NOT NULL DEFAULT FALSE,
  social_paused   BOOLEAN   NOT NULL DEFAULT FALSE,

  -- Verifications and security
  email_verified       BOOLEAN NOT NULL DEFAULT FALSE,
  phone_number         VARCHAR NULL,
  phone_verified       BOOLEAN NOT NULL DEFAULT FALSE,
  last_login_at        TIMESTAMPTZ NULL,
  failed_login_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until         TIMESTAMPTZ NULL,
  date_of_birth        DATE    NULL,

  -- Soft delete
  is_deleted            BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_at            TIMESTAMPTZ NULL,

  -- Timestamps
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Key Indexes
CREATE INDEX idx_users_email    ON users(email);
CREATE INDEX idx_users_phone    ON users(phone_number) WHERE phone_number IS NOT NULL;
CREATE INDEX idx_users_location ON users(country, province, city) WHERE city IS NOT NULL;
CREATE UNIQUE INDEX ux_users_alias ON users(alias) WHERE alias IS NOT NULL;
-- Optional (language-based searches)
-- CREATE INDEX idx_users_language ON users(language) WHERE language IS NOT NULL;
```
---

### 2. Table `user_sessions`

```sql
CREATE TABLE user_sessions (
  id              UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID      NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
  token_hash      VARCHAR   NOT NULL,
  device_info     JSONB     NULL,
  ip_address      INET      NULL,
  user_agent      TEXT      NULL,

-- [NEW] Allows manually closing a session (forced logout)
  revoked_by_user BOOLEAN   NOT NULL DEFAULT FALSE, -- reserved for manual logout

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ NULL
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token   ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at) WHERE revoked_at IS NULL;
```
---

### 3. Table `interests`

```sql
CREATE TABLE interests (
  id            SERIAL   PRIMARY KEY,
  name          TEXT     NOT NULL UNIQUE,
  category      VARCHAR  NULL,

  -- [NEW] Display order in the UI (chips, lists)
  display_order INTEGER  NULL, -- reserved for future UI sorting

  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
---

### 4. Table `user_interests`

```sql
CREATE TABLE user_interests (
  user_id     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  interest_id INTEGER NOT NULL REFERENCES interests(id) ON DELETE CASCADE,
  weight      REAL    NOT NULL DEFAULT 1.0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, interest_id)
);
```
---

### 5. Table `plan_category`

```sql
CREATE TABLE plan_category (
  id          SERIAL   PRIMARY KEY,
  name        TEXT     NOT NULL UNIQUE,
  description TEXT     NULL
);

INSERT INTO plan_category (name, description) VALUES
  ('social','Actividades sociales y encuentros'),
  ('cultural','Museos, arte, teatro'),
  ('gastronomy','Restaurantes, cafés, bares'),
  ('sports','Deporte y actividad física'),
  ('outdoor','Naturaleza y aire libre'),
  ('entertainment','Cine, videojuegos, espectáculos'),
  ('shopping','Compras y centros comerciales'),
  ('education','Cursos, talleres, conferencias'),
  ('nightlife','Vida nocturna y discotecas'),
  ('family','Actividades familiares'),
  ('other','Otras actividades');
```
---

### 6. Tabla `availability_weekly_templates` **[NEW]**

```sql
CREATE TABLE availability_weekly_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id UUID NOT NULL
    REFERENCES users(id)
    ON DELETE CASCADE,

  weekday SMALLINT NOT NULL
    CHECK (weekday BETWEEN 1 AND 7),
    -- ISO 8601: 1 = Monday, 7 = Sunday

  start_minute SMALLINT NOT NULL
    CHECK (start_minute BETWEEN 0 AND 1439),

  end_minute SMALLINT NOT NULL
    CHECK (end_minute BETWEEN 1 AND 1440),

  timezone VARCHAR(50) NOT NULL,
    -- IANA timezone, e.g. 'Europe/Madrid'

  plan_text TEXT NULL,
    -- Optional free text: "What would you like to do?"

  language_code VARCHAR(5) NOT NULL DEFAULT 'es'
    CHECK (language_code ~ '^[a-z]{2}(-[A-Z]{2})?$'),

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CHECK (start_minute < end_minute)
);

CREATE INDEX idx_awd_user ON availability_weekly_templates(user_id);
CREATE INDEX idx_awd_user_weekday ON availability_weekly_templates(user_id, weekday);
```

**Semantics:** default weekly rules. They do not represent real or historical availability.  
They are applied only if no override or specific-date availability exists for a given date.

---

### 7. Table `availability_day_overrides` **[NEW]**

```sql
CREATE TABLE availability_day_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id UUID NOT NULL
    REFERENCES users(id)
    ON DELETE CASCADE,

  date DATE NOT NULL,
    -- Local date in the user's timezone

  timezone VARCHAR(50) NOT NULL,
    -- IANA timezone

  override_type VARCHAR(10) NOT NULL
    CHECK (override_type IN ('replace','clear')),
  -- replace: use only availabilities defined for that day
  -- clear: no availability for the day, even if a weekly template exists

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (user_id, date)
);
```

**Semantics:** explicit signal that a specific date does not follow the weekly template,  
avoiding ambiguity between “not defined” and “not available”.

---

### 8. Table `availabilities`

```sql
CREATE TABLE availabilities (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  start_time_utc  TIMESTAMPTZ NOT NULL,
  end_time_utc    TIMESTAMPTZ NOT NULL,
  timezone        VARCHAR     NOT NULL,

 -- Free-text field: "what would you like to do?"
  plan_text       TEXT        NULL,

  -- Language in which plan_text was written (e.g. 'es', 'en', 'es-ES')
  language_code   VARCHAR(5)  DEFAULT 'es'
                    CHECK (language_code ~ '^[a-z]{2}(-[A-Z]{2})?$'),

  is_flexible     BOOLEAN     NOT NULL DEFAULT FALSE,
  is_synthetic    BOOLEAN     NOT NULL DEFAULT FALSE,

  -- [NEW] Time slot source (weekly onboarding or calendar-specific)
  source          VARCHAR     NULL
                    CHECK (source IN ('habitual','punctual')),

  -- [NEW] Marks recurring availability (not part of the initial MVP)
  is_recurring    BOOLEAN     NOT NULL DEFAULT FALSE, -- reserved for recurring events

  category_id     INTEGER     NULL REFERENCES plan_category(id),

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CHECK (start_time_utc < end_time_utc)
);

CREATE INDEX idx_availabilities_user_time ON availabilities(user_id, start_time_utc, end_time_utc);
CREATE INDEX idx_availabilities_timerange ON availabilities(start_time_utc, end_time_utc);
CREATE INDEX idx_availabilities_synthetic ON availabilities(is_synthetic);
CREATE INDEX idx_availabilities_plan_text ON availabilities(plan_text) WHERE plan_text IS NOT NULL;
CREATE INDEX idx_availabilities_category ON availabilities(category_id);
CREATE INDEX idx_availabilities_source   ON availabilities(source) WHERE source IS NOT NULL;
```
---

### 9. Table `plan_proposals`

```sql
CREATE TABLE plan_proposals (
  id                    UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  proposer_id           UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invitee_id            UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  availability_id       UUID      NOT NULL REFERENCES availabilities(id) ON DELETE CASCADE,
  message               TEXT      NULL,
  status                VARCHAR   NOT NULL
                         CHECK (status IN ('pending','accepted','rejected','cancelled')),
  proposed_start_time   TIMESTAMPTZ NOT NULL,
  proposed_end_time     TIMESTAMPTZ NOT NULL,
  reminder_sent_at      TIMESTAMPTZ NULL,
  rejection_reason      TEXT      NULL,
  rating                INTEGER   CHECK (rating BETWEEN 1 AND 5),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  responded_at          TIMESTAMPTZ NULL,
  cancelled_at          TIMESTAMPTZ NULL,
  cancelled_by          UUID      NULL REFERENCES users(id),
  cancelled_by_role     VARCHAR   NULL
                         CHECK (cancelled_by_role IN ('proposer','invitee')),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CHECK (proposed_start_time < proposed_end_time)
);

CREATE INDEX idx_plan_proposals_status       ON plan_proposals(status, created_at);
CREATE INDEX idx_plan_proposals_proposer     ON plan_proposals(proposer_id, status);
CREATE INDEX idx_plan_proposals_invitee      ON plan_proposals(invitee_id, status);
CREATE INDEX idx_plan_proposals_availability ON plan_proposals(availability_id);
```
---

### 10. Table `contacts`

```sql
CREATE TABLE contacts (
  user_id_1           UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_id_2           UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  active              BOOLEAN NOT NULL DEFAULT TRUE,
  paused              BOOLEAN NOT NULL DEFAULT FALSE,
  connection_source   VARCHAR CHECK (connection_source IN ('invitation_link','search','mutual_friend')),
  last_interaction_at TIMESTAMPTZ NULL,
  interaction_count   INTEGER NOT NULL DEFAULT 0,
  connection_strength REAL    NOT NULL DEFAULT 0.0,

  -- [NEW] Audit: last user who modified the relationship
  last_updated_by     UUID    NULL REFERENCES users(id), -- reserved for auditing

  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  disconnected_at     TIMESTAMPTZ NULL,
  PRIMARY KEY (user_id_1, user_id_2),
  CHECK (user_id_1 < user_id_2)
);

CREATE INDEX idx_contacts_user1    ON contacts(user_id_1);
CREATE INDEX idx_contacts_user2    ON contacts(user_id_2);
CREATE INDEX idx_contacts_active   ON contacts(active, user_id_1);
CREATE INDEX idx_contacts_strength ON contacts(connection_strength DESC);
-- Optional:
-- CREATE INDEX idx_contacts_last_updated_by ON contacts(last_updated_by) WHERE last_updated_by IS NOT NULL;
```
---

### 11. Table `invitation_links`

```sql
CREATE TABLE invitation_links (
  id            UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  creator_id    UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  link_type     VARCHAR   NOT NULL
                   CHECK (link_type IN ('invite_one','invite_many','connect_many','group_scheduling')),
  token         VARCHAR   NOT NULL UNIQUE,
  current_uses  INTEGER   NOT NULL DEFAULT 0,
  max_uses      INTEGER   NOT NULL CHECK (max_uses IN (5,10,20,50)),
  link_status   VARCHAR   NOT NULL CHECK (link_status IN ('active','expired','revoked')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at    TIMESTAMPTZ NOT NULL,
  revoked_at    TIMESTAMPTZ NULL,
  revoked_by    UUID      NULL REFERENCES users(id),
  related_data  JSONB     NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_invitation_links_token   ON invitation_links(token);
CREATE INDEX idx_invitation_links_status         ON invitation_links(link_status, expires_at);
CREATE INDEX idx_invitation_links_creator        ON invitation_links(creator_id, link_status);
```
---

### 12. Table `invitation_acceptances`

```sql
CREATE TABLE invitation_acceptances (
  id                  UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  invitation_link_id  UUID      NOT NULL REFERENCES invitation_links(id) ON DELETE CASCADE,
  user_id             UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- [NEW] Channel used for acceptance (telemetry/analytics)
  accepted_via        VARCHAR   NULL
                        CHECK (accepted_via IN ('web','email','link')),

  accepted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ux_invitation_user UNIQUE(invitation_link_id, user_id)
);

CREATE INDEX idx_invitation_acceptances_link ON invitation_acceptances(invitation_link_id);
CREATE INDEX idx_invitation_acceptances_user ON invitation_acceptances(user_id);
```
---

### 13. Table `notifications`

```sql
CREATE TABLE notifications (
  id         UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type       VARCHAR   NOT NULL CHECK (type IN (
               'invitation_received','plan_proposal','plan_response',
               'expiration_reminder','new_match','plan_cancelled',
               'invitation_revoked','password_reset',
               'contact_request_accepted','system_announcement'
             )),
  content    TEXT      NOT NULL,
  related_id UUID      NULL,
  seen       BOOLEAN   NOT NULL DEFAULT FALSE,

  -- [NEW] Notification priority (1 = normal, 2 = high, etc.)
  priority   SMALLINT  NOT NULL DEFAULT 1, -- reserved for importance

  -- [NEW] Scheduled date/time for reminders
  scheduled_at TIMESTAMPTZ NULL,           -- reserved for reminders

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at    TIMESTAMPTZ NULL
);

CREATE INDEX idx_notifications_user_seen ON notifications(user_id, seen, created_at);
CREATE INDEX idx_notifications_type      ON notifications(type, created_at);
CREATE INDEX idx_notifications_unseen    ON notifications(user_id, created_at) WHERE seen = FALSE;
-- Optional (priority-based inboxes):
-- CREATE INDEX idx_notifications_priority ON notifications(user_id, priority DESC, created_at DESC);
```
---

### 14. Table `user_interaction_logs`

```sql
CREATE TABLE user_interaction_logs (
  id               UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  related_user_id  UUID      NULL REFERENCES users(id),
  event_type       VARCHAR   NOT NULL,
  metadata         JSONB     NULL,
  timestamp        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_logs_user  ON user_interaction_logs(user_id, timestamp);
CREATE INDEX idx_user_logs_event ON user_interaction_logs(event_type, timestamp);
```
---

### 15. Table `user_notification_settings`

```sql
CREATE TABLE user_notification_settings (
  user_id          UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  notification_type TEXT   NOT NULL,
  enabled          BOOLEAN NOT NULL DEFAULT TRUE,
  delivery_method  VARCHAR DEFAULT 'email'
                   CHECK (delivery_method IN ('email','push','sms','webhook')),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, notification_type)
);

CREATE INDEX idx_uns_notification_type ON user_notification_settings(notification_type);
CREATE INDEX idx_uns_delivery_method ON user_notification_settings(delivery_method);
```
---

### 16. Table `contact_requests`

```sql
CREATE TABLE contact_requests (
  id            UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_id  UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  requested_id  UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status        VARCHAR   NOT NULL
                 CHECK (status IN ('pending','accepted','rejected','cancelled')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  responded_at  TIMESTAMPTZ NULL,
  responded_by  UUID      NULL REFERENCES users(id),
  message       TEXT      NULL,
  via_mcp       BOOLEAN   NOT NULL DEFAULT FALSE,
  metadata      JSONB     NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (requester_id, requested_id)
);

CREATE INDEX idx_contact_requests_status    ON contact_requests(status, created_at);
CREATE INDEX idx_contact_requests_requested ON contact_requests(requested_id, status);
```
---

### 17. Table `plan_categories_map`

```sql
CREATE TABLE plan_categories_map (
  availability_id UUID NOT NULL REFERENCES availabilities(id) ON DELETE CASCADE,
  category_id     INTEGER NOT NULL REFERENCES plan_category(id) ON DELETE CASCADE,
  assigned_by     TEXT    NOT NULL
                   CHECK (assigned_by IN ('user','ai'))
                   DEFAULT 'ai',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (availability_id, category_id)
);

CREATE INDEX idx_pcm_category     ON plan_categories_map(category_id);
CREATE INDEX idx_pcm_availability ON plan_categories_map(availability_id);
```
---

### 18. Tabla `semantic_similarity_log`

```sql
CREATE TABLE semantic_similarity_log (
  id                UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  availability_a_id UUID      NOT NULL REFERENCES availabilities(id) ON DELETE CASCADE,
  availability_b_id UUID      NOT NULL REFERENCES availabilities(id) ON DELETE CASCADE,
  score             REAL      NOT NULL,
  model_version     TEXT      NOT NULL DEFAULT 'v1',
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ssl_pair_time ON semantic_similarity_log(availability_a_id, availability_b_id, computed_at);
CREATE INDEX idx_ssl_score     ON semantic_similarity_log(score DESC);
```
---

### 19. Tabla `user_affinities`

```sql
CREATE TABLE user_affinities (
  user_id_a     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_id_b     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  affinity      REAL    NOT NULL,

  -- [NEW] Affinity context (e.g. "plans", "contacts")
  context       VARCHAR NULL, -- reserved for future ML context

  model_version TEXT   NOT NULL DEFAULT 'v1',
  expires_at    TIMESTAMPTZ NULL,
  computed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id_a, user_id_b),
  CHECK (user_id_a < user_id_b)
);

CREATE INDEX idx_ua_inverse  ON user_affinities(user_id_b, user_id_a);
CREATE INDEX idx_ua_affinity ON user_affinities(affinity DESC);
```
---

### 20. Table `mcp_context_snapshots` (reserved for future integration)

> 🧠 **Purpose:** This table is reserved for Yokedo’s future integration with the **Model Context Protocol (MCP)**.  
> It will allow storing “snapshots” of each user’s social, temporal, and semantic context, to be queried or shared with external agents (LLMs, AI pipelines, etc.).  
> **It is not included** in the initial MVP migrations.

```sql
CREATE TABLE mcp_context_snapshots (
  id            UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  context_json  JSONB     NOT NULL, -- Full contextual state (availabilities, affinities, active plans)
  source        VARCHAR   NOT NULL
                  CHECK (source IN ('agent','system','user')),
  model_version TEXT      NOT NULL DEFAULT 'v1',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mcp_snapshots_user ON mcp_context_snapshots(user_id, created_at DESC);
CREATE INDEX idx_mcp_snapshots_source ON mcp_context_snapshots(source);
```
---

## 🚀 STEP 3: Triggers `updated_at`

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applies to all tables that have an updated_at column
CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_availabilities_updated_at
  BEFORE UPDATE ON availabilities
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_plan_proposals_updated_at
  BEFORE UPDATE ON plan_proposals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_invitation_links_updated_at
  BEFORE UPDATE ON invitation_links
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_notification_settings_updated_at
  BEFORE UPDATE ON user_notification_settings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_contact_requests_updated_at
  BEFORE UPDATE ON contact_requests
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_availability_weekly_templates_updated_at
  BEFORE UPDATE ON availability_weekly_templates
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_availability_day_overrides_updated_at
  BEFORE UPDATE ON availability_day_overrides
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```
---

## Notes
- Schema validated against PostgreSQL 15
- Designed to support future ML features (embeddings, similarity logs)

### Internationalization

> **Important Note:** Category names and descriptions are currently stored in Spanish, as the MVP is initially targeted at the Spanish market.  
> These values are considered user-facing content and are expected to be externalized or internationalized (i18n) in a future phase, without without altering the core schema design.

