# companies/ — one settings file per alcohol-beverage company

Each file here is a **company profile**: its own profile/signature, brand
portfolio, party master, MTD file prefix, and Excel schema mapping. The active
company is stored in `active.txt` (a slug). The GUI's **🏢 Company** tab
creates, switches, and deletes companies; the CLI accepts `--company <slug>`.

| File | Purpose |
|---|---|
| `active.txt` | slug of the currently selected company |
| `<slug>.json` | one company's full settings (gitignored — your data) |
| `sample.json.example` | the shape to copy when onboarding a company by hand |

## First run

No `companies/` directory? The tool seeds a **Default Company** from your
legacy `user_settings.json` (profile + brands) and selects it — existing users
see zero change. New users start from the Company tab.

## The schema mapping (multiple MTD file types)

Each company stores how *its* MTD dumps and party master are laid out:

```json
"schema": {
  "sales": {"sheet": "DATA", "header_row": 4,
            "columns": {"depot": "Name Of Depot", "syndicate": "SYNDICATE NAME",
                        "vendor": "VENDOR_NAME", "total": "Total"}},
  "party": {"sheet": null, "header_row": 0,
            "columns": {"party": "PARTY", "phone": "PHONE", "send": "SEND",
                        "priority": "PRIORITY", "total_target": "TOTAL_TARGET"}}
}
```

The first time you load a sales dump for a company, the layout is
**auto-detected** (`schema.py` — fuzzy synonym matching over the first sheets
and header rows) and confirmed in a dialog, then stored. After that, every file
of that type loads silently. Different companies can use completely different
sheet names, header rows, and column spellings.

## Onboarding a new company (the 4-step newbie path)

1. **🏢 Company → ➕ New** → type the agency name.
2. **▶ Run → Browse… → Load File** → confirm the auto-detected sales mapping.
3. Confirm the party master mapping (party/phone/send/priority/target).
4. **🍾 Brands → ➕ Add** each brand with its target/actual columns, then run.

Everything else (profile, brands, mapping) is stored per company automatically.
