# Spaxiom Release Checklist

This document outlines the steps required to release a new version of the Spaxiom DSL package.

## Release Process

### 1. Prepare the Release

- [ ] Make sure all tests pass locally
  ```bash
  python -m pytest
  ```

- [ ] Check code quality with linters
  ```bash
  black --check .
  ruff check .
  ```

- [ ] Update CHANGELOG.md (if present) with changes since the last release

### 2. Bump Version Numbers

- [ ] Update version in `pyproject.toml`:
  ```toml
  [tool.poetry]
  name = "spaxiom"
  version = "X.Y.Z"  # Update this line
  ```

- [ ] Update version in `spaxiom/__init__.py`:
  ```python
  __version__ = "X.Y.Z"  # Update this line
  ```

- [ ] Install the package locally to verify the version change:
  ```bash
  pip install -e .
  python -c "import spaxiom; print(spaxiom.__version__)"
  ```

### 3. Commit and Tag the Release

- [ ] Commit the version change:
  ```bash
  git add pyproject.toml spaxiom/__init__.py
  git commit -m "Bump version to X.Y.Z"
  ```

- [ ] Create a release tag:
  ```bash
  git tag -a vX.Y.Z -m "Version X.Y.Z"
  ```

- [ ] Push the commit and tag:
  ```bash
  git push
  git push origin vX.Y.Z
  ```

### 4. Verify the Build and Deployment

- [ ] Check GitHub Actions to verify the CI workflow is running
  - Go to your repository's Actions tab in GitHub
  - Check that the workflow triggered by the tag is running

- [ ] Verify the package was uploaded to TestPyPI
  - Visit https://test.pypi.org/project/spaxiom/
  - Check that the new version is listed

### 5. Test Installation from TestPyPI

- [ ] Create a new virtual environment:
  ```bash
  python -m venv test_install
  source test_install/bin/activate  # On Unix/macOS
  # or
  test_install\Scripts\activate  # On Windows
  ```

- [ ] Install the package from TestPyPI:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ spaxiom==X.Y.Z
  ```

- [ ] Verify the installation:
  ```bash
  python -c "import spaxiom; print(spaxiom.__version__)"
  spax-run --help
  ```

### 6. Final Release to PyPI (if applicable)

If you're ready to release to the main PyPI repository, update your CI configuration to also deploy to PyPI or manually publish:

- [ ] Deploy to PyPI:
  ```bash
  pip install twine
  twine upload dist/*
  ```

### 7. Post-Release

- [ ] Create a GitHub Release:
  - Go to Releases → Draft a new release
  - Choose the tag you created
  - Add release notes

- [ ] Bump version to next development version (optional):
  - Update version to "X.Y.(Z+1)-dev" in pyproject.toml and __init__.py
  - Commit: `git commit -m "Bump to development version X.Y.(Z+1)-dev"`

## Notes

- The CI workflow will automatically build and deploy the package to TestPyPI when a tag starting with "v" is pushed.
- Make sure the `TEST_PYPI_TOKEN` secret is configured in your GitHub repository settings.
- For proper semantic versioning:
  - Bump major version (X) for incompatible API changes
  - Bump minor version (Y) for new functionality in a backward-compatible manner
  - Bump patch version (Z) for backward-compatible bug fixes 