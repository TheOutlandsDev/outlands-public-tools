# Run the Offline Platform Navigation and Workspace Reporter

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\platform-navigation-workspace-reporter-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. The reporter uses Python's standard library.

Windows PowerShell

```powershell
python platform_navigation.py examples/fictional-registry.json
python platform_navigation.py examples/fictional-registry.json --environment production
python platform_navigation.py examples/fictional-registry.json --workspace demo-studio --environment production
```

Ubuntu

```bash
python3 platform_navigation.py examples/fictional-registry.json
python3 platform_navigation.py examples/fictional-registry.json --environment production
python3 platform_navigation.py examples/fictional-registry.json --workspace demo-studio --environment production
```

The default development menu has six groups. The production menu has five because the development-only group is hidden. The fictional Studio workspace has six resources in both environments, with four primary and two reference links.

## Registry and output

Use the fictional registry as a starting point. Save it as UTF-8 JSON up to 1 MiB. It contains navigation_groups, modules, and external_navigation_items.

- Each navigation group declares its name, positive order, and environments.
- Each module declares a unique module_id, a lifecycle, and a navigation object. The navigation object identifies its group, matching group_order, and items.
- Menu items declare label, href, description, positive order, and environments. Internal links use local paths. External links use HTTP or HTTPS URLs and also name their menu group.
- A module may declare a workspace with a unique workspace_id, workspace_type, label, description, and resources. Resources use the same fields as internal menu items and declare presentation as PRIMARY or REFERENCE.

Use development and production as environment names, CURRENT_EMBEDDED, CURRENT_EMBEDDED_READ_ONLY, or PLANNED_DISABLED as lifecycle values, and PRODUCTION_LAB, ENGINEERING_LAB, or SHARED_OPERATION as workspace types.

The menu output includes each visible group in order, with links sorted by order and then label. It marks internal anchors, external links, and links for planned modules. The workspace report includes resources, primary_resources, and reference_resources, each ordered by order and label. Menu groups and workspace resource visibility follow their respective declarations.

The CLI reads the registry and writes its report to standard output. Success exits 0. An invalid registry, unsupported environment, or unknown workspace exits 2.

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
