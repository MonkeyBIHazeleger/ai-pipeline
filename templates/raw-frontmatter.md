# Raw File Frontmatter Schema

Reference for frontmatter fields written to `obsidian/raw/` by `research.py`.

## Required Fields

```yaml
---
topic: "Topic Name"
source: "Service Name"
date: "YYYY-MM-DD"
target_wiki: "Wiki Folder Name"
query: "Original research query"
ingested: false
---
```

## Field Descriptions

| Field | Type | Values | Description |
|---|---|---|---|
| `topic` | string | Any | Main topic of the research |
| `source` | string | `perplexity` \| `tavily` \| `claude` \| `github` \| `manual` | Which service/method produced this |
| `date` | string | `YYYY-MM-DD` | Date created |
| `target_wiki` | string | `fin_wiki` \| `code_wiki` \| `other_wiki` \| `tools_wiki` | Destination wiki folder |
| `query` | string | Any | The original question or search query |
| `ingested` | boolean | `false` \| `true` | Whether `ingest.py` has processed this file |

## Processing

1. `research.py` creates file with `ingested: false`
2. File placed in `obsidian/raw/research-{slug}-{date}.md`
3. `ingest.py` reads file, processes content, creates/updates wiki pages
4. `ingest.py` updates this file to set `ingested: true` after successful processing
5. File is now immutable (never modify raw files)

## Example

```yaml
---
topic: "Perplexity API"
source: "perplexity"
date: "2026-05-05"
target_wiki: "tools_wiki"
query: "What is the Perplexity API and how is it priced?"
ingested: false
---

# Perplexity API Research Results

[Research content from service goes here...]
```
