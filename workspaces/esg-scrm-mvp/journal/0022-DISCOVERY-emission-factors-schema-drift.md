# DISCOVERY: emission_factors table missing table_or_equation column

## Finding

The `emission_factors` table in both `schema.sql` and `schema_pg.sql` is missing the `table_or_equation TEXT` column required by `specs/framework-mapping.md § Emission Factor Sources`. This means:

1. The column cannot be seeded (seed data cannot target a non-existent column)
2. Any code expecting `table_or_equation` gets a KeyError at runtime

## Evidence

- Spec says: `id, category, factor_value, unit, source (GHG Protocol/IPCC/EPA/DEFRA/IEA), region, year, table_or_equation (TEXT), is_active, org_id`
- schema.sql line ~210-222: NO `table_or_equation` column
- schema_pg.sql line ~209-221: NO `table_or_equation` column

## Fix required

Add `table_or_equation TEXT` to `emission_factors` in both schema.sql and schema_pg.sql.
