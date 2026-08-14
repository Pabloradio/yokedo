# Yokedo — PostgreSQL Data Schema (Verified from PostgreSQL)

**Latest update:** 2026-07-28 
**Source of truth:** verified physically in PostgreSQL (`public` schema)  
**Scope:** current real schema only. This document reflects the physical database state and should override outdated design documents when they conflict.

---

## Tables present in `public`

- `alembic_version_auth`
- `alembic_version_availability`
- `alembic_version_contacts`
- `availabilities`
- `availability_day_overrides`
- `availability_weekly_templates`
- `contact_events`
- `contact_requests`
- `contacts`
- `invitation_acceptances`
- `invitation_links`
- `user_sessions`
- `users`

---

## Alembic revision state

- `alembic_version_auth` → `caf17025ae92`
- `alembic_version_availability` → `901f5fb17643`
- `alembic_version_contacts` → `8460e09ba085`

---

## Trigger inventory

Query result from `information_schema.triggers` for the verified tables:

- No triggers found for:

  - `availabilities`
  - `availability_day_overrides`
  - `availability_weekly_templates`
  - `contact_events`
  - `contact_requests`
  - `contacts`
  - `invitation_acceptances`
  - `invitation_links`
  - `user_sessions`
  - `users`

---

# Table `users`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → no physical DB default
- `email` → `citext` → `NOT NULL` → no physical DB default
- `alias` → `citext` → nullable → no physical DB default
- `password_hash` → `character varying(128)` → `NOT NULL` → no physical DB default
- `is_active` → `boolean` → `NOT NULL` → no physical DB default
- `is_admin` → `boolean` → `NOT NULL` → no physical DB default
- `language` → `character varying(5)` → `NOT NULL` → DB default `'es'::character varying`
- `gender` → `character varying(30)` → nullable → DB default `'prefer_not_to_say'::character varying`
- `age_range` → `character varying(30)` → nullable → DB default `'unspecified'::character varying`
- `timezone` → `character varying(50)` → nullable → DB default `'Europe/Madrid'::character varying`
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `updated_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `first_name` → `character varying(50)` → `NOT NULL` → no physical DB default
- `last_name` → `character varying(50)` → `NOT NULL` → no physical DB default
- `last_login_at` → `timestamp with time zone` → nullable → no physical DB default
- `is_deleted` → `boolean` → `NOT NULL` → DB default `false`
- `deleted_at` → `timestamp with time zone` → nullable → no physical DB default

Constraints:
- `users_pkey` → PRIMARY KEY (`id`)
- `users_alias_key` → UNIQUE (`alias`)
- `users_email_key` → UNIQUE (`email`)

Indexes:
- `users_pkey` → unique btree (`id`)
- `users_alias_key` → unique btree (`alias`)
- `users_email_key` → unique btree (`email`)

Referenced by:
- `availabilities.user_id` → `users(id)` ON DELETE CASCADE
- `availability_day_overrides.user_id` → `users(id)` ON DELETE CASCADE
- `availability_weekly_templates.user_id` → `users(id)` ON DELETE CASCADE
- `contact_events.actor_user_id` → `users(id)` ON DELETE SET NULL
- `contacts.user_high_id` → `users(id)`
- `contacts.user_low_id` → `users(id)`
- `user_sessions.user_id` → `users(id)`
- `invitation_acceptances.user_id` → `users(id)` ON DELETE CASCADE
- `invitation_links.creator_id` → `users(id)` ON DELETE CASCADE
- `invitation_links.revoked_by` → `users(id)` ON DELETE SET NULL

Access method:
- `heap`

## Notes
- No `social_paused` column exists in the current real schema.
- No `private_mode` column exists in the current real schema.
- The absence of a DB default for `id` means this document does **not** assume UUID generation at PostgreSQL level for `users`.

---

# Table `user_sessions`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → no physical DB default
- `user_id` → `uuid` → `NOT NULL` → no physical DB default
- `refresh_token_hash` → `character varying(128)` → `NOT NULL` → no physical DB default
- `created_at` → `timestamp with time zone` → `NOT NULL` → no physical DB default
- `expires_at` → `timestamp with time zone` → `NOT NULL` → no physical DB default
- `user_agent` → `character varying(200)` → nullable → no physical DB default
- `ip_address` → `character varying(45)` → nullable → no physical DB default

Constraints:
- `user_sessions_pkey` → PRIMARY KEY (`id`)
- `user_sessions_user_id_fkey` → FOREIGN KEY (`user_id`) REFERENCES `users(id)`

Indexes:
- `user_sessions_pkey` → unique btree (`id`)

Access method:
- `heap`

## Notes
- Column name is `refresh_token_hash` in the current real schema.
- No physical DB defaults are present in the inspected output.

---

# Table `availabilities`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → DB default `gen_random_uuid()`
- `user_id` → `uuid` → `NOT NULL` → no physical DB default
- `start_time_utc` → `timestamp with time zone` → `NOT NULL` → no physical DB default
- `end_time_utc` → `timestamp with time zone` → `NOT NULL` → no physical DB default
- `timezone` → `character varying(50)` → `NOT NULL` → no physical DB default
- `plan_text` → `text` → nullable → no physical DB default
- `language_code` → `character varying(5)` → nullable → DB default `'es'::character varying`
- `is_flexible` → `boolean` → `NOT NULL` → DB default `false`
- `is_synthetic` → `boolean` → `NOT NULL` → DB default `false`
- `source` → `character varying` → nullable → no physical DB default
- `is_recurring` → `boolean` → `NOT NULL` → DB default `false`
- `category_id` → `integer` → nullable → no physical DB default
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `updated_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`

Constraints:
- `availabilities_pkey` → PRIMARY KEY (`id`)
- `availabilities_user_id_fkey` → FOREIGN KEY (`user_id`) REFERENCES `users(id)` ON DELETE CASCADE
- `ck_availabilities_language_code_format` → CHECK (`language_code IS NULL OR language_code::text ~ '^[a-z]{2}(-[A-Z]{2})?$'::text`)
- `ck_availabilities_source` → CHECK (`source IS NULL OR (source::text = ANY (ARRAY['habitual'::character varying, 'punctual'::character varying]::text[])))`
- `ck_availabilities_start_lt_end` → CHECK (`start_time_utc < end_time_utc`)

Indexes:
- `availabilities_pkey` → unique btree (`id`)
- `idx_availabilities_category` → btree (`category_id`)
- `idx_availabilities_plan_text` → btree (`plan_text`) WHERE (`plan_text IS NOT NULL`)
- `idx_availabilities_source` → btree (`source`) WHERE (`source IS NOT NULL`)
- `idx_availabilities_synthetic` → btree (`is_synthetic`)
- `idx_availabilities_timerange` → btree (`start_time_utc`, `end_time_utc`)
- `idx_availabilities_user_time` → btree (`user_id`, `start_time_utc`, `end_time_utc`)

Access method:
- `heap`

## Notes
- Current DB-level allowed values for `source`: `habitual`, `punctual`, or `NULL`.
- `category_id` exists physically and is indexed, but no foreign key for it appears in the verified constraint output.

---

# Table `availability_weekly_templates`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → DB default `gen_random_uuid()`
- `user_id` → `uuid` → `NOT NULL` → no physical DB default
- `weekday` → `smallint` → `NOT NULL` → no physical DB default
- `start_minute` → `smallint` → `NOT NULL` → no physical DB default
- `end_minute` → `smallint` → `NOT NULL` → no physical DB default
- `timezone` → `character varying(50)` → `NOT NULL` → no physical DB default
- `plan_text` → `text` → nullable → no physical DB default
- `language_code` → `character varying(5)` → `NOT NULL` → DB default `'es'::character varying`
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `updated_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`

Constraints:
- `availability_weekly_templates_pkey` → PRIMARY KEY (`id`)
- `availability_weekly_templates_user_id_fkey` → FOREIGN KEY (`user_id`) REFERENCES `users(id)` ON DELETE CASCADE
- `ck_availability_weekly_templates_end_minute_range` → CHECK (`end_minute >= 1 AND end_minute <= 1440`)
- `ck_availability_weekly_templates_language_code_format` → CHECK (`language_code::text ~ '^[a-z]{2}(-[A-Z]{2})?$'::text`)
- `ck_availability_weekly_templates_start_lt_end` → CHECK (`start_minute < end_minute`)
- `ck_availability_weekly_templates_start_minute_range` → CHECK (`start_minute >= 0 AND start_minute <= 1439`)
- `ck_availability_weekly_templates_weekday_range` → CHECK (`weekday >= 1 AND weekday <= 7`)

Indexes:
- `availability_weekly_templates_pkey` → unique btree (`id`)
- `idx_awd_user` → btree (`user_id`)
- `idx_awd_user_weekday` → btree (`user_id`, `weekday`)

Access method:
- `heap`

---

# Table `availability_day_overrides`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → DB default `gen_random_uuid()`
- `user_id` → `uuid` → `NOT NULL` → no physical DB default
- `date` → `date` → `NOT NULL` → no physical DB default
- `timezone` → `character varying(50)` → `NOT NULL` → no physical DB default
- `override_type` → `character varying(10)` → `NOT NULL` → no physical DB default
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `updated_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`

Constraints:
- `availability_day_overrides_pkey` → PRIMARY KEY (`id`)
- `availability_day_overrides_user_id_fkey` → FOREIGN KEY (`user_id`) REFERENCES `users(id)` ON DELETE CASCADE
- `ck_availability_day_overrides_override_type` → CHECK (`override_type::text = ANY (ARRAY['replace'::character varying, 'clear'::character varying]::text[]))`
- `ux_availability_day_overrides_user_date` → UNIQUE (`user_id`, `date`)

Indexes:
- `availability_day_overrides_pkey` → unique btree (`id`)
- `ux_availability_day_overrides_user_date` → unique btree (`user_id`, `date`)

Access method:
- `heap`

## Notes
- Current DB-level allowed values for `override_type`: `replace`, `clear`.

---

# Table `contact_requests`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → DB default `gen_random_uuid()`
- `requester_id` → `uuid` → `NOT NULL` → no physical DB default
- `requested_id` → `uuid` → `NOT NULL` → no physical DB default
- `status` → `character varying(20)` → `NOT NULL` → no physical DB default
- `message` → `text` → nullable → no physical DB default
- `source` → `character varying(50)` → nullable → no physical DB default
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `updated_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `responded_at` → `timestamp with time zone` → nullable → no physical DB default
- `responded_by` → `uuid` → nullable → no physical DB default

Constraints:
- `pk_contact_requests` → PRIMARY KEY (`id`)
- `ck_contact_requests_ck_contact_requests_no_self_request` → CHECK (`requester_id <> requested_id`)
- `ck_contact_requests_ck_contact_requests_status_valid` → CHECK (`status::text = ANY (ARRAY['pending'::character varying, 'accepted'::character varying, 'rejected'::character varying, 'cancelled'::character varying]::text[]))`

Indexes:
- `pk_contact_requests` → unique btree (`id`)
- `idx_contact_requests_requested_status` → btree (`requested_id`, `status`)
- `idx_contact_requests_requester_status` → btree (`requester_id`, `status`)

Access method:
- `heap`

## Notes
- No physical FKs to `users` exist in the current schema.
- No uniqueness by pair or by direction exists in the current schema.
- `status` has **no physical DB default** in the verified output.
- Current DB-level allowed values for `status`: `pending`, `accepted`, `rejected`, `cancelled`.
- No triggers exist.

---

# Table `invitation_links`

## Physical definition

Columns:

- `id` → `uuid` → NOT NULL → DB default: `gen_random_uuid()`
- `creator_id` → `uuid` → NOT NULL
- `token` → `character varying(255)` → NOT NULL
- `max_uses` → `integer` → NOT NULL
- `current_uses` → `integer` → NOT NULL → DB default: `0`
- `link_status` → `character varying(32)` → NOT NULL → DB default: `'active'::character varying`
- `expires_at` → `timestamp with time zone` → NOT NULL
- `created_at` → `timestamp with time zone` → NOT NULL → DB default: `now()`
- `updated_at` → `timestamp with time zone` → NOT NULL → DB default: `now()`
- `revoked_at` → `timestamp with time zone`
- `revoked_by` → `uuid`

Indexes:

- `pk_invitation_links` → PRIMARY KEY (`id`)
- `ix_invitation_links_creator_id` → (`creator_id`)
- `ix_invitation_links_status_expires_at` → (`link_status`, `expires_at`)
- `uq_invitation_links_token` → UNIQUE (`token`)

Check constraints:

- `ck_invitation_links_current_uses_lte_max_uses`
- `CHECK (current_uses <= max_uses)`

- `ck_invitation_links_current_uses_non_negative`
- `CHECK (current_uses >= 0)`

- `ck_invitation_links_expires_after_created`
- `CHECK (expires_at > created_at)`

- `ck_invitation_links_max_uses_allowed`
- `CHECK (max_uses = ANY (ARRAY[1, 5, 10, 25, 50]))`

- `ck_invitation_links_status_allowed`
- `CHECK (link_status::text = ANY (ARRAY[
    'active'::character varying,
    'expired'::character varying,
    'revoked'::character varying,
    'exhausted'::character varying
]))`

Foreign keys:

- `fk_invitation_links_creator_id_users`
  - `creator_id` → `users(id)` ON DELETE CASCADE

- `fk_invitation_links_revoked_by_users`
  - `revoked_by` → `users(id)` ON DELETE SET NULL

Referenced by:

- `invitation_acceptances.invitation_link_id`
  → `invitation_links(id)` ON DELETE CASCADE

Access method:

- `heap`

## Notes

- Current DB-level allowed values for `link_status`: `active`, `expired`, `revoked`, `exhausted`.
- Current DB-level allowed values for `max_uses`: `1`, `5`, `10`, `25`, `50`.
- No triggers exist.

---

# Table `invitation_acceptances`

## Physical definition

Columns:

- `id` → `uuid` → NOT NULL → DB default: `gen_random_uuid()`
- `invitation_link_id` → `uuid` → NOT NULL
- `user_id` → `uuid` → NOT NULL
- `accepted_via` → `character varying(16)` → NOT NULL
- `accepted_at` → `timestamp with time zone` → NOT NULL → DB default: `now()`

Indexes:

- `pk_invitation_acceptances` → PRIMARY KEY (`id`)
- `ix_invitation_acceptances_invitation_link_id` → (`invitation_link_id`)
- `ix_invitation_acceptances_user_id` → (`user_id`)
- `ux_invitation_acceptances_link_user` → UNIQUE (`invitation_link_id`, `user_id`)

Check constraints:

- `ck_invitation_acceptances_accepted_via_allowed`
- `CHECK (accepted_via::text = ANY (ARRAY[
    'web'::character varying,
    'email'::character varying,
    'link'::character varying
]))`

Foreign keys:

- `fk_invitation_acceptances_invitation_link_id_invitation_links`
  - `invitation_link_id` → `invitation_links(id)` ON DELETE CASCADE

- `fk_invitation_acceptances_user_id_users`
  - `user_id` → `users(id)` ON DELETE CASCADE

Access method:

- `heap`

## Notes

- Current DB-level allowed values for `accepted_via`: `web`, `email`, `link`.
- The unique constraint guarantees one acceptance per `(invitation_link_id, user_id)` pair.
- No triggers exist.

---

# Table `contacts`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → DB default `gen_random_uuid()`
- `user_low_id` → `uuid` → `NOT NULL` → no physical DB default
- `user_high_id` → `uuid` → `NOT NULL` → no physical DB default
- `current_status` → `character varying(32)` → `NOT NULL` → no physical DB default
- `initial_connection_source` → `character varying(64)` → `NOT NULL` → no physical DB default
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`
- `connected_at` → `timestamp with time zone` → `NOT NULL` → no physical DB default
- `disconnected_at` → `timestamp with time zone` → nullable → no physical DB default
- `updated_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`

Constraints:
- `pk_contacts` → PRIMARY KEY (`id`)
- `ck_contacts_current_status` → CHECK (`current_status::text = ANY (ARRAY['active'::character varying, 'inactive'::character varying]::text[]))`
- `ck_contacts_initial_connection_source` → CHECK (`initial_connection_source::text = ANY (ARRAY['contact_request'::character varying, 'invitation_link'::character varying]::text[]))`
- `ck_contacts_status_timestamp_consistency` → CHECK (`current_status::text = 'active'::text AND disconnected_at IS NULL OR current_status::text = 'inactive'::text AND disconnected_at IS NOT NULL AND disconnected_at >= connected_at`)
- `ck_contacts_user_low_id_lt_user_high_id` → CHECK (`user_low_id < user_high_id`)
- `fk_contacts_user_high_id_users` → FOREIGN KEY (`user_high_id`) REFERENCES `users(id)`
- `fk_contacts_user_low_id_users` → FOREIGN KEY (`user_low_id`) REFERENCES `users(id)`
- `ux_contacts_user_low_id_user_high_id` → UNIQUE (`user_low_id`, `user_high_id`)

Indexes:
- `pk_contacts` → unique btree (`id`)
- `ix_contacts_current_status` → btree (`current_status`)
- `ix_contacts_current_status_user_high_id` → btree (`current_status`, `user_high_id`)
- `ix_contacts_current_status_user_low_id` → btree (`current_status`, `user_low_id`)
- `ix_contacts_user_high_id` → btree (`user_high_id`)
- `ix_contacts_user_low_id` → btree (`user_low_id`)
- `ux_contacts_user_low_id_user_high_id` → unique btree (`user_low_id`, `user_high_id`)

Referenced by:
- `contact_events.contact_id` → `contacts(id)` ON DELETE CASCADE

Access method:
- `heap`

## Notes
- `contacts` stores a symmetric relationship in one canonical row.
- Current DB-level allowed values for `current_status`: `active`, `inactive`.
- Current DB-level allowed values for `initial_connection_source`: `contact_request`, `invitation_link`.
- `updated_at` has a DB default but there is no trigger to maintain it automatically on update.

---

# Table `contact_events`

## Physical definition

Columns:
- `id` → `uuid` → `NOT NULL` → DB default `gen_random_uuid()`
- `contact_id` → `uuid` → `NOT NULL` → no physical DB default
- `event_type` → `character varying(32)` → `NOT NULL` → no physical DB default
- `event_at` → `timestamp with time zone` → `NOT NULL` → no physical DB default
- `actor_user_id` → `uuid` → nullable → no physical DB default
- `source` → `character varying(64)` → `NOT NULL` → no physical DB default
- `created_at` → `timestamp with time zone` → `NOT NULL` → DB default `now()`

Constraints:
- `pk_contact_events` → PRIMARY KEY (`id`)
- `ck_contact_events_event_type` → CHECK (`event_type::text = ANY (ARRAY['connected'::character varying, 'disconnected'::character varying]::text[]))`
- `ck_contact_events_event_type_source_consistency` → CHECK (`event_type::text = 'connected'::text AND (source::text = ANY (ARRAY['contact_request_acceptance'::character varying, 'invitation_link_acceptance'::character varying, 'manual_reconnect'::character varying]::text[])) OR event_type::text = 'disconnected'::text AND source::text = 'manual_disconnect'::text`)
- `ck_contact_events_source` → CHECK (`source::text = ANY (ARRAY['contact_request_acceptance'::character varying, 'invitation_link_acceptance'::character varying, 'manual_disconnect'::character varying, 'manual_reconnect'::character varying]::text[]))`
- `fk_contact_events_actor_user_id_users` → FOREIGN KEY (`actor_user_id`) REFERENCES `users(id)` ON DELETE SET NULL
- `fk_contact_events_contact_id_contacts` → FOREIGN KEY (`contact_id`) REFERENCES `contacts(id)` ON DELETE CASCADE

Indexes:
- `pk_contact_events` → unique btree (`id`)
- `ix_contact_events_actor_user_id` → btree (`actor_user_id`)
- `ix_contact_events_contact_id` → btree (`contact_id`)
- `ix_contact_events_contact_id_event_at` → btree (`contact_id`, `event_at`)
- `ix_contact_events_event_at` → btree (`event_at`)

Access method:
- `heap`

## Notes
- Current DB-level allowed values for `event_type`: `connected`, `disconnected`.
- Current DB-level allowed values for `source`:
  - `contact_request_acceptance`
  - `invitation_link_acceptance`
  - `manual_disconnect`
  - `manual_reconnect`
- DB enforces `event_type ↔ source` consistency.
- No triggers exist.

---

## Practical interpretation notes

1. **The real database state overrides old schema documents.**  
   This file is intended to be the safe reference when older docs conflict with PostgreSQL.

2. **Logical ownership is per microservice, but the physical schema is shared.**  
   Isolation is enforced through:
   - service-specific Alembic version tables
   - `include_object`
   - migration metadata isolation
   - runtime discipline

3. **The contacts domain is intentionally divided into distinct persistence layers.**
    - `contact_requests` represents the legacy request-based acquisition flow and is currently reserved/deprioritized for the MVP.
    - `invitation_links` is the active Invitation MVP acquisition mechanism.
    - `invitation_acceptances` stores accepted invitation history and guarantees idempotency.
    - `contacts` stores the effective relationship snapshot.
    - `contact_events` stores immutable relationship history.

4. **Do not assume product concepts that are not physically present.**
   In the current verified schema:
   - no `social_paused`
   - no `private_mode`

5. **No application-side defaults are inferred here.**
   This document records verified PostgreSQL defaults only.

6. **This document should be regenerated from PostgreSQL after future migrations.**

---

This verification supersedes the previous verified snapshot by including the Invitation MVP schema (`invitation_links`, `invitation_acceptances`) and the current contacts-service Alembic revision (`8460e09ba085`).