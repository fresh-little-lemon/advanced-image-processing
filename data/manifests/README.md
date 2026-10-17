# Dataset metadata only

Set MULTIFOCUS_DATA_ROOT to the private local data root. Paths in these public manifests are relative to it. No images, contact sheets, archives or Git objects are included. Obtain data from the upstream repositories pinned in the manifest and preserve their terms and attribution.

MFI-WHU: download MFI-WHU.rar from commit 6071f2909f5563ccb9bcd71317f5102eefe13e6f of https://github.com/HaoZhang1018/MFI-WHU ; extract so that MFI-WHU/MFI-WHU/source_1/1.jpg exists relative to data root. The corresponding source_2 and full_clear filenames match by integer ID.

MFFW2: fetch input/mffw_01 through input/mffw_13 from commit f0f0e0725e7d82fe91aa30eb6296d8241d26e4c9 of https://github.com/xingchenzhang/MFIF ; copy each original file unchanged to MFFW2/01 through MFFW2/13. Do not rename A/B filenames.

Validate each file against its SHA-256 before execution. These manifests freeze the initial scene-level split; see docs/data_protocol.md for remaining semantic/session-independence audit limits.

## Reproduce acquisition

From the project root, choose a directory outside this repository:

```sh
python3 scripts/fetch_multifocus_data.py --data-root /path/to/local/multifocus_data
python3 scripts/fetch_multifocus_data.py --data-root /path/to/local/multifocus_data --verify-only
```

Requirements: Python 3, git, and libarchive on Linux (alternatively bsdtar or 7z). No fusion algorithm or benchmark is executed by this script. The 13 MFFW2 external-test scenes remain reserved until the final configuration is frozen. The downloader refuses to overwrite an existing dataset; interrupted partial output can be retained for diagnosis and a fresh destination used for retry.
