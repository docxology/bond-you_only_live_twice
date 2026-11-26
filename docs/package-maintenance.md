# Maintain the you_only_live_twice package

[Project metadata](../pyproject.toml) declares the package identity and Python
compatibility (`>=3.11`). [The lockfile](../uv.lock) records resolved
dependencies. Compare these two files when checking package metadata.

## Dependency provenance

- `bond-api` resolves to the vendored copy at `vendor/bond-api`. Its
  [provenance record](../vendor/bond-api/PROVENANCE.json) identifies the
  source revision and records content digests.

## Citation and release records

The repository records package metadata in:

- [Citation metadata](../CITATION.cff)
- [Zenodo metadata](../.zenodo.json)

Check the
version fields that are present against the project metadata. A repository
metadata file does not establish that a release has been deposited.

For a documentation review, run `git diff --check` and verify the relative
links added by the change against the tracked checkout. These checks
provide evidence about the documentation and package records.
