# Publishing Ontech Control

The local integration is being prepared for Marketplace and HACS distribution. It is not published, listed in the catalog, or hardware-verified yet.

## Publication hold

The target repository is https://github.com/dannew/ontech and the maintainer is @dannew. Do not create a release, submit to HACS or Home Assistant, or request catalog inclusion until hardware testing and validation are complete and the owner approves publication. CI does not publish anything.

## Complete repository metadata

1. Choose the actual public GitHub repository and maintainer.
2. Set `documentation` in `custom_components/ontech/manifest.json` to `https://github.com/<owner>/<repository>` and `issue_tracker` to that URL plus `/issues`.
3. Set `codeowners` to the responsible GitHub usernames, prefixed with `@`. Do not point these fields at Ontech's support channels.
4. Set a repository description, enable issues, and add relevant topics such as `home-assistant`, `hacs`, `ontech`, and `custom-integration`.
5. Update README installation instructions with the real repository URL and a [My Home Assistant link](https://contributors.home-assistant.io/marketplace/guides/catalog/). Use repository category `integration`, not `plugin` (which means a dashboard plugin).
6. Run `python scripts/check_release.py`. It reports missing publication metadata and checks a tag against the manifest version when run in GitHub Actions.

## Validate a candidate

- Run tests and Ruff as shown in README.md. The supported floor is declared in `hacs.json`; do not lower it without testing that version.
- Run the included HACS and hassfest workflows on the public repository. All checks must pass without ignored checks. Repository description, topics, issues, and releases cannot be verified by the local test suite.
- Replace the pinned 2026.11 beta in CI with the stable version once it is released and tested. A beta test is not a claim of stable-version certification.
- Verify login, devices, physical switching, stale-data handling, restart, and recovery using a real account. Resolve BUG-001 before presenting the integration as production-ready.
- Review license, release notes, known limitations, translations, and brand images. The integration ships its own 256px and 512px icons in `brand/`.

## Create a release

Update `manifest.json` version, add release notes describing user-visible changes and remaining limitations, then create a matching tag and a **GitHub release**. A tag alone does not satisfy catalog submission requirements. No ZIP asset is necessary: Marketplace/HACS installs `custom_components/ontech` from the release archive.

Start with a prerelease while hardware verification is incomplete. Users can try the published repository as a custom repository before catalog inclusion. Do not claim catalog availability merely because `hacs.json` exists.

## Apply to the shared catalog

After validation and a full release, the owner or a major contributor can submit a pull request to [hacs/default](https://github.com/hacs/default), adding the repository to the `integration` list in alphabetical order. Include links to the release and successful HACS and hassfest runs. Catalog maintainers review the submission; acceptance and timing are external to this project.

## References

- [Publish a custom integration](https://contributors.home-assistant.io/marketplace/guides/integrations/)
- [Marketplace validation](https://contributors.home-assistant.io/marketplace/reference/validation/)
- [hacs.json](https://contributors.home-assistant.io/marketplace/reference/hacs-json/)
- [Catalog submission](https://contributors.home-assistant.io/marketplace/guides/catalog/)
- [Custom integration translations](https://contributors.home-assistant.io/core/integrations/translations/#custom-integrations)

## Python compatibility

The source targets Python 3.14, including PEP 758 exception syntax. Do not lower the Home Assistant version floor to a release using an older Python runtime without adapting the syntax and validating the full test matrix.
