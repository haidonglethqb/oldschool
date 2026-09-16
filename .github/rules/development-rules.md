# Development Rules

**IMPORTANT:** Analyze the skills catalog and activate the skills that are needed for the task during the process.
**IMPORTANT:** You ALWAYS follow these principles: **YAGNI (You Aren't Gonna Need It) - KISS (Keep It Simple, Stupid) - DRY (Don't Repeat Yourself)**

## General
- **File Naming**: Use kebab-case for file names with a meaningful name that describes the purpose of the file, doesn't matter if the file name is long, just make sure when LLMs read the file names while using Grep or other tools, they can understand the purpose of the file right away without reading the file content.
- **File Size Management**: Keep individual code files under 200 lines for optimal context management
  - Split large files into smaller, focused components/modules
  - Use composition over inheritance for complex widgets
  - Extract utility functions into separate modules
  - Create dedicated service classes for business logic
- When looking for docs, activate `docs-seeker` skill (`context7` reference) for exploring latest docs.
- Use `gh` bash command to interact with Github features if needed
- Use `psql` bash command to query Postgres database for debugging if needed
- Use `ai-multimodal` skill for describing details of images, videos, documents, etc. if needed
- Use `ai-multimodal` skill and `imagemagick` skill for generating and editing images, videos, documents, etc. if needed
- Use `sequential-thinking` and `debug` skills for sequential thinking, analyzing code, debugging, etc. if needed
- **[IMPORTANT]** Follow the codebase structure and code standards in `./docs` during implementation.
- **[IMPORTANT]** Reference `./docs/system/README.md` as the system documentation hub before working on features
- **[IMPORTANT]** Do not just simulate the implementation or mocking them, always implement the real code.

## Code Quality Guidelines
- Read and follow codebase structure and code standards in `./docs`
- Reference `./docs/system/` for system specifications before implementing changes
- Don't be too harsh on code linting, but **make sure there are no syntax errors and code are compilable**
- Prioritize functionality and readability over strict style enforcement and code formatting
- Use reasonable code quality standards that enhance developer productivity
- Use try catch error handling & cover security standards
- Use `code-reviewer` agent to review code after every implementation

## Pre-commit/Push Rules
- Run linting before commit
- Run tests before push (DO NOT ignore failed tests just to pass the build or github actions)
- Keep commits focused on the actual code changes
- **DO NOT** commit and push any confidential information (such as dotenv files, API keys, database credentials, etc.) to git repository!
- Create clean, professional commit messages without AI references. Use conventional commit format.

## Code Implementation
- Write clean, readable, and maintainable code
- Follow established architectural patterns
- Implement features according to specifications
- Handle edge cases and error scenarios
- **DO NOT** create new enhanced files, update to the existing files directly.
- **[MANDATORY] After implementation, update relevant `./docs/system/` documentation if the change affects system behavior, API contracts, database schema, or business logic**

## Documentation Updates
- **After every feature implementation, bug fix, or refactoring**, review and update relevant files in `./docs/system/`:
  - Changed endpoints → `./docs/system/backend/api-endpoints.md`
  - New models/fields → `./docs/system/database/*.md`
  - Modified business rules → `./docs/system/business-rules/*.md`
  - Security changes → `./docs/system/security/*.md`
  - New workflows → `./docs/system/data-flows/*.md`
  - Auth/RBAC changes → `./docs/system/authentication/*.md`
- Keep each file under 100 lines; split content if needed
- Update cross-references ("Related" sections) when adding/removing links
- Delegate to `docs-manager` agent for complex documentation updates

## Visual Aids
- Use `/preview --explain` when explaining unfamiliar code patterns or complex logic
- Use `/preview --diagram` for architecture diagrams and data flow visualization
- Use `/preview --slides` for step-by-step walkthroughs and presentations
- Use `/preview --ascii` for terminal-friendly diagrams (no browser needed to understand)
- **Plan context:** Active plan determined from `## Plan Context` in hook injection; visuals save to `{plan_dir}/visuals/`
- If no active plan, fallback to `plans/visuals/` directory
- For Mermaid diagrams, use `/mermaidjs-v11` skill for v11 syntax rules
- See `primary-workflow.md` → Step 6 for workflow integration