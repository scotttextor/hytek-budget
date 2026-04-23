-- HYTEK Budget — Migration 14: user-editable day templates
--
-- Moves Day Templates from the hardcoded src/lib/day-templates.ts constant
-- into two database tables so HYTEK can add / edit / delete templates from
-- the Setup UI without a code deploy.
--
-- Seeds the 4 existing hardcoded templates as starting data so nothing
-- breaks between apply + UI deploy. The hytek-install app has a fallback
-- to the static constant if the DB query returns empty, so the order of
-- (apply migration) vs (deploy UI) doesn't matter — both states work.

BEGIN;

-- =============================================================================
-- 1. install_day_templates — one row per template
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.install_day_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text UNIQUE NOT NULL,            -- stable identifier, matches the old TS id field
  name text NOT NULL,
  emoji text,
  description text,
  sort_order int NOT NULL DEFAULT 0,
  active boolean NOT NULL DEFAULT true,
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_install_day_templates_active
  ON public.install_day_templates (active, sort_order)
  WHERE active = true;

-- =============================================================================
-- 2. install_day_template_items — ordered items per template
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.install_day_template_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id uuid NOT NULL REFERENCES public.install_day_templates(id) ON DELETE CASCADE,
  category text NOT NULL,               -- matches budget item category (cranage, travel, etc.)
  label text NOT NULL,                  -- what supervisor sees in the picker
  default_hours numeric,                -- null = qty-type item where hours don't apply
  default_notes text,                   -- pre-fill notes (optional)
  sort_order int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_install_day_template_items_template
  ON public.install_day_template_items (template_id, sort_order);

-- =============================================================================
-- 3. RLS — admin+supervisor manage, anon can read (for mobile /site app)
-- =============================================================================
ALTER TABLE public.install_day_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.install_day_template_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "staff manages day templates" ON public.install_day_templates;
CREATE POLICY "staff manages day templates"
  ON public.install_day_templates
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor')))
  WITH CHECK (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor')));

DROP POLICY IF EXISTS "anon reads active day templates" ON public.install_day_templates;
CREATE POLICY "anon reads active day templates"
  ON public.install_day_templates
  FOR SELECT TO anon
  USING (active = true);

DROP POLICY IF EXISTS "staff manages day template items" ON public.install_day_template_items;
CREATE POLICY "staff manages day template items"
  ON public.install_day_template_items
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor')))
  WITH CHECK (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor')));

DROP POLICY IF EXISTS "anon reads day template items" ON public.install_day_template_items;
CREATE POLICY "anon reads day template items"
  ON public.install_day_template_items
  FOR SELECT TO anon
  USING (true);

-- =============================================================================
-- 4. Seed the 4 existing hardcoded templates
-- =============================================================================
-- Uses ON CONFLICT on slug so re-running the migration is idempotent and
-- doesn't overwrite user edits. Once a template exists in DB, the TS
-- constant becomes display-only fallback.

INSERT INTO public.install_day_templates (slug, name, emoji, description, sort_order)
VALUES
  ('crane-lift-day',          'Crane Lift Day',         '🏗',  '3 cranage claims pre-bundled — supervisor only enters hours.',  1),
  ('form-12-day',             'Form 12 Inspection Day', '📋', '2 claims — Form 12 Inspection + Travel.',                        2),
  ('travel-day',              'Overnight Travel Day',    '🚗', '3 claims — accommodation, food allowance, travel.',              3),
  ('shaftliner-install-day',  'Shaftliner Install Day',  '🪚', 'Per-unit shaftliner + EWP half-day.',                            4)
ON CONFLICT (slug) DO NOTHING;

-- Items — only insert if the template exists AND doesn't already have items.
-- Using a CTE per template to get the FK ids.

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'crane-lift-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'cranage', 'Wet Crane Hire', 8, 1 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items WHERE template_id = t.id);

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'crane-lift-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'cranage', 'Extra Rigger', 8, 2 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items i WHERE i.template_id = t.id AND i.label = 'Extra Rigger');

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'crane-lift-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'cranage', 'Extra Dogman', 8, 3 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items i WHERE i.template_id = t.id AND i.label = 'Extra Dogman');

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'form-12-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'form_12', 'Form 12 Inspection', 1, 1 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items WHERE template_id = t.id);

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'form-12-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'travel', 'Travel (km)', NULL, 2 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items i WHERE i.template_id = t.id AND i.label = 'Travel (km)');

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'travel-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'accommodation', 'Accommodation (1 night)', 1, 1 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items WHERE template_id = t.id);

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'travel-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'food', 'Food allowance (1 day)', 1, 2 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items i WHERE i.template_id = t.id AND i.label = 'Food allowance (1 day)');

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'travel-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'travel', 'Travel (km)', NULL, 3 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items i WHERE i.template_id = t.id AND i.label = 'Travel (km)');

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'shaftliner-install-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'shaftliner', 'Shaftliner Install (sqm)', NULL, 1 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items WHERE template_id = t.id);

WITH t AS (SELECT id FROM public.install_day_templates WHERE slug = 'shaftliner-install-day')
INSERT INTO public.install_day_template_items (template_id, category, label, default_hours, sort_order)
SELECT t.id, 'ewp', 'EWP + Travel (half day)', 4, 2 FROM t
WHERE NOT EXISTS (SELECT 1 FROM public.install_day_template_items i WHERE i.template_id = t.id AND i.label = 'EWP + Travel (half day)');

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY
-- =============================================================================
-- Expect 4 templates with 10 total items (3 + 2 + 3 + 2):
SELECT
  t.slug,
  t.name,
  t.emoji,
  COUNT(i.id) AS item_count
FROM public.install_day_templates t
LEFT JOIN public.install_day_template_items i ON i.template_id = t.id
GROUP BY t.id, t.slug, t.name, t.emoji, t.sort_order
ORDER BY t.sort_order;

-- =============================================================================
-- ROLLBACK (uncomment to undo — destroys any user-added templates)
-- =============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS public.install_day_template_items;
-- DROP TABLE IF EXISTS public.install_day_templates;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
