# Maintain the you_only_live_twice package

The distribution at this revision is `you_only_live_twice` 0.1.0, with
Python compatibility `>=3.11`. This checkout selects Python 3.15 in [`.python-version`](../.python-version).
[Project metadata](../pyproject.toml) declares the package and compatibility.
[The lockfile](../uv.lock) records resolved dependency versions and sources.

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
