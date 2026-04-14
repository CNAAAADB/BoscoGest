-- ============================================================
-- seed_salesian_entities.sql
--
-- Seeds the full Salesian entity hierarchy:
--   1 Confederación (level 2, child of superentity)
--   6 Federaciones (level 3)
--   64 Asociaciones Locales (level 4)
--
-- For each entity: creates entity, associates admin+socio roles,
-- and creates a superadmin membership for user id=1.
--
-- Usage:
--   Local (docker):
--     docker compose exec -T db psql -U postgres -d boscogest < scripts/seed_salesian_entities.sql
--
--   Production (EC2):
--     sudo docker compose exec -T back psql "<DATABASE_URL_sin_psycopg2>" < scripts/seed_salesian_entities.sql
--
-- Idempotent: skips duplicates via ON CONFLICT / WHERE NOT EXISTS.
-- ============================================================

BEGIN;

DO $$
DECLARE
    v_superentity_id      INT;
    v_superadmin_role_id  INT;
    v_admin_role_id       INT;
    v_socio_role_id       INT;
    v_confederacion_id    INT;
    v_federacion_id       INT;
    v_entity_id           INT;
BEGIN
    -- ── Resolve prerequisites ───────────────────────────────

    SELECT id INTO v_superentity_id
      FROM entities WHERE level = 1 AND is_active = true LIMIT 1;

    IF v_superentity_id IS NULL THEN
        RAISE EXCEPTION 'No level-1 superentity found. Run initial seeder first.';
    END IF;

    SELECT id INTO v_superadmin_role_id FROM roles WHERE name = 'superadmin' AND is_active = true;
    SELECT id INTO v_admin_role_id FROM roles WHERE name = 'admin' AND is_active = true;
    SELECT id INTO v_socio_role_id FROM roles WHERE name = 'socio' AND is_active = true;

    IF v_superadmin_role_id IS NULL OR v_admin_role_id IS NULL OR v_socio_role_id IS NULL THEN
        RAISE EXCEPTION 'superadmin, admin and/or socio roles not found. Run initial seeder first.';
    END IF;

    -- ════════════════════════════════════════════════════════
    -- 1. CONFEDERACIÓN (level 2)
    -- ════════════════════════════════════════════════════════

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('Confederación Don Bosco', 2, v_superentity_id, true)
    ON CONFLICT (name) DO NOTHING;

    SELECT id INTO v_confederacion_id FROM entities WHERE name = 'Confederación Don Bosco';

    INSERT INTO entity_roles (entity_id, role_id)
    SELECT v_confederacion_id, v_admin_role_id
    WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_confederacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id)
    SELECT v_confederacion_id, v_socio_role_id
    WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_confederacion_id AND role_id = v_socio_role_id);

    INSERT INTO memberships (user_id, role_id, entity_id, is_active)
    SELECT 1, v_superadmin_role_id, v_confederacion_id, true
    WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_confederacion_id);

    -- ════════════════════════════════════════════════════════
    -- 2. FEDERACIONES (level 3) + LOCALES (level 4)
    -- ════════════════════════════════════════════════════════

    -- ── Mare de Déu de la Mercè ─────────────────────────────

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('Mare de Déu de la Mercè', 3, v_confederacion_id, true)
    ON CONFLICT (name) DO NOTHING;
    SELECT id INTO v_federacion_id FROM entities WHERE name = 'Mare de Déu de la Mercè';

    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_socio_role_id);
    INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_federacion_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_federacion_id);

    FOR v_entity_id IN
        INSERT INTO entities (name, level, parent_id, is_active) VALUES
            ('Horta', 4, v_federacion_id, true),
            ('Sarrià', 4, v_federacion_id, true),
            ('Monzón', 4, v_federacion_id, true),
            ('Ciutadella', 4, v_federacion_id, true),
            ('Gerona', 4, v_federacion_id, true),
            ('Huesca', 4, v_federacion_id, true),
            ('Mataró', 4, v_federacion_id, true)
        ON CONFLICT (name) DO NOTHING RETURNING id
    LOOP
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_admin_role_id);
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_socio_role_id);
        INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_entity_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_entity_id);
    END LOOP;

    -- ── San Francisco Javier ────────────────────────────────

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('San Francisco Javier', 3, v_confederacion_id, true)
    ON CONFLICT (name) DO NOTHING;
    SELECT id INTO v_federacion_id FROM entities WHERE name = 'San Francisco Javier';

    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_socio_role_id);
    INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_federacion_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_federacion_id);

    FOR v_entity_id IN
        INSERT INTO entities (name, level, parent_id, is_active) VALUES
            ('Barakaldo', 4, v_federacion_id, true),
            ('Deusto', 4, v_federacion_id, true),
            ('Burgos', 4, v_federacion_id, true),
            ('Pamplona', 4, v_federacion_id, true),
            ('Santander', 4, v_federacion_id, true)
        ON CONFLICT (name) DO NOTHING RETURNING id
    LOOP
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_admin_role_id);
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_socio_role_id);
        INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_entity_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_entity_id);
    END LOOP;

    -- ── Camino de Santiago ──────────────────────────────────

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('Camino de Santiago', 3, v_confederacion_id, true)
    ON CONFLICT (name) DO NOTHING;
    SELECT id INTO v_federacion_id FROM entities WHERE name = 'Camino de Santiago';

    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_socio_role_id);
    INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_federacion_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_federacion_id);

    FOR v_entity_id IN
        INSERT INTO entities (name, level, parent_id, is_active) VALUES
            ('Astudillo', 4, v_federacion_id, true),
            ('A Coruña Don Bosco', 4, v_federacion_id, true),
            ('A Coruña Calvo Sotelo', 4, v_federacion_id, true),
            ('La Robla', 4, v_federacion_id, true),
            ('León', 4, v_federacion_id, true),
            ('Orense', 4, v_federacion_id, true),
            ('Oviedo', 4, v_federacion_id, true),
            ('Palencia', 4, v_federacion_id, true),
            ('Valladolid', 4, v_federacion_id, true),
            ('Vigo María Auxiliadora', 4, v_federacion_id, true),
            ('Hogar San Roque - Caixanova', 4, v_federacion_id, true),
            ('Allariz', 4, v_federacion_id, true),
            ('Zamora', 4, v_federacion_id, true),
            ('Santiago de Compostela', 4, v_federacion_id, true)
        ON CONFLICT (name) DO NOTHING RETURNING id
    LOOP
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_admin_role_id);
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_socio_role_id);
        INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_entity_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_entity_id);
    END LOOP;

    -- ── Felipe Rinaldi ──────────────────────────────────────

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('Felipe Rinaldi', 3, v_confederacion_id, true)
    ON CONFLICT (name) DO NOTHING;
    SELECT id INTO v_federacion_id FROM entities WHERE name = 'Felipe Rinaldi';

    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_socio_role_id);
    INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_federacion_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_federacion_id);

    FOR v_entity_id IN
        INSERT INTO entities (name, level, parent_id, is_active) VALUES
            ('Atocha', 4, v_federacion_id, true),
            ('Carabanchel', 4, v_federacion_id, true),
            ('Moratalaz', 4, v_federacion_id, true),
            ('Paseo de Extremadura', 4, v_federacion_id, true),
            ('Plasencia', 4, v_federacion_id, true),
            ('Puertollano', 4, v_federacion_id, true),
            ('Salamanca María Aux.', 4, v_federacion_id, true),
            ('Salamanca Pizarrales', 4, v_federacion_id, true),
            ('Guadalajara', 4, v_federacion_id, true),
            ('Parla', 4, v_federacion_id, true),
            ('Alcalá de Henares', 4, v_federacion_id, true)
        ON CONFLICT (name) DO NOTHING RETURNING id
    LOOP
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_admin_role_id);
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_socio_role_id);
        INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_entity_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_entity_id);
    END LOOP;

    -- ── Sur - María Auxiliadora ─────────────────────────────

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('Sur - María Auxiliadora', 3, v_confederacion_id, true)
    ON CONFLICT (name) DO NOTHING;
    SELECT id INTO v_federacion_id FROM entities WHERE name = 'Sur - María Auxiliadora';

    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_socio_role_id);
    INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_federacion_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_federacion_id);

    FOR v_entity_id IN
        INSERT INTO entities (name, level, parent_id, is_active) VALUES
            ('Algeciras', 4, v_federacion_id, true),
            ('Cádiz', 4, v_federacion_id, true),
            ('Córdoba', 4, v_federacion_id, true),
            ('Granada', 4, v_federacion_id, true),
            ('Las Palmas', 4, v_federacion_id, true),
            ('Carmona', 4, v_federacion_id, true),
            ('Málaga', 4, v_federacion_id, true),
            ('Montilla', 4, v_federacion_id, true),
            ('Pozoblanco', 4, v_federacion_id, true),
            ('San Fernando', 4, v_federacion_id, true),
            ('La Orotava', 4, v_federacion_id, true),
            ('Trinidad', 4, v_federacion_id, true),
            ('Úbeda', 4, v_federacion_id, true),
            ('Morón', 4, v_federacion_id, true),
            ('La Línea de la Concepción', 4, v_federacion_id, true),
            ('Santo Domingo Savio-Vivero', 4, v_federacion_id, true),
            ('Linares Baja', 4, v_federacion_id, true),
            ('La Cuesta', 4, v_federacion_id, true),
            ('Palma del Río', 4, v_federacion_id, true),
            ('Mérida', 4, v_federacion_id, true)
        ON CONFLICT (name) DO NOTHING RETURNING id
    LOOP
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_admin_role_id);
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_socio_role_id);
        INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_entity_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_entity_id);
    END LOOP;

    -- ── Carlos Gastini ──────────────────────────────────────

    INSERT INTO entities (name, level, parent_id, is_active)
    VALUES ('Carlos Gastini', 3, v_confederacion_id, true)
    ON CONFLICT (name) DO NOTHING;
    SELECT id INTO v_federacion_id FROM entities WHERE name = 'Carlos Gastini';

    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_admin_role_id);
    INSERT INTO entity_roles (entity_id, role_id) SELECT v_federacion_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_federacion_id AND role_id = v_socio_role_id);
    INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_federacion_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_federacion_id);

    FOR v_entity_id IN
        INSERT INTO entities (name, level, parent_id, is_active) VALUES
            ('Alcoy San Vicente Ferrer', 4, v_federacion_id, true),
            ('Alicante María Auxiliadora', 4, v_federacion_id, true),
            ('Elche', 4, v_federacion_id, true),
            ('San Antonio (Sagunto)', 4, v_federacion_id, true),
            ('Zaragoza', 4, v_federacion_id, true),
            ('Cabezo de Torres', 4, v_federacion_id, true),
            ('Villena', 4, v_federacion_id, true)
        ON CONFLICT (name) DO NOTHING RETURNING id
    LOOP
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_admin_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_admin_role_id);
        INSERT INTO entity_roles (entity_id, role_id) SELECT v_entity_id, v_socio_role_id WHERE NOT EXISTS (SELECT 1 FROM entity_roles WHERE entity_id = v_entity_id AND role_id = v_socio_role_id);
        INSERT INTO memberships (user_id, role_id, entity_id, is_active) SELECT 1, v_superadmin_role_id, v_entity_id, true WHERE NOT EXISTS (SELECT 1 FROM memberships WHERE user_id = 1 AND entity_id = v_entity_id);
    END LOOP;

    -- ── Summary ─────────────────────────────────────────────
    RAISE NOTICE 'Seed complete: 1 Confederación + 6 Federaciones + 64 Locales + memberships for user 1';
END $$;

COMMIT;
