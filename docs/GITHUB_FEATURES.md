# GitHub repository features

These are GitHub navigation areas, not missing application pages.

- **Issues:** Bug reports and feature requests. Templates are in `.github/ISSUE_TEMPLATE/`.
- **Pull requests:** Review proposed code changes. A checklist is in `.github/pull_request_template.md`.
- **Actions:** The `.github/workflows/ci.yml` workflow validates JSON data, compiles the Python backend, and checks expected files on pushes and pull requests.
- **Projects:** Optional planning board. Create a board in the GitHub Projects tab and add issues for roadmap tasks.
- **Wiki:** Optional documentation space. Project setup and API documentation currently live in `README.md` and `docs/`.
- **Security and quality:** Security guidance is in `SECURITY.md`. GitHub may show more controls depending on repository settings and plan.
- **Insights:** GitHub populates charts when it has activity to report; these cannot be filled with fabricated data.
- **Settings:** Administrative controls, not a project feature. Only change settings when there is a specific need.

## Suggested first issues
1. Add automated tests for API endpoints.
2. Add a database and optional account-based sync.
3. Build a retrieval-augmented generation (RAG) pipeline over trusted learning materials.
4. Add a live, attributed resource search provider.
5. Add deployment configuration and production security checks.
