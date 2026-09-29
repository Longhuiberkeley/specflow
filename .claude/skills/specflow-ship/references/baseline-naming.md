# Baseline naming and ordering

Baseline names are the release tag, semver-shaped: `v1.2`, `v1.2.3`, `v1.2.3-rc.1`. `specflow baseline create` rejects freeform names such as `snapshot`, so drift comparison always has release versions to prefer.

## Ordering (SemVer 2.0 section 11)

Baseline listing, drift comparison and "previous release" lookup all sort ascending, newest last:

- Numeric core segments compare as integers (`v1.9.2` < `v1.13.3`).
- A prerelease sorts below the release it belongs to (`v1.0.0-rc.1` < `v1.0.0`).
- Prerelease identifiers split on `.`; numeric ones compare as integers (`rc.9` < `rc.10`), numeric sorts before alphanumeric, alphanumeric compares in ASCII order, and the shorter list sorts first when it is a prefix (`alpha` < `alpha.1` < `alpha.beta` < `beta` < `beta.2` < `beta.11` < `rc.1` < release).
- Build metadata (`+build5`) is ignored for ordering.
- Names that are not semver-parseable sort after every semver name.

## Post-release suffix policy

A suffix after the version, such as `v0.2.1-spec-sync`, is a prerelease of `v0.2.1`, so it sorts BELOW `v0.2.1` and above `v0.2.0`. Use it for spec-only or follow-up baselines cut before the release baseline. To mark something newer than `v0.2.1`, bump the version (`v0.2.2`) instead of adding a suffix.
