# Third-party components

MineProt's application code remains under the repository's MIT LICENSE.
Dependencies retain their own licenses; that MIT grant does not relicense them.

The pinned direct Python dependencies are listed in `requirements.txt`:

| Component | License | Upstream |
| --- | --- | --- |
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| Jinja2 | BSD-3-Clause | https://github.com/pallets/jinja |
| HTTPX | BSD-3-Clause | https://github.com/encode/httpx |
| python-multipart | Apache-2.0 | https://github.com/Kludex/python-multipart |
| Gemmi | MPL-2.0 | https://github.com/project-gemmi/gemmi |
| Foldcomp 1.0.0 | MIT | https://github.com/steineggerlab/foldcomp/tree/v1.0.0 |

Gemmi is used as an unmodified Python dependency, without copying its source
into MIT application files. License text: https://www.mozilla.org/MPL/2.0/.
The corresponding upstream source for Gemmi 0.7.1 is available as the source
archive on https://pypi.org/project/gemmi/0.7.1/#files and in the upstream
repository at https://github.com/project-gemmi/gemmi/tree/v0.7.1.
Recipients of a distributed image can obtain that source from these locations.
Retain package copyright/license files and provide the source for any modified
MPL-covered files if distributing a modified Gemmi build.

Retained components have separate terms:

- US-align: https://github.com/pylelab/USalign/blob/master/LICENSE.
  Keep upstream notices and reference information when distributing. The local
  archive is intentionally retained; record its source revision when replacing it.
- PDBe Mol*: https://github.com/molstar/pdbe-molstar. Search uses version 3.12.0
  (Apache-2.0), vendored in `assets/vendor/pdbe-molstar-3.12.0/` with its LICENSE
  and bundled dependency notices. The original 1.2.1 bundle remains for Salign.
  Both versions include their matching, unmodified light stylesheet. The 1.2.1
  light stylesheet comes from
  https://www.ebi.ac.uk/pdbe/pdb-component-library/css/pdbe-molstar-light-1.2.1.css.
- Highcharts 10.3.1: https://www.highcharts.com/license. It is not MIT. Review the
  license applicable to that version and the deployment's existing authorization,
  especially for commercial use and redistribution. No new Highcharts rights
  are granted by this migration. Its existing script header is retained.
- Elasticsearch 7.12.1: https://www.elastic.co/pricing/faq/licensing. Its default
  distribution is subject to Elastic License terms, not MIT. The existing
  Elasticsearch image, IK plugin and data format are retained.
- Python and Debian base-image packages retain their respective licenses.

Foldcomp is used as an unmodified Python package from PyPI, not as a bundled
standalone executable. Version 1.0.0 uses the MIT license. Preserve its license
and upstream third-party notices when redistributing the package or image:
https://github.com/steineggerlab/foldcomp/blob/v1.0.0/LICENSE.txt and
https://github.com/steineggerlab/foldcomp/blob/v1.0.0/THIRD-PARTY-NOTICES.md.

This file identifies the main components and does not replace their license
texts, package metadata, or a review of the complete image's transitive
components. Preserve upstream notices when publishing source or images.
