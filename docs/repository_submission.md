# GitHub submission checklist

## Repository

- Repository name: `CyberVault-RAG`
- Description: `AI-powered cybersecurity document intelligence using Gemini embeddings, ChromaDB, semantic retrieval and grounded RAG generation.`
- Initial commit message: `Initial release: CyberVault RAG`
- Submission URL placeholder: `https://github.com/<username>/CyberVault-RAG`

## Topics

`artificial-intelligence`, `rag`, `cybersecurity`, `python`, `streamlit`,
`gemini`, `chromadb`, `vector-database`, `semantic-search`

## Exclusions

The `.gitignore` excludes:

- `.env` and other `.env.*` files, except `.env.example`
- Python virtual environments, caches, compiled files, and pytest cache
- ChromaDB runtime data and local database files
- Local source corpus under `data/documents/`
- Streamlit secrets, private keys, and local service credentials
- IDE folders, temporary files, logs, and test coverage output

The corpus is excluded to avoid accidental redistribution before publisher
reuse notices are reviewed. Its official source URLs, terms, and local paths
are recorded in [dataset_sources.md](dataset_sources.md).

## Publication status

Git is unavailable in this environment. Repository status, staged/unstaged
diffs, and Git's actual ignore decisions could not be inspected. The `.gitignore`
rules were reviewed directly. No repository was initialized, no commit was
created, no remote was added, and nothing was pushed.

After installing Git, review the staged files, especially `data/`, `.env`, and
`docs/images/`. Do not commit or push without explicit approval.

```powershell
git init
git add .
git status
git diff --cached --stat
git commit -m "Initial release: CyberVault RAG"
git branch -M main
git remote add origin https://github.com/<username>/CyberVault-RAG.git
git push -u origin main
```
