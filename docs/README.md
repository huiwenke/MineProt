# MineProt documentation

This directory holds the maintained user manuals and Wiki source pages.
Examples follow the current Python Web service and Python 3.12+ toolkit.

| Page | Contents |
| --- | --- |
| [Home](Home.md) | Wiki introduction. |
| [Deployment manual](Deployment-manual.md) | Setup, production/local management, storage, configuration and maintenance. |
| [Toolkit manual](Toolkit-manual.md) | Single imports, ColabFold monomers, AlphaFold3 complexes, batch tools and MSA Neff. Includes the existing Plugins section. |
| [API manual](API-manual.md) | HTTP contracts, limits, imports, file access, Salign and PAE. |

## Where documentation belongs

Maintain detailed user instructions here, with relative links between manuals.
Keep page filenames stable when publishing these sources to the GitHub Wiki.

Some Markdown belongs beside its code or assets:

- Root `README.md`: project overview, quick start, citation and links to manuals.
- `toolkit/README.md`: package installation and contributor checks. It is also
  the package description referenced by `toolkit/pyproject.toml` and included
  in source distributions, so it stays in the package directory.
- `web/DEPLOYMENT.md`: a short pointer to the canonical deployment manual,
  retaining the old documentation entrypoint.
- `web/THIRD_PARTY.md`: dependency licenses and source notices, retained beside
  the Web service and included when Web sources are copied into its image.
- `web/assets/vendor/pdbe-molstar-3.12.0/README.md`: bundle origins, version and
  integrity information, retained beside the unmodified vendored assets.

Do not copy these legal/provenance records into parallel maintained pages.
User-facing behavior belongs in the manuals; installation/development metadata
and third-party notices remain with their components.
