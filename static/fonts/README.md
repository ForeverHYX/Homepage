# Self-hosted fonts

These WOFF2 files are the same Latin/subset assets previously loaded from
Google Fonts at runtime. They are checked in so typography is deterministic,
font discovery starts with the HTML response, and the site has no runtime
dependency on Google infrastructure.

Edit declarations in `src/fonts.css`; `fonts.css` is generated with content
fingerprints by `scripts/build_frontend.py`. The complete Source Sans 3 and
Source Serif 4 variable inputs live under `assets/fonts/vendor/`, while the
runtime copies are restricted to the axes listed below.

| Family | Upstream version | Subset |
| --- | --- | --- |
| Source Sans 3 | v19 | Latin, weights 400–600 |
| Source Serif 4 | v14 | Latin, optical-size variable, weights 400–600 |
| Dancing Script | v29 | Latin, weight 500 |
| Zhi Mang Xing | v19 | `洪奕迅` only |
| JetBrains Mono | v24 | Latin, weights 400–500 |
| Marcellus | v14 | Latin, weight 400 |

All six families are distributed under the [SIL Open Font License 1.1](https://openfontlicense.org/).
The source families and their copyright/license metadata are maintained in the
[Google Fonts repository](https://github.com/google/fonts/tree/main/ofl).
