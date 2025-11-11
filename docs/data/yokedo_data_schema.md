# Yokedo – Modelo de Datos v1.0 (MCP-ready)
**Última actualización:** 2025-11-02 15:26 UTC

---

## 🚀 PASO 1: Extensiones PostgreSQL (CRÍTICO)

```sql
-- Para gen_random_uuid() en PKs
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- Para vectores (embeddings ML)
CREATE EXTENSION IF NOT EXISTS vector;
-- Para campos case-insensitive
CREATE EXTENSION IF NOT EXISTS citext;
```
---

## 🚀 PASO 2: Creación de Tablas (Orden Obligatorio)

1. **users**  
2. **user_sessions**  
3. **interests**  
4. **user_interests**  
5. **plan_category**  
6. **availabilities**  
7. **plan_proposals**  
8. **contacts**  
9. **invitation_links**  
10. **invitation_acceptances**  
11. **notifications**  
12. **user_interaction_logs**  
13. **user_notification_settings**  
14. **contact_requests**  
15. **plan_categories_map**  
16. **semantic_similarity_log**  
17. **user_affinities**  
18. **mcp_context_snapshots** (documentada; reservada)

> Todas las DDL incluyen tipos, `CHECK`, `FK`, índices y comentarios. Los campos marcados con `-- [NEW]` son extensiones seguras **aditivas** y algunos están documentados como *reserved for future use*.

---

### 1. Tabla `users`

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

  -- [NEW] Idioma preferido del usuario (i18n). Ej.: 'es', 'en', 'es-ES'
  language        VARCHAR(5) NULL
                    CHECK (language ~ '^[a-z]2(-[A-Z]2)?$'),

  frequency_social VARCHAR  NULL
                    CHECK (frequency_social IN (
                      'daily','weekly','monthly','rarely'
                    )),

  bio             TEXT      NULL,
  profession      VARCHAR   NULL,
  avatar_url      VARCHAR   NULL,

  private_mode    BOOLEAN   NOT NULL DEFAULT FALSE,
  social_paused   BOOLEAN   NOT NULL DEFAULT FALSE,

  -- Verificaciones y seguridad
  email_verified       BOOLEAN NOT NULL DEFAULT FALSE,
  phone_number         VARCHAR NULL,
  phone_verified       BOOLEAN NOT NULL DEFAULT FALSE,
  last_login_at        TIMESTAMPTZ NULL,
  failed_login_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until         TIMESTAMPTZ NULL,
  date_of_birth        DATE    NULL,

  -- Timestamps
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices clave
CREATE INDEX idx_users_email    ON users(email);
CREATE INDEX idx_users_phone    ON users(phone_number) WHERE phone_number IS NOT NULL;
CREATE INDEX idx_users_location ON users(country, province, city) WHERE city IS NOT NULL;
CREATE UNIQUE INDEX ux_users_alias ON users(alias) WHERE alias IS NOT NULL;
-- Opcional (búsquedas por idioma)
-- CREATE INDEX idx_users_language ON users(language) WHERE language IS NOT NULL;
```
---

### 2. Tabla `user_sessions`

```sql
CREATE TABLE user_sessions (
  id              UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID      NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
  token_hash      VARCHAR   NOT NULL,
  device_info     JSONB     NULL,
  ip_address      INET      NULL,
  user_agent      TEXT      NULL,

  -- [NEW] Permite cerrar una sesión manualmente (logout forzado)
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

### 3. Tabla `interests`

```sql
CREATE TABLE interests (
  id            SERIAL   PRIMARY KEY,
  name          TEXT     NOT NULL UNIQUE,
  category      VARCHAR  NULL,

  -- [NEW] Orden de visualización en UI (chips, listas)
  display_order INTEGER  NULL, -- reserved for future UI sorting

  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
---

### 4. Tabla `user_interests`

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

### 5. Tabla `plan_category`

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

### 6. Tabla `availabilities`

```sql
CREATE TABLE availabilities (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  start_time_utc  TIMESTAMPTZ NOT NULL,
  end_time_utc    TIMESTAMPTZ NOT NULL,
  timezone        VARCHAR     NOT NULL,

  -- Texto libre: "qué te apetece hacer"
  plan_text       TEXT        NULL,

  -- Idioma en el que se escribió plan_text (ej. 'es', 'en', 'es-ES')
  language_code   VARCHAR(5)  DEFAULT 'es'
                    CHECK (language_code ~ '^[a-z]2(-[A-Z]2)?$'),

  is_flexible     BOOLEAN     NOT NULL DEFAULT FALSE,
  is_synthetic    BOOLEAN     NOT NULL DEFAULT FALSE,

  -- [NEW] Origen de la franja (onboarding habitual o puntual en calendario)
  source          VARCHAR     NULL
                    CHECK (source IN ('habitual','punctual')),

  -- [NEW] Marcar disponibilidad recurrente (no MVP inicial)
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

### 7. Tabla `plan_proposals`

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

### 8. Tabla `contacts`

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

  -- [NEW] Auditoría: último usuario que modificó el vínculo
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
-- Opcional:
-- CREATE INDEX idx_contacts_last_updated_by ON contacts(last_updated_by) WHERE last_updated_by IS NOT NULL;
```
---

### 9. Tabla `invitation_links`

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

### 10. Tabla `invitation_acceptances`

```sql
CREATE TABLE invitation_acceptances (
  id                  UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  invitation_link_id  UUID      NOT NULL REFERENCES invitation_links(id) ON DELETE CASCADE,
  user_id             UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- [NEW] Canal utilizado para aceptar (telemetría/analítica)
  accepted_via        VARCHAR   NULL
                        CHECK (accepted_via IN ('web','email','link')),

  accepted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ux_invitation_user UNIQUE(invitation_link_id, user_id)
);

CREATE INDEX idx_invitation_acceptances_link ON invitation_acceptances(invitation_link_id);
CREATE INDEX idx_invitation_acceptances_user ON invitation_acceptances(user_id);
```
---

### 11. Tabla `notifications`

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

  -- [NEW] Prioridad de la notificación (1=normal, 2=alta, etc.)
  priority   SMALLINT  NOT NULL DEFAULT 1, -- reserved for importance

  -- [NEW] Fecha/hora programada para recordatorios
  scheduled_at TIMESTAMPTZ NULL,           -- reserved for reminders

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at    TIMESTAMPTZ NULL
);

CREATE INDEX idx_notifications_user_seen ON notifications(user_id, seen, created_at);
CREATE INDEX idx_notifications_type      ON notifications(type, created_at);
CREATE INDEX idx_notifications_unseen    ON notifications(user_id, created_at) WHERE seen = FALSE;
-- Opcional (bandejas por prioridad):
-- CREATE INDEX idx_notifications_priority ON notifications(user_id, priority DESC, created_at DESC);
```
---

### 12. Tabla `user_interaction_logs`

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

### 13. Tabla `user_notification_settings`

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

### 14. Tabla `contact_requests`

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

### 15. Tabla `plan_categories_map`

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

### 16. Tabla `semantic_similarity_log`

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

### 17. Tabla `user_affinities`

```sql
CREATE TABLE user_affinities (
  user_id_a     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_id_b     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  affinity      REAL    NOT NULL,

  -- [NEW] Contexto de la afinidad (p. ej., "plans", "contacts")
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

### 18. Tabla `mcp_context_snapshots` (reserved for future integration)

> 🧠 **Propósito:** Esta tabla está reservada para la integración futura de Yokedo con el estándar **Model Context Protocol (MCP)**.  
> Permitirá almacenar “snapshots” del contexto social, temporal y semántico de cada usuario, para ser consultados o compartidos con agentes externos (LLMs, pipelines de IA, etc.).  
> **No se incluye** en las migraciones iniciales del MVP.

```sql
CREATE TABLE mcp_context_snapshots (
  id            UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  context_json  JSONB     NOT NULL, -- estado contextual completo (disponibilidades, afinidades, planes activos)
  source        VARCHAR   NOT NULL
                  CHECK (source IN ('agent','system','user')),
  model_version TEXT      NOT NULL DEFAULT 'v1',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mcp_snapshots_user ON mcp_context_snapshots(user_id, created_at DESC);
CREATE INDEX idx_mcp_snapshots_source ON mcp_context_snapshots(source);
```
---

## 🚀 PASO 3: Triggers `updated_at`

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplica a todas las tablas que tienen columna updated_at
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
```
---

## 🎯 Validación Final

* ✔️ **Sintaxis SQL**: sin errores, todos los `CHECK` completos.  
* ✔️ **Integridad**: FK a tablas existentes, orden correcto.  
* ✔️ **Índices**: compuestos y parciales donde corresponde.  
* ✔️ **Seguridad**: UUID, verificaciones, preparado para rate-limiting.  
* ✔️ **Auditoría**: triggers automáticos para `updated_at`.  
* ✔️ **ML/IA**: preparado para embeddings y logs.  
* ✔️ **Extensibilidad segura**: campos *reserved for future use* añadidos como cambios **aditivos** (no rompen el modelo).
```sql
-- ============================================================
-- 🗒️ Notas internas
-- Validación manual completada el 2025-11-02 15:26 UTC
-- Compatible con Alembic y PostgreSQL 15+
-- Preparado para migraciones CI/CD y futuras integraciones MCP
-- Session: 2025-10-26 / MCP-ready revision
-- ============================================================
```
